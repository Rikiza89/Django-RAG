"""
FAISS Vector Store — Knowledge Hub (app_core)
CPU-only index. faiss-gpu-cu12 has no Python 3.12+ wheels; CPU FAISS is
fast enough for this scale and keeps GPU VRAM free for Ollama.
"""
import logging
import os
import pickle

import faiss
import numpy as np
from pathlib import Path
from django.conf import settings

from .cache_manager import embedding_cache

logger = logging.getLogger(__name__)


class FAISSManager:
    """FAISS flat-L2 index with IDMap for document chunk retrieval."""

    def __init__(self):
        self.index_path   = Path(settings.FAISS_INDEX_PATH)
        self.index_file   = self.index_path / 'index.faiss'
        self.metadata_path = self.index_path / 'metadata.pkl'

        self.index    = None
        self.metadata = []
        self.dimension = None

        os.makedirs(self.index_path, exist_ok=True)
        self.load_index()

    # ------------------------------------------------------------------
    def initialize_index(self, dimension: int = None):
        if dimension is None:
            dimension = embedding_cache.get_embedding_dimension()
        self.dimension = dimension
        logger.info(f"Initialising FAISS index (dim={dimension})")
        flat = faiss.IndexFlatL2(dimension)
        self.index = faiss.IndexIDMap(flat)
        self.metadata = []

    # ------------------------------------------------------------------
    def add_documents(self, chunks: list, document_id: int,
                      document_info: dict) -> int:
        if not chunks:
            return 0
        if self.index is None:
            self.initialize_index()

        embeddings = embedding_cache.embed_texts(chunks)
        start_id   = len(self.metadata)
        chunk_ids  = np.arange(start_id, start_id + len(chunks), dtype=np.int64)

        self.index.add_with_ids(embeddings, chunk_ids)

        for i, chunk in enumerate(chunks):
            self.metadata.append({
                'id':             int(chunk_ids[i]),
                'document_id':    document_id,
                'chunk_index':    i,
                'content':        chunk,
                'document_title': document_info.get('title', ''),
                'access_level':   document_info.get('access_level', ''),
                'department':     document_info.get('department', ''),
            })

        logger.info(f"Added {len(chunks)} chunks (total: {self.index.ntotal})")
        self.save_index()
        return len(chunks)

    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = None, user=None) -> list:
        if self.index is None or self.index.ntotal == 0:
            return []

        top_k = top_k or settings.FAISS_TOP_K
        query_emb = embedding_cache.embed_texts([query])
        search_k  = min(top_k * 3, self.index.ntotal)
        distances, indices = self.index.search(query_emb, search_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx >= len(self.metadata):
                continue

            meta = self.metadata[idx]

            if user is not None:
                from .models import Document
                try:
                    doc = Document.objects.get(id=meta['document_id'])
                    if not doc.can_access(user):
                        continue
                except Document.DoesNotExist:
                    continue

            results.append({
                'content':        meta['content'],
                'document_id':    meta['document_id'],
                'document_title': meta['document_title'],
                'chunk_index':    meta['chunk_index'],
                'distance':       float(dist),
                'relevance_score': 1.0 / (1.0 + float(dist)),
            })
            if len(results) >= top_k:
                break

        logger.info(f"Search returned {len(results)} results")
        return results

    # ------------------------------------------------------------------
    def remove_document(self, document_id: int) -> int:
        if self.index is None:
            return 0
        to_remove = [i for i, m in enumerate(self.metadata)
                     if m['document_id'] == document_id]
        if not to_remove:
            return 0
        logger.info(f"Removing {len(to_remove)} chunks for doc {document_id}")
        self._rebuild_without(to_remove)
        return len(to_remove)

    def _rebuild_without(self, indices_to_remove: list):
        remaining = [m for i, m in enumerate(self.metadata)
                     if i not in indices_to_remove]
        if not remaining:
            self.initialize_index(self.dimension)
            return
        texts = [m['content'] for m in remaining]
        embeddings = embedding_cache.embed_texts(texts)
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
        logger.debug(f"FAISS index saved ({self.index.ntotal if self.index else 0} vectors)")

    def load_index(self):
        try:
            if self.index_file.exists() and self.metadata_path.exists():
                self.index = faiss.read_index(str(self.index_file))
                with open(self.metadata_path, 'rb') as f:
                    data = pickle.load(f)
                    self.metadata  = data['metadata']
                    self.dimension = data['dimension']
                logger.info(f"FAISS index loaded ({len(self.metadata)} chunks)")
        except Exception as exc:
            logger.error(f"Could not load FAISS index: {exc}")

    def get_stats(self) -> dict:
        stats = {
            'total_chunks': len(self.metadata),
            'index_size':   self.index.ntotal if self.index else 0,
            'dimension':    self.dimension,
            'index_file_size_mb': 0,
            'metadata_file_size_mb': 0,
            'gpu_enabled': False,      # always False — CPU only
        }
        if self.index_file.exists():
            stats['index_file_size_mb'] = round(
                self.index_file.stat().st_size / (1024 * 1024), 2)
        if self.metadata_path.exists():
            stats['metadata_file_size_mb'] = round(
                self.metadata_path.stat().st_size / (1024 * 1024), 2)
        return stats

    def clear_index(self):
        self.initialize_index(self.dimension)
        self.save_index()


faiss_manager = FAISSManager()
