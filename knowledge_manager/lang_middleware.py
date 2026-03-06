"""
knowledge_manager/lang_middleware.py
=====================================
Stores the current UI language in the session and exposes it via a
thread-local so the custom template loader can read it without touching
every view.

Supported language codes: 'en' (default), 'ja'
Switch URL: /lang/<code>/   (defined in urls.py)
"""
import threading

_local = threading.local()


def get_current_lang() -> str:
    """Return the UI language for the current thread (default 'en')."""
    return getattr(_local, 'lang', 'en')


class LangMiddleware:
    SUPPORTED = {'en', 'ja'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = request.session.get('ui_lang', 'en')
        if lang not in self.SUPPORTED:
            lang = 'en'

        _local.lang = lang
        request.ui_lang = lang          # available in templates as {{ request.ui_lang }}

        try:
            response = self.get_response(request)
        finally:
            _local.lang = 'en'          # reset after request to avoid thread-pool leaks

        return response
