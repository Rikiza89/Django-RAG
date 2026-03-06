"""
Code RAG Pipeline — orchestrates ingestion, retrieval, and generation
for the Coding IDE using Qwen 2.5 Coder + FAISS.
"""
import logging
import time
from django.conf import settings
from .code_processor import CodeProcessor
from .faiss_code_manager import code_faiss_manager
from .ollama_coder_client import ollama_coder_client
from .cache_manager import code_embedding_cache
from .models import CodeKnowledgeBase, CodeChunk, CodeQueryLog

logger = logging.getLogger(__name__)


class CodeRAGPipeline:
    """Full pipeline: ingest code → index → retrieve → generate."""

    def __init__(self):
        self.processor = CodeProcessor()
        self.faiss = code_faiss_manager
        self.llm = ollama_coder_client
        self.embeddings = code_embedding_cache

        self._query_cache: dict = {}
        self._max_cache = settings.CODE_QUERY_CACHE_SIZE if settings.CODE_ENABLE_QUERY_CACHE else 0

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def process_code_file(self, code_file: CodeKnowledgeBase) -> dict:
        """
        Full ingestion pipeline for a CodeKnowledgeBase instance.

        Returns: {'success': bool, 'chunks_created': int, 'processing_time': float}
        """
        start = time.time()
        try:
            logger.info(f"Processing code file: {code_file.title} (id={code_file.id})")

            # 1. Extract source text
            content = self.processor.extract_text(code_file.file.path)
            if not content or len(content) < 10:
                raise ValueError("File content is too short or empty")

            # 2. Preview
            code_file.content_preview = self.processor.get_preview(content)

            # 3. Chunk
            chunk_size = settings.CODE_CHUNK_SIZE
            overlap = settings.CODE_CHUNK_OVERLAP
            chunks_data = self.processor.chunk_code(content, chunk_size=chunk_size, overlap=overlap)
            if not chunks_data:
                raise ValueError("No chunks created from code file")

            # 4. Index in FAISS
            file_info = {
                'title': code_file.title,
                'language': code_file.language,
                'tags': code_file.tags,
            }
            num_added = self.faiss.add_chunks(chunks_data, code_file.id, file_info)

            # 5. Persist chunks in DB
            for i, chunk in enumerate(chunks_data):
                CodeChunk.objects.create(
                    code_file=code_file,
                    chunk_index=i,
                    content=chunk['content'],
                    embedding_id=f"code_{code_file.id}_{i}",
                    start_line=chunk.get('start_line', 0),
                    chunk_type=chunk.get('chunk_type', 'code'),
                )

            code_file.is_processed = True
            code_file.chunk_count = len(chunks_data)
            code_file.processing_error = None
            code_file.save()

            elapsed = time.time() - start
            logger.info(f"Code file processed in {elapsed:.2f}s — {num_added} chunks")
            return {'success': True, 'chunks_created': num_added, 'processing_time': elapsed}

        except Exception as e:
            logger.error(f"Error processing code file {code_file.id}: {e}")
            code_file.is_processed = False
            code_file.processing_error = str(e)
            code_file.save()
            return {'success': False, 'error': str(e), 'processing_time': time.time() - start}

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def query(self, query_text: str, user, top_k: int = None,
              language_filter: str = None, temperature: float = 0.2) -> dict:
        """
        Full RAG query: retrieve relevant code chunks → generate response.

        Returns dict with 'answer', 'sources', timing fields, etc.
        """
        start = time.time()
        try:
            cache_key = f"{user.id}:{language_filter or ''}:{query_text}"
            if settings.CODE_ENABLE_QUERY_CACHE and cache_key in self._query_cache:
                cached = dict(self._query_cache[cache_key])
                cached['from_cache'] = True
                return cached

            # 1. Retrieve
            t_ret = time.time()
            chunks = self.faiss.search(
                query_text,
                top_k=top_k or settings.CODE_FAISS_TOP_K,
                language_filter=language_filter or None,
            )
            retrieval_ms = int((time.time() - t_ret) * 1000)

            if not chunks:
                return {
                    'answer': (
                        "No relevant code was found in the knowledge base for your request.\n"
                        "Try uploading relevant source files first, or broaden your query."
                    ),
                    'sources': [],
                    'retrieval_time_ms': retrieval_ms,
                    'inference_time_ms': 0,
                    'total_time_ms': int((time.time() - start) * 1000),
                    'from_cache': False,
                }

            # 2. Generate
            context = [c['content'] for c in chunks]
            t_inf = time.time()
            response = self.llm.generate(
                prompt=query_text,
                context=context,
                language=language_filter,
                temperature=temperature,
            )
            inference_ms = int((time.time() - t_inf) * 1000)

            # 3. Build sources
            seen = set()
            sources = []
            for c in chunks:
                fid = c['code_file_id']
                if fid not in seen:
                    seen.add(fid)
                    sources.append({
                        'code_file_id': fid,
                        'title': c['title'],
                        'language': c['language'],
                        'relevance_score': c['relevance_score'],
                    })

            total_ms = int((time.time() - start) * 1000)

            result = {
                'answer': response['text'],
                'sources': sources,
                'retrieval_time_ms': retrieval_ms,
                'inference_time_ms': inference_ms,
                'total_time_ms': total_ms,
                'model': response['model'],
                'from_cache': False,
            }

            # 4. Log
            CodeQueryLog.objects.create(
                user=user,
                query_text=query_text,
                response_text=response['text'],
                source_files=[s['code_file_id'] for s in sources],
                language_filter=language_filter or '',
                retrieval_time_ms=retrieval_ms,
                inference_time_ms=inference_ms,
                total_time_ms=total_ms,
            )

            # 5. Cache
            if settings.CODE_ENABLE_QUERY_CACHE:
                self._cache(cache_key, result)

            logger.info(f"Code query done in {total_ms}ms (ret={retrieval_ms}ms, inf={inference_ms}ms)")
            return result

        except Exception as e:
            logger.error(f"Code RAG query error: {e}")
            return {
                'answer': f"An error occurred: {e}",
                'sources': [],
                'retrieval_time_ms': 0,
                'inference_time_ms': 0,
                'total_time_ms': int((time.time() - start) * 1000),
                'error': str(e),
            }

    def _cache(self, key: str, result: dict):
        if len(self._query_cache) >= self._max_cache:
            oldest = next(iter(self._query_cache))
            del self._query_cache[oldest]
        self._query_cache[key] = result

    # ------------------------------------------------------------------
    # Management
    # ------------------------------------------------------------------

    def reindex(self, code_file: CodeKnowledgeBase) -> dict:
        self.faiss.remove_file(code_file.id)
        CodeChunk.objects.filter(code_file=code_file).delete()
        return self.process_code_file(code_file)

    def remove(self, code_file: CodeKnowledgeBase):
        self.faiss.remove_file(code_file.id)
        CodeChunk.objects.filter(code_file=code_file).delete()
        code_file.is_processed = False
        code_file.chunk_count = 0
        code_file.save()

    def get_system_status(self) -> dict:
        return {
            'embedding_model': self.embeddings.check_cache_status(),
            'faiss_index': self.faiss.get_stats(),
            'llm': {
                'connected': self.llm.check_connection(),
                'model_available': self.llm.check_model_available(),
                'model_name': self.llm.model,
            },
            'code_files': {
                'total': CodeKnowledgeBase.objects.count(),
                'processed': CodeKnowledgeBase.objects.filter(is_processed=True).count(),
                'failed': CodeKnowledgeBase.objects.filter(
                    is_processed=False, processing_error__isnull=False
                ).count(),
            },
            'query_cache': {
                'enabled': settings.CODE_ENABLE_QUERY_CACHE,
                'size': len(self._query_cache),
                'max_size': self._max_cache,
            },
        }

    def clear_cache(self):
        self._query_cache.clear()


code_rag_pipeline = CodeRAGPipeline()
