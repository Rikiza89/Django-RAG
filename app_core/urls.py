"""
URL Configuration for app_core
"""
from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Documents
    path('documents/', views.document_list, name='documents'),
    path('documents/upload/', views.document_upload, name='document_upload'),
    path('documents/<int:pk>/', views.document_detail, name='document_detail'),
    path('documents/<int:pk>/download/', views.document_download, name='document_download'),
    path('documents/<int:pk>/delete/', views.document_delete, name='document_delete'),
    path('documents/<int:pk>/reindex/', views.document_reindex, name='document_reindex'),
    
    # Chat / Query
    path('chat/', views.chat, name='chat'),
    path('api/query/', views.query_api, name='query_api'),
    path('queries/', views.query_history, name='query_history'),
    
    # System Management
    path('system/status/', views.system_status, name='system_status'),
    path('api/clear-cache/', views.clear_cache, name='clear_cache'),
    
    # User Management
    path('profile/', views.profile, name='profile'),
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    
    # API Endpoints
    path('api/check-ollama/', views.api_check_ollama, name='api_check_ollama'),
    path('api/embedding-status/', views.api_embedding_status, name='api_embedding_status'),
    path('api/model-download-status/', views.api_model_download_status, name='api_model_download_status'),
]