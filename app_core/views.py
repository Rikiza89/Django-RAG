"""
Views for Knowledge Management System
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.http import JsonResponse, FileResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.conf import settings

from .models import Document, UserProfile, QueryLog, DocumentChunk, EmbeddingMetadata
from .forms import (
    DocumentUploadForm, QueryForm, UserProfileForm, 
    UserCreationForm, DocumentFilterForm
)
from .rag_pipeline import rag_pipeline

logger = logging.getLogger(__name__)

# ============= Authentication Views =============

def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'app_core/login.html')

@login_required
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')

# ============= Dashboard Views =============

@login_required
def dashboard(request):
    """Main dashboard view"""
    user = request.user
    profile = UserProfile.objects.filter(user=user).first()
    
    # Get documents accessible to user
    if user.is_superuser:
        documents = Document.objects.all()
    elif profile:
        if profile.role == 'admin':
            documents = Document.objects.all()
        elif profile.role == 'manager':
            documents = Document.objects.filter(
                Q(access_level='public') |
                Q(access_level='department', department=profile.department) |
                Q(access_level='manager')
            )
        else:
            documents = Document.objects.filter(
                Q(access_level='public') |
                Q(access_level='department', department=profile.department)
            )
    else:
        documents = Document.objects.filter(access_level='public')
    
    # Statistics
    stats = {
        'total_documents': documents.count(),
        'processed_documents': documents.filter(is_processed=True).count(),
        'failed_documents': documents.filter(is_processed=False, processing_error__isnull=False).count(),
        'total_chunks': DocumentChunk.objects.filter(document__in=documents).count(),
        'recent_queries': QueryLog.objects.filter(user=user).count(),
    }
    
    # Recent documents
    recent_documents = documents.order_by('-uploaded_at')[:5]
    
    # Recent queries
    recent_queries = QueryLog.objects.filter(user=user).order_by('-created_at')[:5]
    
    # System status
    system_status = rag_pipeline.get_system_status()
    
    context = {
        'stats': stats,
        'recent_documents': recent_documents,
        'recent_queries': recent_queries,
        'system_status': system_status,
        'profile': profile,
    }
    
    return render(request, 'app_core/dashboard.html', context)

# ============= Document Views =============

@login_required
def document_list(request):
    """List all documents with filtering"""
    user = request.user
    profile = UserProfile.objects.filter(user=user).first()
    
    # Base queryset with access control
    if user.is_superuser or (profile and profile.role == 'admin'):
        documents = Document.objects.all()
    elif profile and profile.role == 'manager':
        documents = Document.objects.filter(
            Q(access_level='public') |
            Q(access_level='department', department=profile.department) |
            Q(access_level='manager')
        )
    elif profile:
        documents = Document.objects.filter(
            Q(access_level='public') |
            Q(access_level='department', department=profile.department)
        )
    else:
        documents = Document.objects.filter(access_level='public')
    
    # Apply filters
    filter_form = DocumentFilterForm(request.GET)
    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        if search:
            documents = documents.filter(
                Q(title__icontains=search) |
                Q(text_preview__icontains=search)
            )
        
        access_level = filter_form.cleaned_data.get('access_level')
        if access_level:
            documents = documents.filter(access_level=access_level)
        
        department = filter_form.cleaned_data.get('department')
        if department:
            documents = documents.filter(department__icontains=department)
        
        file_type = filter_form.cleaned_data.get('file_type')
        if file_type:
            documents = documents.filter(file_type=file_type)
        
        processed = filter_form.cleaned_data.get('processed')
        if processed == 'yes':
            documents = documents.filter(is_processed=True)
        elif processed == 'no':
            documents = documents.filter(is_processed=False, processing_error__isnull=True)
        elif processed == 'error':
            documents = documents.filter(is_processed=False, processing_error__isnull=False)
    
    # Pagination
    paginator = Paginator(documents.order_by('-uploaded_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'documents': page_obj,
        'filter_form': filter_form,
        'profile': profile,
    }
    
    return render(request, 'app_core/documents.html', context)

@login_required
def document_upload(request):
    """Upload and process new document"""
    profile = UserProfile.objects.filter(user=request.user).first()
    
    # Check upload permission
    if not (request.user.is_superuser or (profile and profile.can_upload())):
        messages.error(request, 'You do not have permission to upload documents.')
        return redirect('documents')
    
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            document = form.save(commit=False)
            document.uploaded_by = request.user
            
            # Auto-fill department for department-level docs
            if document.access_level == 'department' and not document.department and profile:
                document.department = profile.department
            
            try:
                document.save()
                messages.success(request, f'Document "{document.title}" uploaded successfully. Processing...')
                
                # Process document in background (in production, use Celery)
                result = rag_pipeline.process_document(document)
                
                if result['success']:
                    messages.success(
                        request, 
                        f'Document processed: {result["chunks_created"]} chunks created in {result["processing_time"]:.1f}s'
                    )
                else:
                    messages.error(request, f'Processing failed: {result["error"]}')
                
                return redirect('document_detail', pk=document.pk)
                
            except Exception as e:
                logger.error(f"Error uploading document: {str(e)}")
                messages.error(request, f'Error uploading document: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DocumentUploadForm()
        
        # Pre-fill department if user has one
        if profile and profile.department:
            form.initial['department'] = profile.department
    
    context = {
        'form': form,
        'profile': profile,
    }
    
    return render(request, 'app_core/upload.html', context)

@login_required
def document_detail(request, pk):
    """View document details"""
    document = get_object_or_404(Document, pk=pk)
    
    # Check access permission
    if not document.can_access(request.user):
        return HttpResponseForbidden("You don't have permission to access this document.")
    
    # Get chunks
    chunks = DocumentChunk.objects.filter(document=document).order_by('chunk_index')
    
    context = {
        'document': document,
        'chunks': chunks,
    }
    
    return render(request, 'app_core/document_detail.html', context)

@login_required
def document_download(request, pk):
    """Download document file"""
    document = get_object_or_404(Document, pk=pk)
    
    # Check access permission
    if not document.can_access(request.user):
        return HttpResponseForbidden("You don't have permission to access this document.")
    
    return FileResponse(
        document.file.open('rb'),
        as_attachment=True,
        filename=document.file.name.split('/')[-1]
    )

@login_required
def document_delete(request, pk):
    """Delete document"""
    document = get_object_or_404(Document, pk=pk)
    
    # Only uploader, managers, or admins can delete
    profile = UserProfile.objects.filter(user=request.user).first()
    can_delete = (
        request.user.is_superuser or
        document.uploaded_by == request.user or
        (profile and profile.role in ['admin', 'manager'])
    )
    
    if not can_delete:
        return HttpResponseForbidden("You don't have permission to delete this document.")
    
    if request.method == 'POST':
        title = document.title
        
        # Remove from RAG pipeline
        rag_pipeline.remove_document(document)
        
        # Delete file and database entry
        document.file.delete()
        document.delete()
        
        messages.success(request, f'Document "{title}" deleted successfully.')
        return redirect('documents')
    
    return render(request, 'app_core/document_confirm_delete.html', {'document': document})

@login_required
def document_reindex(request, pk):
    """Reindex a document"""
    document = get_object_or_404(Document, pk=pk)
    
    # Check permission
    profile = UserProfile.objects.filter(user=request.user).first()
    if not (request.user.is_superuser or (profile and profile.role == 'admin')):
        return HttpResponseForbidden("You don't have permission to reindex documents.")
    
    if request.method == 'POST':
        try:
            result = rag_pipeline.reindex_document(document)
            
            if result['success']:
                messages.success(
                    request,
                    f'Document reindexed: {result["chunks_created"]} chunks in {result["processing_time"]:.1f}s'
                )
            else:
                messages.error(request, f'Reindexing failed: {result["error"]}')
        except Exception as e:
            messages.error(request, f'Error reindexing: {str(e)}')
        
        return redirect('document_detail', pk=pk)
    
    return render(request, 'app_core/document_confirm_reindex.html', {'document': document})

# ============= Chat / Query Views =============

@login_required
def chat(request):
    """Chat interface for querying documents"""
    form = QueryForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'app_core/chat.html', context)

@login_required
@require_http_methods(["POST"])
def query_api(request):
    """API endpoint for processing queries"""
    form = QueryForm(request.POST)
    
    if not form.is_valid():
        return JsonResponse({'error': 'Invalid form data'}, status=400)
    
    query_text = form.cleaned_data['query']
    top_k = form.cleaned_data.get('top_k') or settings.FAISS_TOP_K
    temperature = form.cleaned_data.get('temperature') or 0.7
    
    try:
        result = rag_pipeline.query(
            query_text=query_text,
            user=request.user,
            top_k=top_k,
            temperature=temperature
        )
        
        return JsonResponse({
            'success': True,
            'answer': result['answer'],
            'sources': result['sources'],
            'retrieval_time_ms': result['retrieval_time_ms'],
            'inference_time_ms': result['inference_time_ms'],
            'total_time_ms': result['total_time_ms'],
            'from_cache': result.get('from_cache', False),
        })
        
    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def query_history(request):
    """View query history"""
    queries = QueryLog.objects.filter(user=request.user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(queries, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'queries': page_obj,
    }
    
    return render(request, 'app_core/query_history.html', context)

# ============= System Management Views =============

@login_required
def system_status(request):
    """View system status"""
    profile = UserProfile.objects.filter(user=request.user).first()
    
    # Only admins can view system status
    if not (request.user.is_superuser or (profile and profile.role == 'admin')):
        return HttpResponseForbidden("You don't have permission to view system status.")
    
    status = rag_pipeline.get_system_status()
    
    # Additional statistics
    status['database'] = {
        'total_documents': Document.objects.count(),
        'total_chunks': DocumentChunk.objects.count(),
        'total_users': UserProfile.objects.count(),
        'total_queries': QueryLog.objects.count(),
    }
    
    context = {
        'status': status,
    }
    
    return render(request, 'app_core/system_status.html', context)

@login_required
@require_http_methods(["POST"])
def clear_cache(request):
    """Clear query cache"""
    profile = UserProfile.objects.filter(user=request.user).first()
    
    if not (request.user.is_superuser or (profile and profile.role == 'admin')):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        rag_pipeline.clear_cache()
        return JsonResponse({'success': True, 'message': 'Cache cleared successfully'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ============= User Management Views =============

@login_required
def profile(request):
    """View and edit user profile"""
    profile_obj = UserProfile.objects.filter(user=request.user).first()
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile_obj, user=request.user)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile_obj, user=request.user)
    
    context = {
        'form': form,
        'profile': profile_obj,
    }
    
    return render(request, 'app_core/profile.html', context)

@login_required
def user_list(request):
    """List all users (admin only)"""
    profile = UserProfile.objects.filter(user=request.user).first()
    
    if not (request.user.is_superuser or (profile and profile.can_manage_users())):
        return HttpResponseForbidden("You don't have permission to manage users.")
    
    users = UserProfile.objects.select_related('user').all().order_by('user__username')
    
    # Add document counts
    for user_profile in users:
        user_profile.document_count = Document.objects.filter(uploaded_by=user_profile.user).count()
        user_profile.query_count = QueryLog.objects.filter(user=user_profile.user).count()
    
    context = {
        'users': users,
    }
    
    return render(request, 'app_core/user_list.html', context)

@login_required
def user_create(request):
    """Create new user (admin only)"""
    profile = UserProfile.objects.filter(user=request.user).first()
    
    if not (request.user.is_superuser or (profile and profile.can_manage_users())):
        return HttpResponseForbidden("You don't have permission to create users.")
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.username}" created successfully.')
            return redirect('user_list')
    else:
        form = UserCreationForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'app_core/user_create.html', context)

# ============= API Views =============

@login_required
def api_check_ollama(request):
    """Check Ollama connection status"""
    from .ollama_client import ollama_client
    
    status = {
        'connected': ollama_client.check_connection(),
        'model_available': ollama_client.check_model_available(),
        'model_name': ollama_client.model,
        'host': ollama_client.host,
    }
    
    return JsonResponse(status)

@login_required
def api_embedding_status(request):
    """Check embedding model status"""
    from .cache_manager import embedding_cache
    
    status = embedding_cache.check_cache_status()
    
    return JsonResponse(status)


@login_required
def api_model_download_status(request):
    """Return the current embedding-model download state as JSON."""
    from .cache_manager import get_download_state, embedding_cache
    state = get_download_state()
    status = embedding_cache.check_cache_status()
    return JsonResponse({**state, **{
        'is_cached':    status['is_cached'],
        'cache_size_mb': status['cache_size_mb'],
        'model_name':   status['model_name'],
        'model_loaded': status['model_loaded'],
    }})
