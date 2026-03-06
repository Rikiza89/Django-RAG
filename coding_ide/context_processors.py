from django.conf import settings


def gpu_context(request):
    return {
        'USE_GPU': getattr(settings, 'USE_GPU', False),
    }
