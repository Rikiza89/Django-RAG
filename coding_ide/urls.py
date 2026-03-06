from django.urls import path
from . import views

app_name = 'coding_ide'

urlpatterns = [
    # Dashboard
    path('', views.ide_dashboard, name='dashboard'),

    # Knowledge Base
    path('knowledge-base/', views.knowledge_base_list, name='knowledge_base'),
    path('knowledge-base/upload/', views.upload_code, name='upload_code'),
    path('knowledge-base/<int:pk>/', views.code_file_detail, name='code_detail'),
    path('knowledge-base/<int:pk>/reindex/', views.code_file_reindex, name='code_reindex'),
    path('knowledge-base/<int:pk>/delete/', views.code_file_delete, name='code_delete'),

    # IDE Chat
    path('chat/', views.ide_chat, name='ide_chat'),
    path('api/query/', views.ide_query_api, name='ide_query_api'),

    # History
    path('history/', views.code_query_history, name='query_history'),

    # In-browser Code Editor
    path('editor/', views.code_editor, name='code_editor'),
    path('editor/<int:pk>/', views.code_editor, name='code_editor_edit'),
    path('editor/save/', views.code_editor_save, name='code_editor_save'),
    path('editor/<int:pk>/delete/', views.code_editor_delete, name='code_editor_delete'),
    path('api/snippet/<int:pk>/', views.api_snippet_content, name='api_snippet_content'),

    # Git Manager
    path('git/', views.git_manager, name='git_manager'),
    path('git/add/', views.git_add_repo, name='git_add_repo'),
    path('git/<int:pk>/remove/', views.git_remove_repo, name='git_remove_repo'),
    path('api/git/<int:pk>/status/', views.api_git_status, name='api_git_status'),
    path('api/git/<int:pk>/init/', views.api_git_init, name='api_git_init'),
    path('api/git/<int:pk>/add/', views.api_git_add, name='api_git_add'),
    path('api/git/<int:pk>/commit/', views.api_git_commit, name='api_git_commit'),
    path('api/git/<int:pk>/branch/', views.api_git_branch, name='api_git_branch'),
    path('api/git/<int:pk>/checkout/', views.api_git_checkout, name='api_git_checkout'),
    path('api/git/<int:pk>/push/', views.api_git_push, name='api_git_push'),
    path('api/git/<int:pk>/pull/', views.api_git_pull, name='api_git_pull'),

    # System
    path('status/', views.ide_system_status, name='system_status'),
    path('api/check-model/', views.api_check_coder_model, name='api_check_model'),
    path('api/clear-cache/', views.api_clear_code_cache, name='api_clear_cache'),
]
