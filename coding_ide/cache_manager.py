"""
Embedding model cache for the Coding IDE.
Uses a code-aware sentence-transformer model, GPU-enabled when available.
"""
import os
import gc
import logging
from pathlib import Path
from django.conf import settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class CodeEmbeddingCache:
    """Singleton embedding model cache for code RAG."""

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.cache_dir = settings.CODE_MODELS_CACHE_DIR
        self.model_name = settings.CODE_EMBEDDING_MODEL
        self.device = settings.CODE_EMBEDDING_DEVICE
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_model(self, force_reload=False):
        if self._model is not None and not force_reload:
            return self._model
        try:
            model_path = self._get_local_model_path()
            if self._is_cached():
                logger.info(f"Loading code embedding model from cache: {model_path}")
                self._model = SentenceTransformer(str(model_path), device=self.device)
            else:
                logger.info(f"Downloading code embedding model: {self.model_name}")
                self._model = SentenceTransformer(
                    self.model_name,
                    device=self.device,
                    cache_folder=str(self.cache_dir),
                )
                logger.info(f"Code embedding model cached at: {self.cache_dir}")
            return self._model
        except Exception as e:
            logger.error(f"Error loading code embedding model: {e}")
            raise

    def _get_local_model_path(self):
        model_name_safe = self.model_name.replace('/', '--')
        base_path = Path(self.cache_dir) / f"models--{model_name_safe}"
        snapshot_dir = base_path / "snapshots"
        if snapshot_dir.exists():
            snaps = sorted(snapshot_dir.glob("*"), key=os.path.getmtime, reverse=True)
            if snaps:
                return snaps[0]
        for p in [base_path, Path(self.cache_dir) / self.model_name.split('/')[-1]]:
            if p.exists():
                return p
        return base_path

    def _is_cached(self):
        path = self._get_local_model_path()
        if not path.exists():
            return False
        has_weights = any((path / f).exists() for f in ['pytorch_model.bin', 'model.safetensors'])
        return has_weights and (path / 'config.json').exists()

    def get_dimension(self):
        return self.get_model().get_sentence_embedding_dimension()

    def embed_texts(self, texts, batch_size=None, show_progress=False):
        if not texts:
            return None
        model = self.get_model()
        batch_size = batch_size or settings.CODE_EMBEDDING_BATCH_SIZE
        logger.info(f"Embedding {len(texts)} code chunks (device={self.device})")
        return model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            device=self.device,
        )

    def clear_memory(self):
        if self._model is not None:
            del self._model
            self._model = None
            gc.collect()

    def status(self):
        path = self._get_local_model_path()
        size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file()) if path.exists() else 0
        return {
            'model_name': self.model_name,
            'is_cached': self._is_cached(),
            'cache_path': str(path),
            'cache_size_mb': round(size / (1024 * 1024), 2),
            'device': self.device,
            'model_loaded': self._model is not None,
        }


code_embedding_cache = CodeEmbeddingCache()
