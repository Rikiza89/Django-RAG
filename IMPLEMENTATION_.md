# Implementation Summary — Django-RAG

## What This Is

A **production-ready Django 5.x application** for offline Knowledge Management with RAG (Retrieval-Augmented Generation), consisting of two integrated apps:

- **Knowledge Hub** (`app_core`) — Document Q&A over PDF, DOCX, XLSX, TXT files
- **Coding IDE** (`coding_ide`) — In-browser code assistant with Monaco editor and Git manager

---

## Architecture

### Core Components

#### Language Switching Infrastructure
- **`knowledge_manager/lang_middleware.py`** — `LangMiddleware` stores `request.session['ui_lang']`
  in `threading.local()` on every request, making the current language available thread-safely
  to the template loader without modifying any view.
- **`knowledge_manager/lang_loader.py`** — `LangLoader` subclasses Django's `AppDirectoriesLoader`.
  When `lang='ja'`, it prepends a lookup for `<app>/ja/<template>.html` before falling back to the
  English original. Infinite-loop prevention: if `'/ja/'` is already in the template name, no
  redirect is attempted.
- **`knowledge_manager/urls.py`** — Custom `set_lang` view at `/lang/<lang>/` sets the session
  preference and redirects back to the referring page. Replaces the broken Django i18n
  `/i18n/set_language/` URL.
- **`knowledge_manager/settings.py`** — `APP_DIRS: False` + explicit `loaders: [LangLoader]`
  (required to use a custom loader); `LangMiddleware` added to `MIDDLEWARE`.

#### RAG Pipeline (both apps)
- **Embedding model** — `BAAI/bge-large-en-v1.5` (1024 dims, ~1.3 GB). Downloaded once via
  `python manage.py cache_models`, shared between both apps via `app_core/cache_manager.py`
  singleton. Always runs on **CPU**.
- **FAISS** — CPU-only flat index (`faiss-cpu`). `app_core/faiss_manager.py` for documents;
  `coding_ide/faiss_code_manager.py` for code files. Separate indexes per app.
- **Ollama** — Document LLM: `llama3.2:3b`. Coding LLM: `qwen2.5-coder:14b-instruct-q4_K_M`
  (8192 ctx, 4096 max output). Both run on GPU via Ollama's own CUDA runtime.

#### Cache Detection (Windows fix)
On Windows without Developer Mode, HuggingFace Hub cannot create symlinks. It falls back to
copying files to `blobs/`, leaving broken symlinks in the snapshot directory. `_is_cached()` in
`cache_manager.py` uses a three-stage detection:
1. Standard `Path.exists()` on snapshot files
2. `os.path.realpath()` to resolve symlinks before checking existence
3. Blob directory cumulative size check (>100 MB = real model is present)

---

## File Structure

```
knowledge_manager/
├── settings.py            # APP_DIRS=False; LangLoader; LangMiddleware
├── urls.py                # /lang/<lang>/ + app includes
├── lang_middleware.py     # Thread-local UI language
└── lang_loader.py         # Template redirect to ja/ subdirs

app_core/
├── models.py              # Document, UserProfile, QueryHistory
├── views.py               # CRUD + RAG query views
├── cache_manager.py       # Embedding model singleton (CPU)
├── document_processor.py  # PDF/DOCX/XLSX/TXT → text chunks
├── faiss_manager.py       # FAISS flat index for documents
├── ollama_client.py       # Document LLM (llama3.2:3b)
├── rag_pipeline.py        # Retrieve → prompt → generate
├── management/commands/
│   └── cache_models.py    # Download + verify embedding model
└── templates/app_core/
    ├── base.html / login.html / dashboard.html / …  (14 English templates)
    └── ja/                                           (14 Japanese mirrors)

coding_ide/
├── models.py              # CodeFile, CodeQuery, GitRepository, CodeSnippet
├── views.py               # IDE views + code RAG
├── cache_manager.py       # Re-exports app_core singleton
├── faiss_code_manager.py  # FAISS flat index for code files
├── ollama_coder_client.py # Qwen 2.5 Coder client
├── rag_pipeline.py        # Code retrieve → prompt → generate
├── context_processors.py  # GPU info for templates
└── templates/coding_ide/
    ├── base_ide.html / dashboard.html / …           (10 English templates)
    └── ja/                                           (10 Japanese mirrors)
```

