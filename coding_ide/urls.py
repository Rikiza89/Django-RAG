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

    # System
    path('status/', views.ide_system_status, name='system_status'),
    path('api/check-model/', views.api_check_coder_model, name='api_check_model'),
    path('api/clear-cache/', views.api_clear_code_cache, name='api_clear_cache'),
]
