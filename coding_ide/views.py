"""
Views for the Coding IDE RAG system.
"""
import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings

from .models import CodeKnowledgeBase, CodeChunk, CodeQueryLog, CodeLanguage
from .forms import CodeUploadForm, CodeQueryForm
from .rag_pipeline import code_rag_pipeline
from .ollama_coder_client import ollama_coder_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dashboard / IDE home
# ---------------------------------------------------------------------------

@login_required
def ide_dashboard(request):
    stats = {
        'total_files': CodeKnowledgeBase.objects.count(),
        'processed_files': CodeKnowledgeBase.objects.filter(is_processed=True).count(),
        'total_chunks': CodeChunk.objects.count(),
        'total_queries': CodeQueryLog.objects.filter(user=request.user).count(),
    }
    recent_files = CodeKnowledgeBase.objects.filter(is_processed=True).order_by('-uploaded_at')[:6]
    recent_queries = CodeQueryLog.objects.filter(user=request.user).order_by('-created_at')[:5]

    # Language distribution
    from django.db.models import Count
    lang_dist = (
        CodeKnowledgeBase.objects
        .filter(is_processed=True)
        .values('language')
        .annotate(count=Count('id'))
        .order_by('-count')[:8]
    )

    return render(request, 'coding_ide/dashboard.html', {
        'stats': stats,
        'recent_files': recent_files,
        'recent_queries': recent_queries,
        'lang_dist': list(lang_dist),
    })


# ---------------------------------------------------------------------------
# Knowledge base management
# ---------------------------------------------------------------------------

@login_required
def knowledge_base_list(request):
    qs = CodeKnowledgeBase.objects.all()

    language = request.GET.get('language', '')
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')

    if language:
        qs = qs.filter(language=language)
    if search:
        qs = qs.filter(title__icontains=search) | qs.filter(description__icontains=search) | qs.filter(tags__icontains=search)
    if status == 'processed':
        qs = qs.filter(is_processed=True)
    elif status == 'failed':
        qs = qs.filter(is_processed=False, processing_error__isnull=False)
    elif status == 'pending':
        qs = qs.filter(is_processed=False, processing_error__isnull=True)

    return render(request, 'coding_ide/knowledge_base.html', {
        'files': qs,
        'languages': CodeLanguage.choices,
        'current_language': language,
        'current_search': search,
        'current_status': status,
    })


@login_required
def upload_code(request):
    if request.method == 'POST':
        form = CodeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            code_file = form.save(commit=False)
            code_file.uploaded_by = request.user
            # Auto-generate hash for deduplication before first save
            if not code_file.file_hash:
                code_file.file_hash = code_file._calculate_hash()
            code_file.save()

            result = code_rag_pipeline.process_code_file(code_file)
            if result['success']:
                messages.success(
                    request,
                    f"'{code_file.title}' uploaded and indexed successfully "
                    f"({result['chunks_created']} chunks in {result['processing_time']:.1f}s)."
                )
            else:
                messages.warning(
                    request,
                    f"File saved but indexing failed: {result.get('error', 'Unknown error')}. "
                    "You can retry indexing from the knowledge base."
                )
            return redirect('coding_ide:knowledge_base')
    else:
        form = CodeUploadForm()

    return render(request, 'coding_ide/upload_code.html', {'form': form})


@login_required
def code_file_detail(request, pk):
    code_file = get_object_or_404(CodeKnowledgeBase, pk=pk)
    chunks = CodeChunk.objects.filter(code_file=code_file).order_by('chunk_index')
    return render(request, 'coding_ide/code_detail.html', {
        'code_file': code_file,
        'chunks': chunks,
    })


@login_required
@require_POST
def code_file_reindex(request, pk):
    code_file = get_object_or_404(CodeKnowledgeBase, pk=pk)
    result = code_rag_pipeline.reindex(code_file)
    if result['success']:
        messages.success(request, f"Reindexed '{code_file.title}' — {result['chunks_created']} chunks.")
    else:
        messages.error(request, f"Reindex failed: {result.get('error')}")
    return redirect('coding_ide:code_detail', pk=pk)


@login_required
@require_POST
def code_file_delete(request, pk):
    code_file = get_object_or_404(CodeKnowledgeBase, pk=pk)
    title = code_file.title
    code_rag_pipeline.remove(code_file)
    code_file.delete()
    messages.success(request, f"'{title}' removed from knowledge base.")
    return redirect('coding_ide:knowledge_base')


# ---------------------------------------------------------------------------
# Code IDE Chat
# ---------------------------------------------------------------------------

@login_required
def ide_chat(request):
    form = CodeQueryForm()
    return render(request, 'coding_ide/ide_chat.html', {'form': form})


@login_required
@require_POST
def ide_query_api(request):
    """AJAX endpoint that returns a JSON code generation response."""
    form = CodeQueryForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'success': False, 'error': str(form.errors)}, status=400)

    query = form.cleaned_data['query']
    lang = form.cleaned_data.get('language_filter') or None
    top_k = form.cleaned_data['top_k']
    temperature = form.cleaned_data['temperature']

    result = code_rag_pipeline.query(
        query_text=query,
        user=request.user,
        top_k=top_k,
        language_filter=lang,
        temperature=temperature,
    )

    return JsonResponse({
        'success': 'error' not in result,
        'answer': result.get('answer', ''),
        'sources': result.get('sources', []),
        'retrieval_time_ms': result.get('retrieval_time_ms', 0),
        'inference_time_ms': result.get('inference_time_ms', 0),
        'total_time_ms': result.get('total_time_ms', 0),
        'model': result.get('model', ''),
        'from_cache': result.get('from_cache', False),
        'error': result.get('error', ''),
    })


# ---------------------------------------------------------------------------
# Query history
# ---------------------------------------------------------------------------

@login_required
def code_query_history(request):
    logs = CodeQueryLog.objects.filter(user=request.user).order_by('-created_at')[:100]
    return render(request, 'coding_ide/query_history.html', {'logs': logs})


# ---------------------------------------------------------------------------
# System status API
# ---------------------------------------------------------------------------

@login_required
def ide_system_status(request):
    status = code_rag_pipeline.get_system_status()
    return render(request, 'coding_ide/system_status.html', {'status': status})


@login_required
def api_check_coder_model(request):
    return JsonResponse({
        'connected': ollama_coder_client.check_connection(),
        'model_available': ollama_coder_client.check_model_available(),
        'model': ollama_coder_client.model,
    })


@login_required
@require_POST
def api_clear_code_cache(request):
    code_rag_pipeline.clear_cache()
    return JsonResponse({'success': True, 'message': 'Code query cache cleared.'})
