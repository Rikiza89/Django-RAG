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

### Shared Infrastructure
- **Single embedding model** (`sentence-transformers/all-mpnet-base-v2`) — downloaded once, shared by both apps
- **CPU embeddings** — always runs on CPU (no CUDA kernel issues)
- **GPU for Ollama only** — Ollama uses its own CUDA runtime
- **FAISS CPU** — `faiss-cpu` (faiss-gpu-cu12 has no Python 3.12+ wheels)
- Download progress visible in System Status

---

## Architecture

```
Django-RAG/
├── knowledge_manager/     # Django project settings + root URLs
├── app_core/              # Document RAG app
│   ├── cache_manager.py   # Shared singleton embedding model
│   ├── faiss_manager.py   # CPU-only FAISS index
│   ├── rag_pipeline.py    # Document RAG pipeline
│   └── management/commands/cache_models.py
├── coding_ide/            # Coding IDE app
│   ├── cache_manager.py   # Re-exports app_core singleton
│   ├── faiss_code_manager.py  # CPU-only code FAISS index
│   ├── rag_pipeline.py    # Code RAG pipeline
│   ├── ollama_coder_client.py # Qwen 2.5 Coder client
│   └── templates/
│       ├── code_editor.html   # Monaco Editor
│       └── git_manager.html   # Git UI
└── requirements.txt
```

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
ollama pull qwen2.5-coder:7b-instruct-q4_K_M

# 8. Run
python manage.py runserver
```

---

## GPU Notes (RTX 5050 / CUDA 12.8)

- **Ollama** automatically uses GPU for LLM inference (manages its own CUDA runtime)
- **Embeddings** always run on CPU (`EMBEDDING_DEVICE = 'cpu'`) — no CUDA errors
- **FAISS** uses CPU-only (`faiss-cpu`) — `faiss-gpu-cu12` has no Python 3.12+ wheels
- Install CUDA-enabled PyTorch from `https://download.pytorch.org/whl/cu124` for accurate GPU detection in System Status

---

## URL Routes

| Path | App | Description |
|------|-----|-------------|
| `/` | app_core | Document dashboard |
| `/documents/` | app_core | Document list |
| `/chat/` | app_core | Document Q&A |
| `/ide/` | coding_ide | Coding IDE dashboard |
| `/ide/chat/` | coding_ide | Code assistant |
| `/ide/editor/` | coding_ide | Monaco code editor |
| `/ide/git/` | coding_ide | Git manager |
| `/ide/knowledge-base/` | coding_ide | Code file knowledge base |
| `/ide/status/` | coding_ide | System status |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | required | Django secret key |
| `DEBUG` | `False` | Debug mode |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API host |
| `OLLAMA_MODEL` | `llama3.2:3b` | Document LLM model |
| `CODING_OLLAMA_MODEL` | `qwen2.5-coder:7b-instruct-q4_K_M` | Coding LLM model |
| `EMBEDDING_MODEL` | `sentence-transformers/all-mpnet-base-v2` | Shared embedding model |
