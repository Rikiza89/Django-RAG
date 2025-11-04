"""
Models for Knowledge Management System
Includes Document storage, Embedding metadata, and User profiles
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.conf import settings
import hashlib
import os


class AccessLevel(models.TextChoices):
    """Document access levels for authorization"""
    PUBLIC = 'public', 'Public (All Users)'
    DEPARTMENT = 'department', 'Department Only'
    MANAGER = 'manager', 'Managers Only'
    PRIVATE = 'private', 'Private (Admin Only)'


class Document(models.Model):
    """
    Core document model with access control and metadata
    """
    title = models.CharField(max_length=255)
    file = models.FileField(
        upload_to='documents/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'docx', 'txt', 'xlsx'])]
    )
    file_type = models.CharField(max_length=10)
    file_size = models.IntegerField(help_text="Size in bytes")
    file_hash = models.CharField(max_length=64, unique=True, help_text="SHA-256 hash for deduplication")
    
    # Access Control
    access_level = models.CharField(
        max_length=20,
        choices=AccessLevel.choices,
        default=AccessLevel.DEPARTMENT
    )
    department = models.CharField(max_length=100, blank=True, help_text="Department name for filtering")
    
    # Metadata
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_documents')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    # Processing Status
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True, null=True)
    chunk_count = models.IntegerField(default=0, help_text="Number of text chunks created")
    
    # Content Preview
    text_preview = models.TextField(blank=True, help_text="First 500 chars of extracted text")
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['access_level', 'department']),
            models.Index(fields=['uploaded_by', 'uploaded_at']),
            models.Index(fields=['file_hash']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Calculate file hash if not set
        if not self.file_hash and self.file:
            self.file_hash = self.calculate_file_hash()
        
        # Extract file type from extension
        if self.file:
            self.file_type = os.path.splitext(self.file.name)[1].lower().replace('.', '')
            self.file_size = self.file.size
        
        super().save(*args, **kwargs)
    
    def calculate_file_hash(self):
        """Calculate SHA-256 hash of the file"""
        sha256 = hashlib.sha256()
        self.file.seek(0)
        for chunk in iter(lambda: self.file.read(4096), b''):
            sha256.update(chunk)
        self.file.seek(0)
        return sha256.hexdigest()
    
    def can_access(self, user):
        """Check if user has permission to access this document"""
        if not user.is_authenticated:
            return False
        
        # Admin can access everything
        if user.is_superuser:
            return True
        
        # Check access level
        if self.access_level == AccessLevel.PUBLIC:
            return True
        
        profile = UserProfile.objects.filter(user=user).first()
        if not profile:
            return False
        
        if self.access_level == AccessLevel.PRIVATE:
            return False
        
        if self.access_level == AccessLevel.MANAGER:
            return profile.role in ['admin', 'manager']
        
        if self.access_level == AccessLevel.DEPARTMENT:
            return profile.department == self.department or profile.role in ['admin', 'manager']
        
        return False


class DocumentChunk(models.Model):
    """
    Text chunks extracted from documents for RAG
    """
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.IntegerField(help_text="Order of chunk in document")
    content = models.TextField(help_text="Actual text content")
    embedding_id = models.CharField(max_length=64, unique=True, help_text="ID in FAISS index")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['document', 'chunk_index']
        unique_together = ['document', 'chunk_index']
        indexes = [
            models.Index(fields=['embedding_id']),
        ]
    
    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"


class EmbeddingMetadata(models.Model):
    """
    Metadata for FAISS embeddings to track index status
    """
    total_embeddings = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    embedding_dimension = models.IntegerField(default=384, help_text="Dimension of embedding vectors")
    model_name = models.CharField(max_length=255, default=settings.EMBEDDING_MODEL)
    index_size_bytes = models.BigIntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "Embedding Metadata"
    
    def __str__(self):
        return f"Embeddings: {self.total_embeddings} | Updated: {self.last_updated}"


class UserRole(models.TextChoices):
    """User roles for authorization"""
    ADMIN = 'admin', 'Administrator'
    MANAGER = 'manager', 'Manager'
    EMPLOYEE = 'employee', 'Employee'


class UserProfile(models.Model):
    """
    Extended user profile with role and department
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.EMPLOYEE)
    department = models.CharField(max_length=100, blank=True)
    
    # Preferences
    preferred_chunk_size = models.IntegerField(default=settings.CHUNK_SIZE)
    max_query_results = models.IntegerField(default=settings.FAISS_TOP_K)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['role', 'department']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    def can_upload(self):
        """Check if user can upload documents"""
        return self.role in [UserRole.ADMIN, UserRole.MANAGER]
    
    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.role == UserRole.ADMIN


class QueryLog(models.Model):
    """
    Log of user queries for analytics and caching
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='queries')
    query_text = models.TextField()
    response_text = models.TextField()
    source_documents = models.JSONField(default=list, help_text="List of document IDs used")
    
    # Performance metrics
    retrieval_time_ms = models.IntegerField(default=0)
    inference_time_ms = models.IntegerField(default=0)
    total_time_ms = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.query_text[:50]}..."