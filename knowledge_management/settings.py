"""
Django settings for knowledge_manager project.
Optimized for offline, low-resource operation.
"""
import os
from pathlib import Path
from decouple import config, Csv

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Security Settings
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app_core',
    'django_apscheduler',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'knowledge_manager.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'knowledge_manager.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# ===== RAG & AI Configuration =====

# Ollama Configuration
OLLAMA_HOST = config('OLLAMA_HOST', default='http://localhost:11434')
OLLAMA_MODEL = config('OLLAMA_MODEL', default='llama3.2:3b')
OLLAMA_TIMEOUT = config('OLLAMA_TIMEOUT', default=120, cast=int)

# Embedding Configuration
EMBEDDING_MODEL = config('EMBEDDING_MODEL', default='sentence-transformers/all-MiniLM-L6-v2')
MODELS_CACHE_DIR = BASE_DIR / config('MODELS_CACHE_DIR', default='models_cache')
EMBEDDING_BATCH_SIZE = config('EMBEDDING_BATCH_SIZE', default=16, cast=int)
EMBEDDING_DEVICE = config('EMBEDDING_DEVICE', default='cpu')

# FAISS Configuration
FAISS_INDEX_PATH = BASE_DIR / config('FAISS_INDEX_PATH', default='faiss_index')
FAISS_TOP_K = config('FAISS_TOP_K', default=5, cast=int)
CHUNK_SIZE = config('CHUNK_SIZE', default=500, cast=int)
CHUNK_OVERLAP = config('CHUNK_OVERLAP', default=50, cast=int)

# Memory Optimization
MAX_CONCURRENT_EMBEDDINGS = config('MAX_CONCURRENT_EMBEDDINGS', default=1, cast=int)
ENABLE_QUERY_CACHE = config('ENABLE_QUERY_CACHE', default=True, cast=bool)
QUERY_CACHE_SIZE = config('QUERY_CACHE_SIZE', default=50, cast=int)

# Upload Settings
MAX_UPLOAD_SIZE = config('MAX_UPLOAD_SIZE', default=50, cast=int) * 1024 * 1024  # Convert MB to bytes
ALLOWED_EXTENSIONS = config('ALLOWED_EXTENSIONS', default='.pdf,.docx,.txt,.xlsx', cast=Csv())

# Create necessary directories
os.makedirs(MODELS_CACHE_DIR, exist_ok=True)
os.makedirs(FAISS_INDEX_PATH, exist_ok=True)
os.makedirs(MEDIA_ROOT, exist_ok=True)

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'knowledge_manager.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'app_core': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
