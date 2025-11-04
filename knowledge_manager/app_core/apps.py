
"""
Django App Configuration for app_core
"""
from django.apps import AppConfig


class AppCoreConfig(AppConfig):
    """Configuration for the app_core application"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_core'
    verbose_name = 'Knowledge Management Core'
    
    def ready(self):
        """
        Initialize app when Django starts
        Can be used for signal registration, etc.
        """
        # Import signals here if you add any later
        # import app_core.signals
        pass