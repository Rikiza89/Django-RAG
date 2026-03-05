"""
Models for the Coding IDE RAG system.
Tracks uploaded code files, their chunks, and query history.
"""
import hashlib
import os
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings


class CodeLanguage(models.TextChoices):
    PYTHON = 'python', 'Python'
    JAVASCRIPT = 'javascript', 'JavaScript'
    TYPESCRIPT = 'typescript', 'TypeScript'
    JAVA = 'java', 'Java'
    CPP = 'cpp', 'C++'
    C = 'c', 'C'
    GO = 'go', 'Go'
    RUST = 'rust', 'Rust'
    PHP = 'php', 'PHP'
    RUBY = 'ruby', 'Ruby'
    SWIFT = 'swift', 'Swift'
    KOTLIN = 'kotlin', 'Kotlin'
    CSHARP = 'csharp', 'C#'
    HTML = 'html', 'HTML'
    CSS = 'css', 'CSS'
    SQL = 'sql', 'SQL'
    SHELL = 'shell', 'Shell/Bash'
    MARKDOWN = 'markdown', 'Markdown'
    JSON = 'json', 'JSON'
    YAML = 'yaml', 'YAML'
    OTHER = 'other', 'Other'


EXTENSION_TO_LANGUAGE = {
    '.py': CodeLanguage.PYTHON,
    '.js': CodeLanguage.JAVASCRIPT,
    '.ts': CodeLanguage.TYPESCRIPT,
    '.java': CodeLanguage.JAVA,
    '.cpp': CodeLanguage.CPP,
    '.cc': CodeLanguage.CPP,
    '.cxx': CodeLanguage.CPP,
    '.c': CodeLanguage.C,
    '.h': CodeLanguage.C,
    '.hpp': CodeLanguage.CPP,
    '.go': CodeLanguage.GO,
    '.rs': CodeLanguage.RUST,
    '.php': CodeLanguage.PHP,
    '.rb': CodeLanguage.RUBY,
    '.swift': CodeLanguage.SWIFT,
    '.kt': CodeLanguage.KOTLIN,
    '.cs': CodeLanguage.CSHARP,
    '.html': CodeLanguage.HTML,
    '.htm': CodeLanguage.HTML,
    '.css': CodeLanguage.CSS,
    '.sql': CodeLanguage.SQL,
    '.sh': CodeLanguage.SHELL,
    '.bash': CodeLanguage.SHELL,
    '.md': CodeLanguage.MARKDOWN,
    '.json': CodeLanguage.JSON,
    '.yaml': CodeLanguage.YAML,
    '.yml': CodeLanguage.YAML,
}


class CodeKnowledgeBase(models.Model):
    """
    A code file stored in the knowledge base.
    """
    title = models.CharField(max_length=255, help_text="Descriptive name for this code file/snippet")
    description = models.TextField(blank=True, help_text="What this code does (used as RAG context)")
    file = models.FileField(upload_to='code_files/%Y/%m/%d/', blank=True, null=True)
    file_hash = models.CharField(max_length=64, unique=True, help_text="SHA-256 hash for deduplication")
    file_size = models.IntegerField(default=0, help_text="Size in bytes")
    language = models.CharField(
        max_length=20,
        choices=CodeLanguage.choices,
        default=CodeLanguage.OTHER,
    )

    # Processing status
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True, null=True)
    chunk_count = models.IntegerField(default=0)

    # Content
    content_preview = models.TextField(blank=True, help_text="First 600 chars of source code")

    # Meta
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='code_files')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated tags for filtering")

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['language', 'uploaded_at']),
            models.Index(fields=['uploaded_by', 'uploaded_at']),
            models.Index(fields=['file_hash']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_language_display()})"

    def save(self, *args, **kwargs):
        if self.file and not self.file_hash:
            self.file_hash = self._calculate_hash()
            self.file_size = self.file.size
            ext = os.path.splitext(self.file.name)[1].lower()
            self.language = EXTENSION_TO_LANGUAGE.get(ext, CodeLanguage.OTHER)
        super().save(*args, **kwargs)

    def _calculate_hash(self):
        sha256 = hashlib.sha256()
        self.file.seek(0)
        for chunk in iter(lambda: self.file.read(4096), b''):
            sha256.update(chunk)
        self.file.seek(0)
        return sha256.hexdigest()

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()]


class CodeChunk(models.Model):
    """
    A text chunk extracted from a CodeKnowledgeBase file for RAG.
    """
    code_file = models.ForeignKey(CodeKnowledgeBase, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.IntegerField()
    content = models.TextField()
    embedding_id = models.CharField(max_length=64, unique=True)

    # Context metadata
    start_line = models.IntegerField(default=0, help_text="Approximate start line in source file")
    chunk_type = models.CharField(
        max_length=20,
        default='code',
        choices=[('code', 'Code'), ('comment', 'Comment/Docstring'), ('mixed', 'Mixed')],
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code_file', 'chunk_index']
        unique_together = ['code_file', 'chunk_index']

    def __str__(self):
        return f"{self.code_file.title} — Chunk {self.chunk_index}"


class CodeQueryLog(models.Model):
    """
    Records coding queries for history and analytics.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='code_queries')
    query_text = models.TextField()
    response_text = models.TextField()
    source_files = models.JSONField(default=list, help_text="List of CodeKnowledgeBase IDs used")
    language_filter = models.CharField(max_length=20, blank=True, help_text="Language filter applied")

    # Performance
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
        return f"{self.user.username}: {self.query_text[:50]}…"
