from django.contrib import admin
from .models import CodeKnowledgeBase, CodeChunk, CodeQueryLog


@admin.register(CodeKnowledgeBase)
class CodeKnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ['title', 'language', 'uploaded_by', 'is_processed', 'chunk_count', 'uploaded_at']
    list_filter = ['language', 'is_processed', 'uploaded_at']
    search_fields = ['title', 'description', 'tags']
    readonly_fields = ['file_hash', 'file_size', 'chunk_count', 'is_processed', 'processing_error', 'uploaded_at', 'modified_at']


@admin.register(CodeChunk)
class CodeChunkAdmin(admin.ModelAdmin):
    list_display = ['code_file', 'chunk_index', 'chunk_type', 'created_at']
    list_filter = ['chunk_type', 'created_at']
    search_fields = ['code_file__title', 'content']


@admin.register(CodeQueryLog)
class CodeQueryLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'query_text', 'total_time_ms', 'created_at']
    list_filter = ['user', 'created_at', 'language_filter']
    readonly_fields = ['user', 'query_text', 'response_text', 'source_files', 'retrieval_time_ms', 'inference_time_ms', 'total_time_ms', 'created_at']
