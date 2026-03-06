# Django-RAG — Knowledge Hub + Coding IDE

A production-ready Django 5.x application combining:

- **Knowledge Hub** (`app_core`) — RAG over uploaded documents (PDF, Word, Excel, TXT) using FAISS + Ollama
- **Coding IDE** (`coding_ide`) — In-browser coding assistant powered by Qwen 2.5 Coder + RAG over code files, Monaco editor, and Git manager

---

## Features

### Knowledge Hub (`app_core`)
- Upload and index documents (PDF, DOCX, XLSX, TXT)
- Semantic search via FAISS (CPU)
- LLM answers via Ollama (`llama3.2:3b` or similar)
- Query history and cache management

### Coding IDE (`coding_ide`)
- **Code Assistant** — Ask questions about code using RAG over uploaded source files
- **In-browser Monaco Editor** — Write code directly in the browser (VS Code experience)
  - Syntax highlighting for 20+ languages
  - Save snippets, load them back, send to AI assistant
  - Ctrl+S to save
- **Git Manager** — Manage local git repos from the UI
  - Init, Status, Add, Commit, Branch, Checkout, Push, Pull
  - Add any local path as a repository
- **Knowledge Base** — Upload code files (`.py`, `.js`, `.ts`, `.go`, `.rs`, etc.) for RAG indexing
- **Query History** — Browse past code queries

### Japanese UI (EN↔JA)
- Full Japanese translations of all 24 templates (14 × Knowledge Hub, 10 × Coding IDE)
- Custom template-based language switcher — no Django i18n required
- Toggle between English and Japanese via the **EN / JA** button (bottom-right, or IDE sidebar)
- Language preference stored per-session; survives page navigation
- Japanese-friendly font stack (`Hiragino Sans`, `Meiryo`, `Yu Gothic`)

### Shared Infrastructure
- **Single embedding model** (`BAAI/bge-large-en-v1.5`) — downloaded once, shared by both apps
- **CPU embeddings** — always runs on CPU (no CUDA kernel issues)
- **GPU for Ollama only** — Ollama uses its own CUDA runtime
- **FAISS CPU** — `faiss-cpu` (faiss-gpu-cu12 has no Python 3.12+ wheels)
- Download progress visible in System Status

---

## Architecture

```
Django-RAG/
├── knowledge_manager/           # Django project settings + root URLs
│   ├── settings.py              # TEMPLATES uses LangLoader; APP_DIRS=False
│   ├── urls.py                  # Includes /lang/<lang>/ switcher
│   ├── lang_middleware.py       # Thread-local per-request UI language
│   └── lang_loader.py           # AppDirs subclass → serves ja/ templates
├── app_core/                    # Document RAG app
│   ├── cache_manager.py         # Shared singleton embedding model
│   ├── faiss_manager.py         # CPU-only FAISS index
│   ├── rag_pipeline.py          # Document RAG pipeline
│   ├── management/commands/cache_models.py
│   └── templates/app_core/
│       ├── base.html / dashboard.html / chat.html / …  (English)
│       └── ja/                  # Japanese mirrors (14 files)
│           ├── base.html / dashboard.html / chat.html / …
├── coding_ide/                  # Coding IDE app
│   ├── cache_manager.py         # Re-exports app_core singleton
│   ├── faiss_code_manager.py    # CPU-only code FAISS index
│   ├── rag_pipeline.py          # Code RAG pipeline
│   ├── ollama_coder_client.py   # Qwen 2.5 Coder client
│   └── templates/coding_ide/
│       ├── base_ide.html / dashboard.html / …          (English)
│       └── ja/                  # Japanese mirrors (10 files)
│           ├── base_ide.html / dashboard.html / …
└── requirements.txt
```

### Language Switching — How It Works

1. **`LangMiddleware`** reads `request.session['ui_lang']` on every request and stores it in `threading.local()`.
2. **`LangLoader`** (subclass of `AppDirectoriesLoader`) intercepts every template lookup; when `lang='ja'`, it first tries `<app>/ja/<template>.html` before falling back to the English original.
3. **`/lang/<lang>/`** — a lightweight view that sets `request.session['ui_lang']` and redirects back to the referring page.
4. No Django i18n / `gettext` required; no `.po` files.

---

## Quick Start

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions.

