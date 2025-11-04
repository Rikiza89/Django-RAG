"""
Complete RAG Pipeline
Orchestrates document processing, embedding, retrieval, and generation
"""
import logging
import time
from django.conf import settings
from .document_processor import DocumentProcessor
from .faiss_manager import faiss_manager
from .ollama_client import ollama_client
from .cache_manager import embedding_cache
from .models import Document, DocumentChunk, QueryLog

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Complete RAG pipeline for document ingestion and querying
    """
    
    def __init__(self):
        self.processor = DocumentProcessor()
        self.faiss = faiss_manager
        self.ollama = ollama_client
        self.embedding = embedding_cache
        
        # Simple query cache
        self.query_cache = {}
        self.max_cache_size = settings.QUERY_CACHE_SIZE if settings.ENABLE_QUERY_CACHE else 0
    
    def process_document(self, document):
        """
        Complete document processing pipeline
        
        Args:
            document (Document): Django Document model instance
        
        Returns:
            dict: Processing results
        """
        start_time = time.time()
        
        try:
            logger.info(f"Processing document: {document.title} (ID: {document.id})")
            
            # Step 1: Extract text
            file_path = document.file.path
            text = self.processor.extract_text(file_path, document.file_type)
            
            if not text or len(text) < 50:
                raise ValueError("Extracted text is too short or empty")
            
            # Step 2: Create text preview
            document.text_preview = self.processor.get_text_preview(text)
            
            # Step 3: Chunk text - ensure chunk_size and overlap are integers
            chunk_size = int(settings.CHUNK_SIZE) if isinstance(settings.CHUNK_SIZE, str) else settings.CHUNK_SIZE
            chunk_overlap = int(settings.CHUNK_OVERLAP) if isinstance(settings.CHUNK_OVERLAP, str) else settings.CHUNK_OVERLAP
            
            logger.info(f"Chunking with size={chunk_size}, overlap={chunk_overlap}")
            chunks = self.processor.chunk_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
            
            if not chunks:
                raise ValueError("No chunks created from document")
            
            # Step 4: Add to FAISS and create DocumentChunk records
            document_info = {
                'title': document.title,
                'access_level': document.access_level,
                'department': document.department,
            }
            
            num_added = self.faiss.add_documents(chunks, document.id, document_info)
            
            # Step 5: Create DocumentChunk database records
            for i, chunk in enumerate(chunks):
                DocumentChunk.objects.create(
                    document=document,
                    chunk_index=i,
                    content=chunk,
                    embedding_id=f"{document.id}_{i}"
                )
            
            # Update document status
            document.is_processed = True
            document.chunk_count = len(chunks)
            document.processing_error = None
            document.save()
            
            processing_time = time.time() - start_time
            
            logger.info(f"Document processed successfully in {processing_time:.2f}s: {num_added} chunks")
            
            return {
                'success': True,
                'chunks_created': num_added,
                'processing_time': processing_time,
                'text_length': len(text),
            }
            
        except Exception as e:
            logger.error(f"Error processing document {document.id}: {str(e)}")
            
            document.is_processed = False
            document.processing_error = str(e)
            document.save()
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time,
            }
    
    def query(self, query_text, user, top_k=None, temperature=0.7):
        """
        Complete RAG query pipeline
        
        Args:
            query_text (str): User query
            user (User): Django user for access control
            top_k (int): Number of documents to retrieve
            temperature (float): LLM temperature
        
        Returns:
            dict: Query results with answer and sources
        """
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = f"{user.id}:{query_text}"
            if settings.ENABLE_QUERY_CACHE and cache_key in self.query_cache:
                logger.info("Returning cached query result")
                cached = self.query_cache[cache_key]
                cached['from_cache'] = True
                return cached
            
            logger.info(f"Processing query from user {user.username}: {query_text[:100]}...")
            
            # Step 1: Retrieve relevant chunks
            retrieval_start = time.time()
            relevant_chunks = self.faiss.search(query_text, top_k=top_k, user=user)
            retrieval_time = (time.time() - retrieval_start) * 1000  # ms
            
            if not relevant_chunks:
                return {
                    'answer': "I couldn't find any relevant information in the available documents to answer your question.",
                    'sources': [],
                    'retrieval_time_ms': int(retrieval_time),
                    'inference_time_ms': 0,
                    'total_time_ms': int((time.time() - start_time) * 1000),
                }
            
            # Step 2: Prepare context
            context = [chunk['content'] for chunk in relevant_chunks[:top_k or settings.FAISS_TOP_K]]
            
            # Step 3: Generate answer with LLM
            inference_start = time.time()
            response = self.ollama.generate(
                prompt=query_text,
                context=context,
                temperature=temperature
            )
            inference_time = (time.time() - inference_start) * 1000  # ms
            
            # Step 4: Prepare source information
            sources = []
            seen_docs = set()
            
            for chunk in relevant_chunks:
                doc_id = chunk['document_id']
                if doc_id not in seen_docs:
                    seen_docs.add(doc_id)
                    sources.append({
                        'document_id': doc_id,
                        'document_title': chunk['document_title'],
                        'relevance_score': chunk['relevance_score'],
                    })
            
            total_time = (time.time() - start_time) * 1000  # ms
            
            result = {
                'answer': response['text'],
                'sources': sources,
                'retrieval_time_ms': int(retrieval_time),
                'inference_time_ms': int(inference_time),
                'total_time_ms': int(total_time),
                'model': response['model'],
                'from_cache': False,
            }
            
            # Log query
            QueryLog.objects.create(
                user=user,
                query_text=query_text,
                response_text=response['text'],
                source_documents=[s['document_id'] for s in sources],
                retrieval_time_ms=int(retrieval_time),
                inference_time_ms=int(inference_time),
                total_time_ms=int(total_time),
            )
            
            # Cache result
            if settings.ENABLE_QUERY_CACHE:
                self._cache_query(cache_key, result)
            
            logger.info(f"Query completed in {total_time:.0f}ms (retrieval: {retrieval_time:.0f}ms, inference: {inference_time:.0f}ms)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                'answer': f"An error occurred while processing your query: {str(e)}",
                'sources': [],
                'retrieval_time_ms': 0,
                'inference_time_ms': 0,
                'error': str(e),
                'total_time_ms': int((time.time() - start_time) * 1000),
            }
    
    def _cache_query(self, key, result):
        """Add query result to cache with LRU eviction"""
        if len(self.query_cache) >= self.max_cache_size:
            # Remove oldest entry (simple FIFO for now)
            oldest_key = next(iter(self.query_cache))
            del self.query_cache[oldest_key]
        
        self.query_cache[key] = result
    
    def reindex_document(self, document):
        """
        Remove and re-process a document
        
        Args:
            document (Document): Document to reindex
        
        Returns:
            dict: Reindexing results
        """
        logger.info(f"Reindexing document: {document.title} (ID: {document.id})")
        
        # Remove from FAISS
        self.faiss.remove_document(document.id)
        
        # Remove chunks from database
        DocumentChunk.objects.filter(document=document).delete()
        
        # Reprocess
        return self.process_document(document)
    
    def remove_document(self, document):
        """
        Remove document from index and database
        
        Args:
            document (Document): Document to remove
        """
        logger.info(f"Removing document: {document.title} (ID: {document.id})")
        
        # Remove from FAISS
        self.faiss.remove_document(document.id)
        
        # Remove chunks
        DocumentChunk.objects.filter(document=document).delete()
        
        # Mark as not processed
        document.is_processed = False
        document.chunk_count = 0
        document.save()
    
    def get_system_status(self):
        """
        Get status of all system components
        
        Returns:
            dict: System status information
        """
        status = {
            'embedding_model': self.embedding.check_cache_status(),
            'faiss_index': self.faiss.get_stats(),
            'ollama': {
                'connected': self.ollama.check_connection(),
                'model_available': self.ollama.check_model_available(),
                'model_name': self.ollama.model,
            },
            'documents': {
                'total': Document.objects.count(),
                'processed': Document.objects.filter(is_processed=True).count(),
                'failed': Document.objects.filter(is_processed=False, processing_error__isnull=False).count(),
            },
            'query_cache': {
                'enabled': settings.ENABLE_QUERY_CACHE,
                'size': len(self.query_cache),
                'max_size': self.max_cache_size,
            }
        }
        
        return status
    
    def clear_cache(self):
        """Clear query cache"""
        self.query_cache.clear()
        logger.info("Query cache cleared")


# Singleton instance
rag_pipeline = RAGPipeline()