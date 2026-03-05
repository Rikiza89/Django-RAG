"""
FAISS Vector Store for Code RAG.
Separate index from the main document RAG, GPU-enabled when available.
"""
import os
import pickle
import logging
import numpy as np
import faiss
from pathlib import Path
from django.conf import settings
from .cache_manager import code_embedding_cache

logger = logging.getLogger(__name__)


def _get_gpu_resource():
    use_gpu = getattr(settings, 'FAISS_USE_GPU', False)
    if not use_gpu:
        return None
    try:
        res = faiss.StandardGpuResources()
        logger.info("Code FAISS GPU resource initialised")
        return res
    except AttributeError:
        logger.warning("faiss-gpu not installed; code FAISS will run on CPU")
        return None


class CodeFAISSManager:
    """Manages a FAISS index dedicated to code embeddings."""

    def __init__(self):
        self.index_path = Path(settings.CODE_FAISS_INDEX_PATH)
        self.metadata_path = self.index_path / 'metadata.pkl'
        self.index_file = self.index_path / 'index.faiss'

        self.index = None
        self._gpu_res = _get_gpu_resource()
        self.metadata = []
        self.dimension = None

        os.makedirs(self.index_path, exist_ok=True)
        self.load_index()

    def initialize_index(self, dimension=None):
        if dimension is None:
            dimension = code_embedding_cache.get_dimension()
        self.dimension = dimension

        cpu_index = faiss.IndexFlatL2(dimension)
        cpu_index = faiss.IndexIDMap(cpu_index)

        if self._gpu_res is not None:
            try:
                self.index = faiss.index_cpu_to_gpu(self._gpu_res, 0, cpu_index)
                logger.info("Code FAISS index moved to GPU")
            except Exception as e:
                logger.warning(f"GPU transfer failed: {e}; using CPU")
                self.index = cpu_index
        else:
            self.index = cpu_index

        self.metadata = []
        logger.info(f"Code FAISS index initialised (dim={dimension})")

    def add_chunks(self, chunks_data: list[dict], code_file_id: int, file_info: dict) -> int:
        """
        Add code chunks to the index.
        chunks_data: list of {'content', 'start_line', 'chunk_type'}
        """
        if not chunks_data:
            return 0
        if self.index is None:
            self.initialize_index()

        texts = [c['content'] for c in chunks_data]
        embeddings = code_embedding_cache.embed_texts(texts)

        start_id = len(self.metadata)
        ids = np.arange(start_id, start_id + len(texts), dtype=np.int64)
        self.index.add_with_ids(embeddings, ids)

        for i, chunk in enumerate(chunks_data):
            self.metadata.append({
                'id': int(ids[i]),
                'code_file_id': code_file_id,
                'chunk_index': i,
                'content': chunk['content'],
                'start_line': chunk.get('start_line', 0),
                'chunk_type': chunk.get('chunk_type', 'code'),
                'title': file_info.get('title', ''),
                'language': file_info.get('language', ''),
                'tags': file_info.get('tags', ''),
            })

        self.save_index()
        logger.info(f"Added {len(texts)} code chunks (total: {self.index.ntotal})")
        return len(texts)

    def search(self, query: str, top_k: int = None, language_filter: str = None) -> list[dict]:
        if self.index is None or self.index.ntotal == 0:
            return []

        top_k = top_k or settings.CODE_FAISS_TOP_K
        query_emb = code_embedding_cache.embed_texts([query])
        search_k = min(top_k * 4, self.index.ntotal)
        distances, indices = self.index.search(query_emb, search_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx >= len(self.metadata):
                continue
            meta = self.metadata[idx]
            if language_filter and meta.get('language') != language_filter:
                continue
            results.append({
                'content': meta['content'],
                'code_file_id': meta['code_file_id'],
                'title': meta['title'],
                'language': meta['language'],
                'chunk_index': meta['chunk_index'],
                'start_line': meta['start_line'],
                'chunk_type': meta['chunk_type'],
                'distance': float(dist),
                'relevance_score': 1.0 / (1.0 + float(dist)),
            })
            if len(results) >= top_k:
                break

        logger.info(f"Code search returned {len(results)} results")
        return results

    def remove_file(self, code_file_id: int) -> int:
        if self.index is None:
            return 0
        to_remove = [i for i, m in enumerate(self.metadata) if m['code_file_id'] == code_file_id]
        if not to_remove:
            return 0
        self._rebuild_without(to_remove)
        return len(to_remove)

    def _rebuild_without(self, indices_to_remove: list[int]):
        remaining = [m for i, m in enumerate(self.metadata) if i not in indices_to_remove]
        if not remaining:
            self.initialize_index(self.dimension)
            return
        texts = [m['content'] for m in remaining]
        embeddings = code_embedding_cache.embed_texts(texts)
        self.initialize_index(self.dimension)
        ids = np.arange(len(texts), dtype=np.int64)
        self.index.add_with_ids(embeddings, ids)
        for i, m in enumerate(remaining):
            m['id'] = i
        self.metadata = remaining
        self.save_index()

    def save_index(self):
        try:
            if self.index is not None:
                try:
                    cpu_index = faiss.index_gpu_to_cpu(self.index)
                except AttributeError:
                    cpu_index = self.index
                faiss.write_index(cpu_index, str(self.index_file))
            with open(self.metadata_path, 'wb') as f:
                pickle.dump({'metadata': self.metadata, 'dimension': self.dimension}, f)
        except Exception as e:
            logger.error(f"Error saving code FAISS index: {e}")
            raise

    def load_index(self):
        try:
            if self.index_file.exists() and self.metadata_path.exists():
                cpu_index = faiss.read_index(str(self.index_file))
                if self._gpu_res is not None:
                    try:
                        self.index = faiss.index_cpu_to_gpu(self._gpu_res, 0, cpu_index)
                        logger.info("Code FAISS index loaded and moved to GPU")
                    except Exception as e:
                        logger.warning(f"GPU load failed: {e}")
                        self.index = cpu_index
                else:
                    self.index = cpu_index
                with open(self.metadata_path, 'rb') as f:
                    data = pickle.load(f)
                    self.metadata = data['metadata']
                    self.dimension = data['dimension']
                logger.info(f"Loaded {len(self.metadata)} code chunks from index")
            else:
                logger.info("No existing code FAISS index found")
        except Exception as e:
            logger.error(f"Error loading code FAISS index: {e}")

    def get_stats(self) -> dict:
        return {
            'total_chunks': len(self.metadata),
            'index_size': self.index.ntotal if self.index else 0,
            'dimension': self.dimension,
            'gpu_enabled': self._gpu_res is not None,
            'index_file_size_mb': round(self.index_file.stat().st_size / (1024 * 1024), 2) if self.index_file.exists() else 0,
        }

    def clear_index(self):
        self.initialize_index(self.dimension)
        self.save_index()


code_faiss_manager = CodeFAISSManager()
