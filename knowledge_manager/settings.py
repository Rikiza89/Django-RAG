"""
Django settings for knowledge_manager / Django-Coding-RAG project.
"""

import os
from pathlib import Path
from decouple import config, Csv

# ---------------------------------------------------------------------------
# GPU detection — used for reporting only.
# Embeddings ALWAYS run on CPU (avoids CUDA kernel errors with
# sentence-transformers).  Ollama uses the GPU for LLM inference
# independently through its own CUDA runtime.
# ---------------------------------------------------------------------------
def _detect_cuda():
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            print(f"[GPU] {name}  |  {vram:.1f} GB VRAM  |  CUDA available for Ollama")
            return True
        print("[GPU] No CUDA device detected — Ollama will use CPU")
        return False
    except ImportError:
        print("[GPU] torch not installed. GPU install: "
              "pip install torch --index-url https://download.pytorch.org/whl/cu124")
        return False

USE_GPU = _detect_cuda()   # True = GPU visible; embeddings still run on CPU

# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'app_core',
    'coding_ide',
    'django_apscheduler',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "knowledge_manager.urls"

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
                'coding_ide.context_processors.gpu_context',
            ],
        },
    },
]

WSGI_APPLICATION = "knowledge_manager.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = config('TIME_ZONE', default='UTC')
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
_static_dir = BASE_DIR / 'static'
STATICFILES_DIRS = [_static_dir] if _static_dir.exists() else []

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# ---------------------------------------------------------------------------
# Shared Embedding Model
# Both app_core and coding_ide use ONE model loaded once into memory.
# CPU only — keeps GPU VRAM free for Ollama LLM inference.
# Run:  python manage.py cache_models   to pre-download before first use.
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = config(
    'EMBEDDING_MODEL',
    # Top pick: excellent for English text + code, 768 dims, ~420 MB
    default='sentence-transformers/all-mpnet-base-v2'
    # Multilingual: 'intfloat/multilingual-e5-large'  (1024 dims, ~1.1 GB)
    # Lightweight:  'intfloat/multilingual-e5-small'  (384 dims,  ~120 MB)
)
EMBEDDING_DEVICE = 'cpu'           # Always CPU — do NOT change
EMBEDDING_BATCH_SIZE = config('EMBEDDING_BATCH_SIZE', default=16, cast=int)
MODELS_CACHE_DIR = BASE_DIR / config('MODELS_CACHE_DIR', default='models_cache')

# ---------------------------------------------------------------------------
# Knowledge Hub — Document RAG (app_core)
# ---------------------------------------------------------------------------
OLLAMA_HOST    = config('OLLAMA_HOST',    default='http://localhost:11434')
OLLAMA_MODEL   = config('OLLAMA_MODEL',   default='llama3.2:3b')
OLLAMA_TIMEOUT = config('OLLAMA_TIMEOUT', default=120, cast=int)

FAISS_INDEX_PATH = BASE_DIR / config('FAISS_INDEX_PATH', default='faiss_index')
FAISS_TOP_K      = config('FAISS_TOP_K',   default=3,   cast=int)
CHUNK_SIZE       = config('CHUNK_SIZE',    default=500,  cast=int)
CHUNK_OVERLAP    = config('CHUNK_OVERLAP', default=100,  cast=int)

ENABLE_QUERY_CACHE = config('ENABLE_QUERY_CACHE', default=True, cast=bool)
QUERY_CACHE_SIZE   = config('QUERY_CACHE_SIZE',   default=50,   cast=int)

MAX_UPLOAD_SIZE    = config('MAX_UPLOAD_SIZE', default=50, cast=int) * 1024 * 1024
ALLOWED_EXTENSIONS = config('ALLOWED_EXTENSIONS', default='.pdf,.docx,.txt,.xlsx', cast=Csv())

# ---------------------------------------------------------------------------
# Coding IDE — Code RAG
# ---------------------------------------------------------------------------
CODING_OLLAMA_HOST    = config('CODING_OLLAMA_HOST',    default='http://localhost:11434')
# Recommended models (pull via `ollama pull <model>`):
#   qwen2.5-coder:7b-instruct-q4_K_M   — best for 8 GB VRAM (recommended)
#   qwen2.5-coder:14b-instruct-q4_K_M  — better, needs ~10 GB VRAM
CODING_OLLAMA_MODEL   = config('CODING_OLLAMA_MODEL',   default='qwen2.5-coder:7b-instruct-q4_K_M')
CODING_OLLAMA_TIMEOUT = config('CODING_OLLAMA_TIMEOUT', default=240, cast=int)

# coding_ide reuses EMBEDDING_MODEL and MODELS_CACHE_DIR — no second download
CODE_FAISS_INDEX_PATH   = BASE_DIR / config('CODE_FAISS_INDEX_PATH',   default='code_faiss_index')
CODE_FAISS_TOP_K        = config('CODE_FAISS_TOP_K',        default=5,    cast=int)
CODE_CHUNK_SIZE         = config('CODE_CHUNK_SIZE',         default=600,  cast=int)
CODE_CHUNK_OVERLAP      = config('CODE_CHUNK_OVERLAP',      default=100,  cast=int)
CODE_ENABLE_QUERY_CACHE = config('CODE_ENABLE_QUERY_CACHE', default=True, cast=bool)
CODE_QUERY_CACHE_SIZE   = config('CODE_QUERY_CACHE_SIZE',   default=30,   cast=int)

CODE_ALLOWED_EXTENSIONS = config(
    'CODE_ALLOWED_EXTENSIONS',
    default='.py,.js,.ts,.jsx,.tsx,.java,.cpp,.c,.h,.hpp,.go,.rs,.php,.rb,.swift,.kt,.cs,.html,.css,.sql,.sh,.bash,.md,.json,.yaml,.yml,.toml,.txt,.vue,.svelte',
    cast=Csv()
)

# ---------------------------------------------------------------------------
# Ensure required directories exist
# ---------------------------------------------------------------------------
for _d in [MODELS_CACHE_DIR, FAISS_INDEX_PATH, CODE_FAISS_INDEX_PATH, MEDIA_ROOT]:
    os.makedirs(_d, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {module} {message}', 'style': '{'},
        'simple':  {'format': '{levelname} {message}', 'style': '{'},
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
            'formatter': 'simple',
        },
    },
    'loggers': {
        'app_core':   {'handlers': ['file', 'console'], 'level': 'INFO', 'propagate': False},
        'coding_ide': {'handlers': ['file', 'console'], 'level': 'INFO', 'propagate': False},
    },
}
