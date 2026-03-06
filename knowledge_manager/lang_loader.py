"""
knowledge_manager/lang_loader.py
==================================
Custom Django template loader that transparently serves language-specific
template variants.

When the current UI language is 'ja', a request for:
    app_core/dashboard.html
will first look for:
    app_core/ja/dashboard.html
and fall back to the English original if the ja-variant is not found.

This means views need no changes — all language switching is transparent.
"""
from django.template.loaders.app_directories import Loader as AppDirsLoader

from knowledge_manager.lang_middleware import get_current_lang


class LangLoader(AppDirsLoader):
    """
    App-directories loader with automatic lang-prefix lookup.

    For template_name = '{app}/{name}.html' and lang = 'ja':
      1. Tries   {app}/ja/{name}.html   (lang-specific variant)
      2. Falls back to {app}/{name}.html  (original English)
    """

    def get_template_sources(self, template_name):
        lang = get_current_lang()

        if lang != 'en' and f'/{lang}/' not in template_name:
            # Build the language-specific path:
            #   'app_core/dashboard.html' → 'app_core/ja/dashboard.html'
            parts = template_name.rsplit('/', 1)
            if len(parts) == 2:
                lang_template = f'{parts[0]}/{lang}/{parts[1]}'
            else:
                lang_template = f'{lang}/{template_name}'

            # Yield lang-specific sources first (highest priority)
            yield from super().get_template_sources(lang_template)

        # Always yield the original as fallback
        yield from super().get_template_sources(template_name)