```bash
# 1. Clone and install
git clone <repo-url>
cd Django-RAG
pip install -r requirements.txt

# 2. Install PyTorch with CUDA (for GPU reporting — embeddings still use CPU)
pip install torch --index-url https://download.pytorch.org/whl/cu124

# 3. Configure environment
cp change.env.txt .env
# Edit .env with your settings

# 4. Database setup
python manage.py migrate

# 5. Download embedding model
python manage.py cache_models

# 6. Create admin user
python manage.py createsuperuser

# 7. Pull Ollama models
ollama pull llama3.2:3b
ollama pull qwen2.5-coder:14b-instruct-q4_K_M

# 8. Run
python manage.py runserver
```

---

## Hardware Profile (RTX 5050 · 32 GB RAM · Ryzen 7)

| Component | Value | Notes |
|-----------|-------|-------|
| GPU | RTX 5050 · 8 GB VRAM | Used exclusively by Ollama for LLM inference |
| RAM | 32 GB | Allows large caches, batch size 64, 100 MB uploads |
| CPU | Ryzen 7 | Multi-core embedding batching |
| Coding LLM | `qwen2.5-coder:14b-instruct-q4_K_M` | ~8.5 GB VRAM · 4096 token output · 8192 ctx |
| Document LLM | `llama3.2:3b` | Lightweight, leaves VRAM for coder |
| Embedding model | `BAAI/bge-large-en-v1.5` | 1024 dims · ~1.3 GB · best retrieval quality |
| FAISS | CPU-only | `faiss-gpu-cu12` has no Python 3.12+ wheels |

- **Embeddings** always run on CPU (`EMBEDDING_DEVICE = 'cpu'`) — no CUDA errors
- Install CUDA-enabled PyTorch from `https://download.pytorch.org/whl/cu124` for accurate GPU detection in System Status
- **Changing the embedding model** invalidates existing FAISS indexes — re-upload your files after switching

---

## URL Routes

| Path | App | Description |
|------|-----|-------------|
| `/` | app_core | Document dashboard |
| `/documents/` | app_core | Document list |
| `/chat/` | app_core | Document Q&A |
| `/upload/` | app_core | Upload document |
| `/status/` | app_core | System status |
| `/history/` | app_core | Query history |
| `/profile/` | app_core | User profile |
| `/users/` | app_core | User management (admin) |
| `/lang/en/` | root | Switch UI to English |
| `/lang/ja/` | root | Switch UI to Japanese |
| `/coding-ide/` | coding_ide | Coding IDE dashboard |
| `/coding-ide/chat/` | coding_ide | Code assistant |
| `/coding-ide/editor/` | coding_ide | Monaco code editor |
| `/coding-ide/git/` | coding_ide | Git manager |
| `/coding-ide/knowledge-base/` | coding_ide | Code file knowledge base |
| `/coding-ide/status/` | coding_ide | IDE system status |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | required | Django secret key |
| `DEBUG` | `False` | Debug mode |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Allowed hostnames |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API host |
| `OLLAMA_MODEL` | `llama3.2:3b` | Document LLM model |
| `CODING_OLLAMA_HOST` | `http://localhost:11434` | Ollama host for coding IDE |
| `CODING_OLLAMA_MODEL` | `qwen2.5-coder:14b-instruct-q4_K_M` | Coding LLM model |
| `EMBEDDING_MODEL` | `BAAI/bge-large-en-v1.5` | Shared embedding model (1024 dims) |
| `EMBEDDING_DEVICE` | `cpu` | Device for embeddings (always CPU) |
| `EMBEDDING_BATCH_SIZE` | `64` | Embedding batch size (32 GB RAM) |
| `MAX_UPLOAD_SIZE_MB` | `100` | Max file upload size in MB |
| `CHUNK_SIZE` | `512` | Text chunk size (tokens) |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `TOP_K_RESULTS` | `5` | Number of RAG results to retrieve |

---

## Windows — HuggingFace Cache Note

On Windows **without Developer Mode**, the OS cannot create symlinks. HuggingFace Hub falls back to copying model files to `blobs/`, but the snapshot directory may contain broken symlinks that cause `Path.exists()` to return `False`, showing "Not Cached" even after a successful download.

The cache detection in this project uses a three-stage check:
1. Standard `Path.exists()` on snapshot files
2. `os.path.realpath()` to resolve broken symlinks
3. Blob directory size check (>100 MB = real model present)

To avoid the issue entirely, enable **Windows Developer Mode** before running `cache_models`.
