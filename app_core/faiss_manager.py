"""
FAISS Vector Store Manager
Handles vector storage, retrieval, and index management
"""
import os
import logging
import pickle
import numpy as np
import faiss
from pathlib import Path
from django.conf import settings
from .cache_manager import embedding_cache

logger = logging.getLogger(__name__)


def _get_gpu_resource():
    """Return a FAISS GPU resource if CUDA is available and faiss-gpu is installed."""
    use_gpu = getattr(settings, 'FAISS_USE_GPU', False)
    if not use_gpu:
        return None
    try:
        res = faiss.StandardGpuResources()
        logger.info("FAISS GPU resource initialised")
        return res
    except AttributeError:
        logger.warning("faiss-gpu not installed; falling back to CPU FAISS")
        return None


class FAISSManager:
    """
    Manages FAISS index for document embeddings.
    Supports GPU acceleration when FAISS_USE_GPU=True and faiss-gpu is installed.
    """

    def __init__(self):
        self.index_path = settings.FAISS_INDEX_PATH
        self.metadata_path = self.index_path / 'metadata.pkl'
        self.index_file = self.index_path / 'index.faiss'

        self.index = None
        self._gpu_res = _get_gpu_resource()
        self.metadata = []  # List of dicts with chunk info
        self.dimension = None

        # Ensure directory exists
        os.makedirs(self.index_path, exist_ok=True)

        # Load existing index if available
        self.load_index()
    
    def initialize_index(self, dimension=None):
        """
        Initialize a new FAISS index
        
        Args:
            dimension (int): Dimension of embedding vectors
        """
        if dimension is None:
            dimension = embedding_cache.get_embedding_dimension()
        
        self.dimension = dimension

        # Build a flat L2 index and wrap with IDMap
        logger.info(f"Initializing FAISS Flat index with dimension {dimension}")
        cpu_index = faiss.IndexFlatL2(dimension)
        cpu_index = faiss.IndexIDMap(cpu_index)

        # Move to GPU if a GPU resource is available
        if self._gpu_res is not None:
            try:
                self.index = faiss.index_cpu_to_gpu(self._gpu_res, 0, cpu_index)
                logger.info("FAISS index moved to GPU")
            except Exception as e:
                logger.warning(f"Failed to move FAISS index to GPU: {e}; using CPU")
                self.index = cpu_index
        else:
            self.index = cpu_index

        self.metadata = []
        logger.info("FAISS index initialized successfully")
    
    def add_documents(self, chunks, document_id, document_info):
        """
        Add document chunks to FAISS index
        
        Args:
            chunks (list): List of text chunks
            document_id (int): Database document ID
            document_info (dict): Document metadata (title, access_level, etc.)
        
        Returns:
            int: Number of chunks added
        """
        if not chunks:
            logger.warning("No chunks to add")
            return 0
        
        # Initialize index if needed
        if self.index is None:
            self.initialize_index()
        
        try:
            # Generate embeddings
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            embeddings = embedding_cache.embed_texts(chunks)
            
            # Generate IDs for chunks
            start_id = len(self.metadata)
            chunk_ids = np.arange(start_id, start_id + len(chunks), dtype=np.int64)
            
            # Add to FAISS index
            self.index.add_with_ids(embeddings, chunk_ids)
            
            # Store metadata
            for i, chunk in enumerate(chunks):
                self.metadata.append({
                    'id': int(chunk_ids[i]),
                    'document_id': document_id,
                    'chunk_index': i,
                    'content': chunk,
                    'document_title': document_info.get('title', ''),
                    'access_level': document_info.get('access_level', ''),
                    'department': document_info.get('department', ''),
                })
            
            logger.info(f"Added {len(chunks)} chunks to FAISS index (total: {self.index.ntotal})")
            
            # Save index
            self.save_index()
            
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Error adding documents to FAISS: {str(e)}")
            raise
    
    def search(self, query, top_k=None, user=None):
        """
        Search for relevant document chunks
        
        Args:
            query (str): Search query
            top_k (int): Number of results to return
            user (User): Django user for access control
        
        Returns:
            list: List of dicts with chunk content and metadata
        """
        if self.index is None or self.index.ntotal == 0:
            logger.warning("FAISS index is empty")
            return []
        
        top_k = top_k or settings.FAISS_TOP_K
        
        try:
            # Generate query embedding
            logger.info(f"Searching for: {query[:100]}...")
            query_embedding = embedding_cache.embed_texts([query])
            
            # Search in FAISS (retrieve more than needed for filtering)
            search_k = min(top_k * 3, self.index.ntotal)
            distances, indices = self.index.search(query_embedding, search_k)
            
            # Get results
            results = []
            for distance, idx in zip(distances[0], indices[0]):
                if idx == -1:  # FAISS returns -1 for empty slots
                    continue
                
                if idx >= len(self.metadata):
                    continue
                
                chunk_meta = self.metadata[idx]
                
                # Apply access control if user provided
                if user is not None:
                    from .models import Document
                    try:
                        doc = Document.objects.get(id=chunk_meta['document_id'])
                        if not doc.can_access(user):
                            continue
                    except Document.DoesNotExist:
                        continue
                
                results.append({
                    'content': chunk_meta['content'],
                    'document_id': chunk_meta['document_id'],
                    'document_title': chunk_meta['document_title'],
                    'chunk_index': chunk_meta['chunk_index'],
                    'distance': float(distance),
                    'relevance_score': 1.0 / (1.0 + float(distance))  # Convert distance to similarity
                })
                
                if len(results) >= top_k:
                    break
            
            logger.info(f"Found {len(results)} relevant chunks")
            return results
            
        except Exception as e:
            logger.error(f"Error searching FAISS index: {str(e)}")
            raise
    
    def remove_document(self, document_id):
        """
        Remove all chunks of a document from the index
        
        Args:
            document_id (int): Database document ID
        
        Returns:
            int: Number of chunks removed
        """
        if self.index is None:
            return 0
        
        # Find indices to remove
        indices_to_remove = [
            i for i, meta in enumerate(self.metadata)
            if meta['document_id'] == document_id
        ]
        
        if not indices_to_remove:
            return 0
        
        logger.info(f"Removing {len(indices_to_remove)} chunks for document {document_id}")
        
        # FAISS doesn't support direct deletion, so we need to rebuild
        # For small datasets, this is acceptable
        self._rebuild_index_without(indices_to_remove)
        
        logger.info(f"Removed document {document_id} from index")
        return len(indices_to_remove)
    
    def _rebuild_index_without(self, indices_to_remove):
        """Rebuild index excluding specified indices"""
        # Keep metadata and get embeddings for remaining chunks
        remaining_metadata = [
            meta for i, meta in enumerate(self.metadata)
            if i not in indices_to_remove
        ]
        
        if not remaining_metadata:
            # Index is now empty
            self.initialize_index(self.dimension)
            return
        
        # Get chunks to re-embed
        remaining_chunks = [meta['content'] for meta in remaining_metadata]
        
        # Regenerate embeddings
        embeddings = embedding_cache.embed_texts(remaining_chunks)
        
        # Create new index
        self.initialize_index(self.dimension)
        
        # Add back remaining chunks
        chunk_ids = np.arange(len(remaining_chunks), dtype=np.int64)
        self.index.add_with_ids(embeddings, chunk_ids)
        
        # Update metadata with new IDs
        for i, meta in enumerate(remaining_metadata):
            meta['id'] = i
        
        self.metadata = remaining_metadata
        self.save_index()
    
    def save_index(self):
        """Save FAISS index and metadata to disk (converts GPU index to CPU first)."""
        try:
            if self.index is not None:
                # GPU indexes must be cloned to CPU before writing
                try:
                    cpu_index = faiss.index_gpu_to_cpu(self.index)
                except AttributeError:
                    cpu_index = self.index  # already CPU
                faiss.write_index(cpu_index, str(self.index_file))
                logger.info(f"FAISS index saved to {self.index_file}")
            
            with open(self.metadata_path, 'wb') as f:
                pickle.dump({
                    'metadata': self.metadata,
                    'dimension': self.dimension
                }, f)
            logger.info(f"Metadata saved to {self.metadata_path}")
            
        except Exception as e:
            logger.error(f"Error saving FAISS index: {str(e)}")
            raise
    
    def load_index(self):
        """Load FAISS index and metadata from disk, then optionally move to GPU."""
        try:
            if self.index_file.exists() and self.metadata_path.exists():
                # Load index from disk (always CPU first)
                cpu_index = faiss.read_index(str(self.index_file))
                logger.info(f"FAISS index loaded from {self.index_file}")

                # Move to GPU if available
                if self._gpu_res is not None:
                    try:
                        self.index = faiss.index_cpu_to_gpu(self._gpu_res, 0, cpu_index)
                        logger.info("Loaded FAISS index moved to GPU")
                    except Exception as e:
                        logger.warning(f"GPU transfer failed: {e}; keeping on CPU")
                        self.index = cpu_index
                else:
                    self.index = cpu_index
                
                # Load metadata
                with open(self.metadata_path, 'rb') as f:
                    data = pickle.load(f)
                    self.metadata = data['metadata']
                    self.dimension = data['dimension']
                
                logger.info(f"Loaded {len(self.metadata)} chunks from metadata")
                
            else:
                logger.info("No existing FAISS index found")
                
        except Exception as e:
            logger.error(f"Error loading FAISS index: {str(e)}")
            # Don't raise - allow initialization of new index
    
    def get_stats(self):
        """
        Get statistics about the FAISS index
        
        Returns:
            dict: Index statistics
        """
        stats = {
            'total_chunks': len(self.metadata) if self.metadata else 0,
            'index_size': self.index.ntotal if self.index else 0,
            'dimension': self.dimension,
            'index_file_size_mb': 0,
            'metadata_file_size_mb': 0,
        }
        
        if self.index_file.exists():
            stats['index_file_size_mb'] = round(
                self.index_file.stat().st_size / (1024 * 1024), 2
            )
        
        if self.metadata_path.exists():
            stats['metadata_file_size_mb'] = round(
                self.metadata_path.stat().st_size / (1024 * 1024), 2
            )
        
        return stats
    
    def clear_index(self):
        """Clear the entire FAISS index"""
        logger.warning("Clearing FAISS index")
        self.initialize_index(self.dimension)
        self.save_index()


# Singleton instance - instantiate after class definition
faiss_manager = FAISSManager()