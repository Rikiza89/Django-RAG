"""
coding_ide/cache_manager.py
===========================
The Coding IDE reuses the SAME embedding model as app_core.
There is only one model in memory regardless of how many times this module
is imported.
"""
# Re-export the shared singleton — no second download, no second instance.
from app_core.cache_manager import embedding_cache as code_embedding_cache

__all__ = ['code_embedding_cache']
