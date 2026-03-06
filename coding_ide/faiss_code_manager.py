"""
FAISS Vector Store — Coding IDE
CPU-only, separate index from the Knowledge Hub.
Shares the same embedding model loaded by app_core.
"""
import logging
import os
import pickle

import faiss
import numpy as np
from pathlib import Path
from django.conf import settings

from .cache_manager import code_embedding_cache

logger = logging.getLogger(__name__)


class CodeFAISSManager:
    """Flat L2 FAISS index for code chunk retrieval — CPU only."""

    def __init__(self):
        self.index_path    = Path(settings.CODE_FAISS_INDEX_PATH)
        self.index_file    = self.index_path / 'index.faiss'
        self.metadata_path = self.index_path / 'metadata.pkl'

        self.index     = None
        self.metadata  = []
        self.dimension = None

        os.makedirs(self.index_path, exist_ok=True)
        self.load_index()

    # ------------------------------------------------------------------
    def initialize_index(self, dimension: int = None):
        if dimension is None:
            dimension = code_embedding_cache.get_embedding_dimension()
        self.dimension = dimension
        flat = faiss.IndexFlatL2(dimension)
        self.index = faiss.IndexIDMap(flat)
        self.metadata = []
        logger.info(f"Code FAISS index initialised (dim={dimension})")

    # ------------------------------------------------------------------
    def add_chunks(self, chunks_data: list, code_file_id: int,
                   file_info: dict) -> int:
        """
        chunks_data: list of dicts {'content', 'start_line', 'chunk_type'}
        """
        if not chunks_data:
            return 0
        if self.index is None:
            self.initialize_index()

        texts      = [c['content'] for c in chunks_data]
        embeddings = code_embedding_cache.embed_texts(texts)
        start_id   = len(self.metadata)
        ids        = np.arange(start_id, start_id + len(texts), dtype=np.int64)

        self.index.add_with_ids(embeddings, ids)

        for i, chunk in enumerate(chunks_data):
            self.metadata.append({
                'id':          int(ids[i]),
                'code_file_id': code_file_id,
                'chunk_index': i,
                'content':     chunk['content'],
                'start_line':  chunk.get('start_line', 0),
                'chunk_type':  chunk.get('chunk_type', 'code'),
                'title':       file_info.get('title', ''),
                'language':    file_info.get('language', ''),
                'tags':        file_info.get('tags', ''),
            })

        self.save_index()
        logger.info(f"Added {len(texts)} code chunks (total: {self.index.ntotal})")
        return len(texts)

    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = None,
               language_filter: str = None) -> list:
        if self.index is None or self.index.ntotal == 0:
            return []

        top_k     = top_k or settings.CODE_FAISS_TOP_K
        query_emb = code_embedding_cache.embed_texts([query])
        search_k  = min(top_k * 4, self.index.ntotal)
        distances, indices = self.index.search(query_emb, search_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx >= len(self.metadata):
                continue
            meta = self.metadata[idx]
            if language_filter and meta.get('language') != language_filter:
                continue
            results.append({
                'content':        meta['content'],
                'code_file_id':   meta['code_file_id'],
                'title':          meta['title'],
                'language':       meta['language'],
                'chunk_index':    meta['chunk_index'],
                'start_line':     meta['start_line'],
                'chunk_type':     meta['chunk_type'],
                'distance':       float(dist),
                'relevance_score': 1.0 / (1.0 + float(dist)),
            })
            if len(results) >= top_k:
                break

        return results

    # ------------------------------------------------------------------
    def remove_file(self, code_file_id: int) -> int:
        if self.index is None:
            return 0
        to_remove = [i for i, m in enumerate(self.metadata)
                     if m['code_file_id'] == code_file_id]
        if not to_remove:
            return 0
        self._rebuild_without(to_remove)
        return len(to_remove)

    def _rebuild_without(self, indices_to_remove: list):
        remaining = [m for i, m in enumerate(self.metadata)
                     if i not in indices_to_remove]
        if not remaining:
            self.initialize_index(self.dimension)
            return
        texts      = [m['content'] for m in remaining]
        embeddings = code_embedding_cache.embed_texts(texts)
        self.initialize_index(self.dimension)
        ids = np.arange(len(texts), dtype=np.int64)
        self.index.add_with_ids(embeddings, ids)
        for i, m in enumerate(remaining):
            m['id'] = i
        self.metadata = remaining
        self.save_index()

    # ------------------------------------------------------------------
    def save_index(self):
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_file))
        with open(self.metadata_path, 'wb') as f:
            pickle.dump({'metadata': self.metadata, 'dimension': self.dimension}, f)

    def load_index(self):
        try:
            if self.index_file.exists() and self.metadata_path.exists():
                self.index = faiss.read_index(str(self.index_file))
                with open(self.metadata_path, 'rb') as f:
                    data = pickle.load(f)
                    self.metadata  = data['metadata']
                    self.dimension = data['dimension']
                logger.info(f"Code FAISS index loaded ({len(self.metadata)} chunks)")
        except Exception as exc:
            logger.error(f"Could not load code FAISS index: {exc}")

    def get_stats(self) -> dict:
        stats = {
            'total_chunks': len(self.metadata),
            'index_size':   self.index.ntotal if self.index else 0,
            'dimension':    self.dimension,
            'gpu_enabled':  False,
            'index_file_size_mb': 0,
        }
        if self.index_file.exists():
            stats['index_file_size_mb'] = round(
                self.index_file.stat().st_size / (1024 * 1024), 2)
        return stats

    def clear_index(self):
        self.initialize_index(self.dimension)
        self.save_index()


code_faiss_manager = CodeFAISSManager()
