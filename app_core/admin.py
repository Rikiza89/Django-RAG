"""
Django Admin Configuration for Knowledge Management System
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Document, DocumentChunk, EmbeddingMetadata, 
    UserProfile, QueryLog
)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin interface for Document model"""
    list_display = [
        'title', 'file_type', 'file_size_display', 'access_level', 
        'department', 'uploaded_by', 'uploaded_at', 'status_badge'
    ]
    list_filter = ['access_level', 'file_type', 'is_processed', 'uploaded_at']
    search_fields = ['title', 'text_preview', 'department']
    readonly_fields = [
        'file_hash', 'file_size', 'file_type', 'uploaded_at', 
        'modified_at', 'chunk_count', 'text_preview'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'file', 'file_type', 'file_size')
        }),
        ('Access Control', {
            'fields': ('access_level', 'department')
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'uploaded_at', 'modified_at', 'file_hash')
        }),
        ('Processing Status', {
            'fields': ('is_processed', 'processing_error', 'chunk_count', 'text_preview')
        }),
    )
    
    def file_size_display(self, obj):
        """Display file size in human-readable format"""
        return f"{obj.file_size / 1024:.1f} KB"
    file_size_display.short_description = 'Size'
    
    def status_badge(self, obj):
        """Display processing status as colored badge"""
        if obj.is_processed:
            return format_html(
                '<span style="color: green;">✓ Processed ({} chunks)</span>',
                obj.chunk_count
            )
        elif obj.processing_error:
            return format_html('<span style="color: red;">✗ Error</span>')
        else:
            return format_html('<span style="color: orange;">⏳ Pending</span>')
    status_badge.short_description = 'Status'


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    """Admin interface for DocumentChunk model"""
    list_display = ['document', 'chunk_index', 'content_preview', 'created_at']
    list_filter = ['document', 'created_at']
    search_fields = ['content', 'document__title']
    readonly_fields = ['embedding_id', 'created_at']
    
    def content_preview(self, obj):
        """Show first 100 characters of content"""
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content Preview'


@admin.register(EmbeddingMetadata)
class EmbeddingMetadataAdmin(admin.ModelAdmin):
    """Admin interface for EmbeddingMetadata model"""
    list_display = [
        'total_embeddings', 'embedding_dimension', 
        'model_name', 'index_size_display', 'last_updated'
    ]
    readonly_fields = [
        'total_embeddings', 'embedding_dimension', 
        'model_name', 'index_size_bytes', 'last_updated'
    ]
    
    def index_size_display(self, obj):
        """Display index size in human-readable format"""
        return f"{obj.index_size_bytes / (1024 * 1024):.2f} MB"
    index_size_display.short_description = 'Index Size'
    
    def has_add_permission(self, request):
        """Prevent manual creation"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion"""
        return False


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for UserProfile model"""
    list_display = [
        'user', 'role', 'department', 
        'preferred_chunk_size', 'max_query_results', 'created_at'
    ]
    list_filter = ['role', 'department', 'created_at']
    search_fields = ['user__username', 'user__email', 'department']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Role & Department', {
            'fields': ('role', 'department')
        }),
        ('Preferences', {
            'fields': ('preferred_chunk_size', 'max_query_results')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    """Admin interface for QueryLog model"""
    list_display = [
        'user', 'query_preview', 'response_preview',
        'source_count', 'total_time_display', 'created_at'
    ]
    list_filter = ['user', 'created_at']
    search_fields = ['query_text', 'response_text', 'user__username']
    readonly_fields = [
        'user', 'query_text', 'response_text', 'source_documents',
        'retrieval_time_ms', 'inference_time_ms', 'total_time_ms', 'created_at'
    ]
    
    def query_preview(self, obj):
        """Show first 50 characters of query"""
        return obj.query_text[:50] + '...' if len(obj.query_text) > 50 else obj.query_text
    query_preview.short_description = 'Query'
    
    def response_preview(self, obj):
        """Show first 50 characters of response"""
        return obj.response_text[:50] + '...' if len(obj.response_text) > 50 else obj.response_text
    response_preview.short_description = 'Response'
    
    def source_count(self, obj):
        """Display number of source documents"""
        return len(obj.source_documents) if obj.source_documents else 0
    source_count.short_description = 'Sources'
    
    def total_time_display(self, obj):
        """Display total time with formatting"""
        return f"{obj.total_time_ms}ms"
    total_time_display.short_description = 'Time'
    
    def has_add_permission(self, request):
        """Prevent manual creation"""
        return False


# Customize admin site headers
admin.site.site_header = "Knowledge Management System Admin"
admin.site.site_title = "KMS Admin"
admin.site.index_title = "System Administration"