---

## Key Features

### Document Management (app_core)
- Multi-format upload (PDF, DOCX, TXT, XLSX) up to 100 MB
- Automatic text extraction, chunking (512 tokens, 50 overlap), deduplication by file hash
- Access control: Public / Department / Manager / Private
- FAISS indexing per document; re-index on demand

### Code Assistant (coding_ide)
- Upload source files (`.py`, `.js`, `.ts`, `.go`, `.rs`, `.java`, `.cpp`, …)
- RAG over code using same embedding model
- Qwen 2.5 Coder 14B — tuned for 8 GB VRAM, 8192 context
- Monaco editor with 20+ language syntax highlighting, snippet persistence
- Git Manager: Init, Status, Add, Commit, Branch, Checkout, Pull, Push

### Japanese UI
- 24 Japanese template files (14 app_core + 10 coding_ide), fully translated
- `LangLoader` transparently serves `ja/` templates — zero changes to views
- EN↔JA toggle in every base template; preference stored in session
- Japanese-friendly font stack: `Hiragino Sans`, `Meiryo`, `Yu Gothic`, `Noto Sans JP`
- Date format: `Y年m月d日`; byte names: バイト / KB / MB / GB; all JS strings translated

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Framework | Django 5.x |
| Database | SQLite (PostgreSQL-ready) |
| Embedding model | `BAAI/bge-large-en-v1.5` (CPU, 1024 dims) |
| Vector store | FAISS CPU (`faiss-cpu`) |
| Document LLM | Ollama → `llama3.2:3b` |
| Coding LLM | Ollama → `qwen2.5-coder:14b-instruct-q4_K_M` |
| Code editor | Monaco Editor (VS Code engine) |
| Frontend | Bootstrap 5 + Vanilla JS |
| Document parsing | PyMuPDF, python-docx, openpyxl |
| Language switching | Custom `LangLoader` + `LangMiddleware` |

---

## Performance (RTX 5050 · 8 GB VRAM · 32 GB RAM · Ryzen 7)

| Operation | Typical time |
|-----------|-------------|
| Document upload + embed (10 pages) | 5–15 s |
| Embedding batch (64 chunks, CPU) | ~3 s |
| FAISS retrieval (10 K chunks) | <100 ms |
| Code assistant response (14B, GPU) | 4–10 s |
| Document Q&A response (3B, GPU) | 2–5 s |

### Memory usage
| Component | RAM |
|-----------|-----|
| Django base | ~100 MB |
| Embedding model (loaded) | ~1.3 GB |
| FAISS index (10 K chunks) | ~40 MB |
| Ollama llama3.2:3b | ~2 GB VRAM |
| Ollama qwen2.5-coder:14b Q4_K_M | ~8.5 GB VRAM |

---

## Environment Variables (GPU-optimized defaults)

```env
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=64
MAX_UPLOAD_SIZE_MB=100
CHUNK_SIZE=512
CHUNK_OVERLAP=50
TOP_K_RESULTS=5
OLLAMA_MODEL=llama3.2:3b
CODING_OLLAMA_MODEL=qwen2.5-coder:14b-instruct-q4_K_M
```

---

## Security

- CSRF protection on all POST forms
- Django ORM (no raw SQL → no injection)
- File type + size validation on upload
- Role-based access (Admin / Manager / Employee)
- Document-level access control (Public / Department / Manager / Private)
- `SECRET_KEY` and `DEBUG` controlled via `.env`

---

## Known Limitations

1. **Concurrent users** — SQLite works well up to ~10 simultaneous users; switch to PostgreSQL for production load
2. **FAISS scale** — Flat index is accurate but O(n) at search time; suitable for <200 K chunks
3. **VRAM sharing** — Running both LLMs simultaneously requires >10 GB VRAM; Ollama auto-unloads idle models
4. **Symlinks on Windows** — HuggingFace Hub needs Developer Mode for symlink support; three-stage fallback detection is in place
