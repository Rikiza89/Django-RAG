from django.apps import AppConfig


class AppCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_core'
    verbose_name = 'Knowledge Hub'

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(_post_migrate_check, sender=self)


def _post_migrate_check(sender, **kwargs):
    """
    After migrations, check whether the embedding model is cached.
    If not, print a one-liner hint — does NOT auto-download.
    """
    try:
        from django.conf import settings
        from app_core.cache_manager import embedding_cache
        status = embedding_cache.check_cache_status()
        if not status['is_cached']:
            print(
                "\n[cache_models] Embedding model not yet downloaded.\n"
                f"  Model : {settings.EMBEDDING_MODEL}\n"
                "  Run  :  python manage.py cache_models\n"
                "  (Required before document upload or code indexing)\n"
            )
    except Exception:
        pass
