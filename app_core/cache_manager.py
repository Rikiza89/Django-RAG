"""
Shared Embedding Model Cache
============================
Single embedding model instance used by BOTH app_core and coding_ide.
• Always runs on CPU — keeps GPU VRAM free for Ollama.
• Tracks download progress so the UI can show status.
• Thread-safe singleton using a module-level lock.
"""
import gc
import logging
import os
import threading
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Download progress registry (used by /api/model-download-status/)
# ---------------------------------------------------------------------------
_download_state = {
    'status':   'idle',       # idle | downloading | ready | error
    'progress': 0,            # 0-100
    'message':  '',
    'model':    '',
    'size_mb':  0,
}
_state_lock = threading.Lock()


def get_download_state() -> dict:
    with _state_lock:
        return dict(_download_state)


def _set_state(**kwargs):
    with _state_lock:
        _download_state.update(kwargs)


# ---------------------------------------------------------------------------
# Singleton cache
# ---------------------------------------------------------------------------
class EmbeddingModelCache:
    """
    Loads and caches the sentence-transformers embedding model.
    Both app_core and coding_ide import the ``embedding_cache`` singleton
    from this module — the model is loaded only once.
    """

    _instance = None
    _model = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self.device = 'cpu'                          # Always CPU
        self.batch_size = settings.EMBEDDING_BATCH_SIZE
        self.cache_dir = Path(settings.MODELS_CACHE_DIR)
        os.makedirs(self.cache_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def get_model(self, force_reload: bool = False):
        """Return the loaded model, downloading it if necessary."""
        if self._model is not None and not force_reload:
            return self._model

        with self._lock:
            # Double-check after acquiring lock
            if self._model is not None and not force_reload:
                return self._model

            _set_state(status='downloading', progress=5,
                       message='Checking local cache…', model=self.model_name)

            try:
                from sentence_transformers import SentenceTransformer

                local_path = self._local_model_path()

                if self._is_cached(local_path):
                    logger.info(f"Loading embedding model from cache: {local_path}")
                    _set_state(status='downloading', progress=60,
                               message='Loading from local cache…')
                    self._model = SentenceTransformer(str(local_path), device=self.device)
                else:
                    logger.info(f"Downloading embedding model: {self.model_name}")
                    _set_state(status='downloading', progress=10,
                               message=f'Downloading {self.model_name}… (first run only)')
                    self._model = SentenceTransformer(
                        self.model_name,
                        device=self.device,
                        cache_folder=str(self.cache_dir),
                    )
                    logger.info(f"Model cached at: {self.cache_dir}")

                _set_state(status='ready', progress=100,
                           message='Model ready',
                           size_mb=self._cache_size_mb())
                logger.info(f"Embedding model ready (device={self.device})")
                return self._model

            except Exception as exc:
                _set_state(status='error', progress=0, message=str(exc))
                logger.error(f"Failed to load embedding model: {exc}")
                raise

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _local_model_path(self) -> Path:
        safe = self.model_name.replace('/', '--')
        base = self.cache_dir / f"models--{safe}"

        snap = base / 'snapshots'
        if snap.exists():
            snaps = sorted(snap.glob('*'), key=os.path.getmtime, reverse=True)
            if snaps:
                return snaps[0]

        for candidate in [base, self.cache_dir / self.model_name.split('/')[-1]]:
            if candidate.exists():
                return candidate
        return base

    def _is_cached(self, path: Path) -> bool:
        if not path.exists():
            return False
        has_weights = any((path / f).exists()
                          for f in ['pytorch_model.bin', 'model.safetensors'])
        return has_weights and (path / 'config.json').exists()

    def _cache_size_mb(self) -> float:
        p = self._local_model_path()
        if not p.exists():
            return 0.0
        total = sum(f.stat().st_size for f in p.rglob('*') if f.is_file())
        return round(total / (1024 * 1024), 1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_embedding_dimension(self) -> int:
        return self.get_model().get_sentence_embedding_dimension()

    def embed_texts(self, texts: list, batch_size: int = None,
                    show_progress: bool = False):
        """Encode a list of strings and return a numpy array of embeddings."""
        if not texts:
            return None
        model = self.get_model()
        bs = batch_size or self.batch_size
        logger.debug(f"Embedding {len(texts)} texts on CPU (batch={bs})")
        return model.encode(
            texts,
            batch_size=bs,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            device=self.device,
        )

    def clear_memory(self):
        with self._lock:
            if self._model is not None:
                del self._model
                self._model = None
                gc.collect()
                logger.info("Embedding model cleared from memory")

    def check_cache_status(self) -> dict:
        """Return a status dict (used by views and the setup command)."""
        local = self._local_model_path()
        cached = self._is_cached(local)
        return {
            'model_name':    self.model_name,
            'is_cached':     cached,
            'model_loaded':  self._model is not None,
            'cache_path':    str(local),
            'cache_size_mb': self._cache_size_mb() if cached else 0,
            'device':        self.device,
            'download_state': get_download_state(),
        }


# ---------------------------------------------------------------------------
# Module-level singleton — import this everywhere
# ---------------------------------------------------------------------------
embedding_cache = EmbeddingModelCache()
