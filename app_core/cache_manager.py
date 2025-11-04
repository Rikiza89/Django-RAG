"""
Cache Manager for Embedding Models
Ensures models are downloaded once and reused offline
"""
import os
import logging
from pathlib import Path
from django.conf import settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingModelCache:
    """
    Manages local caching of embedding models for offline use
    """
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.cache_dir = settings.MODELS_CACHE_DIR
        self.model_name = settings.EMBEDDING_MODEL
        self.device = settings.EMBEDDING_DEVICE
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_model(self, force_reload=False):
        """
        Get or load the embedding model from cache
        
        Args:
            force_reload (bool): Force reload model even if already loaded
        
        Returns:
            SentenceTransformer: The embedding model
        """
        if self._model is not None and not force_reload:
            logger.info("Using cached embedding model from memory")
            return self._model
        
        try:
            model_path = self._get_local_model_path()
            
            if self._is_model_cached():
                logger.info(f"Loading embedding model from local cache: {model_path}")
                self._model = SentenceTransformer(
                    str(model_path),
                    device=self.device
                )
            else:
                logger.info(f"Downloading and caching embedding model: {self.model_name}")
                logger.warning("This requires internet connection for first-time download")
                
                # Download and cache the model
                self._model = SentenceTransformer(
                    self.model_name,
                    device=self.device,
                    cache_folder=str(self.cache_dir)
                )
                
                logger.info(f"Model successfully cached at: {self.cache_dir}")
            
            return self._model
            
        except Exception as e:
            logger.error(f"Error loading embedding model: {str(e)}")
            raise
    
    def _get_local_model_path(self):
        """Locate the correct local path for the cached model"""
        model_name_safe = self.model_name.replace('/', '--')
        base_path = self.cache_dir / f"models--{model_name_safe}"

        # Check for snapshot structure
        snapshot_dir = base_path / "snapshots"
        if snapshot_dir.exists():
            snapshots = sorted(snapshot_dir.glob("*"), key=os.path.getmtime, reverse=True)
            if snapshots:
                return snapshots[0]  # use the latest snapshot

        # fallback to simple model folder
        possible_folders = [
            base_path,
            self.cache_dir / self.model_name.replace('/', '_'),
            self.cache_dir / self.model_name.split('/')[-1],
        ]

        for folder in possible_folders:
            if folder.exists():
                return folder

        return base_path

    
    def _is_model_cached(self):
        """Check if model is already downloaded and cached"""
        model_path = self._get_local_model_path()
        if not model_path.exists():
            return False

        has_model_file = any(
            (model_path / fname).exists()
            for fname in ['pytorch_model.bin', 'model.safetensors']
        )

        if not has_model_file or not (model_path / 'config.json').exists():
            return False

        logger.info(f"Model found in cache: {model_path}")
        return True
    
    def get_embedding_dimension(self):
        """Get the dimension of embeddings produced by the model"""
        model = self.get_model()
        return model.get_sentence_embedding_dimension()
    
    def embed_texts(self, texts, batch_size=None, show_progress=False):
        """
        Generate embeddings for a list of texts
        
        Args:
            texts (list): List of text strings to embed
            batch_size (int): Batch size for processing
            show_progress (bool): Show progress bar
        
        Returns:
            numpy.ndarray: Array of embeddings
        """
        if not texts:
            return None
        
        model = self.get_model()
        batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE
        
        logger.info(f"Generating embeddings for {len(texts)} texts (batch_size={batch_size})")
        
        try:
            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                device=self.device
            )
            
            logger.info(f"Successfully generated {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    def clear_memory(self):
        """Clear model from memory to free RAM"""
        if self._model is not None:
            logger.info("Clearing embedding model from memory")
            del self._model
            self._model = None
            
            # Force garbage collection
            import gc
            gc.collect()
    
    def check_cache_status(self):
        """
        Get information about cache status
        
        Returns:
            dict: Cache status information
        """
        is_cached = self._is_model_cached()
        model_path = self._get_local_model_path()
        
        cache_size = 0
        if model_path.exists():
            cache_size = sum(
                f.stat().st_size 
                for f in model_path.rglob('*') 
                if f.is_file()
            )
        
        return {
            'is_cached': is_cached,
            'model_name': self.model_name,
            'cache_path': str(model_path),
            'cache_size_mb': round(cache_size / (1024 * 1024), 2),
            'device': self.device,
            'model_loaded': self._model is not None
        }


# Singleton instance
embedding_cache = EmbeddingModelCache()