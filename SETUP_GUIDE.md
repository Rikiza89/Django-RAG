# Setup Guide — Django-RAG

## Prerequisites

- Python 3.11 or 3.12
- pip
- [Ollama](https://ollama.ai) installed and running
- Git (for the Git Manager feature)

---

## 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

> **Note**: `faiss-gpu-cu12` has no Python 3.12+ wheels. Use `faiss-cpu` (already in requirements).

### PyTorch CUDA (optional but recommended for GPU reporting)

Install PyTorch with CUDA 12.4 support for accurate GPU detection:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

> Embeddings always run on CPU regardless. This only affects the GPU detection readout in System Status.

---

## 2. Environment Configuration

```bash
cp change.env.txt .env
```

Edit `.env`:

```env
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# Document LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

# Coding LLM (Qwen 2.5 Coder)
CODING_OLLAMA_HOST=http://localhost:11434
CODING_OLLAMA_MODEL=qwen2.5-coder:7b-instruct-q4_K_M

# Embedding model (shared by both apps, always CPU)
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
```

---

## 3. Database Setup

```bash
python manage.py migrate
```

---

## 4. Download Embedding Model

The embedding model must be downloaded before indexing works.

```bash
# Download and cache the model
python manage.py cache_models

# Check status without downloading
python manage.py cache_models --check

# Force re-download
python manage.py cache_models --force
```

The model (~420 MB) is cached at `models_cache/` and shared between both apps.
Download progress is visible in the System Status page during runtime.

---

## 5. Create Admin User

```bash
python manage.py createsuperuser
```

---

## 6. Pull Ollama Models

```bash
# For document Q&A
ollama pull llama3.2:3b

# For code assistant (choose based on VRAM)
ollama pull qwen2.5-coder:7b-instruct-q4_K_M   # ~4.5 GB VRAM (recommended)
ollama pull qwen2.5-coder:14b-instruct-q4_K_M  # ~8.5 GB VRAM (higher quality)
```

---

## 7. Run the Server

```bash
python manage.py runserver
```

Visit [http://localhost:8000](http://localhost:8000)

---

## VRAM Guidelines (RTX 5050 / 8 GB)

| Model | VRAM | Quality |
|-------|------|---------|
| `qwen2.5-coder:7b-instruct-q4_K_M` | ~4.5 GB | Good |
| `qwen2.5-coder:14b-instruct-q4_K_M` | ~8.5 GB | Better (tight fit) |
| `llama3.2:3b` | ~2 GB | Fast for documents |
| `llama3.2:8b` | ~5 GB | Better for documents |

---

## GPU Setup Details

| Component | Device | Notes |
|-----------|--------|-------|
| Embedding model | **CPU** | Always CPU — avoids CUDA kernel errors |
| FAISS index | **CPU** | `faiss-cpu` — no Python 3.12+ wheels for faiss-gpu |
| Ollama LLM | **GPU** | Uses its own CUDA runtime automatically |

---

## Using the Code Editor

1. Navigate to **Coding IDE → Code Editor**
2. Write code in the Monaco editor (VS Code experience)
3. Select language from the dropdown
4. **Ctrl+S** or click **Save** to persist the snippet
5. Click **Ask AI** to send the code to the code assistant with a review prompt
6. Previous snippets appear in the left panel — click to load

---

## Using the Git Manager

1. Navigate to **Coding IDE → Git Manager**
2. Click **Add Repository** and enter the absolute path to a local folder
3. Select a repository from the list to work with it
4. Available actions:
   - **Status** — view working tree status and recent commits
   - **Init** — initialize a new git repository
   - **Add** — stage files (leave blank to stage all)
   - **Commit** — commit with a message
   - **New Branch** — create a new branch
   - **Checkout** — switch branches (prefix `+` to create new)
   - **Pull** — pull from remote (format: `origin main`)
   - **Push** — push to remote (format: `origin main`)

---

## Troubleshooting

### "CUDA error: no kernel image" on file upload
- This has been fixed. Embeddings always run on CPU.
- Ensure `EMBEDDING_DEVICE = 'cpu'` in settings (it is hardcoded).

### "No CUDA device found" in System Status
- Install PyTorch with CUDA: `pip install torch --index-url https://download.pytorch.org/whl/cu124`
- Note: this only affects the reporting. Ollama still uses GPU for inference.

### Embedding model not downloading
- Run `python manage.py cache_models`
- Check internet access to Hugging Face
- Check disk space (~500 MB required)

### Ollama model not available
- Run `ollama pull <model-name>`
- Verify Ollama is running: `ollama serve`
- Check `CODING_OLLAMA_HOST` in `.env`

### git not found in Git Manager
- Install git: `sudo apt install git` (Ubuntu/Debian) or `brew install git` (macOS)
- Restart the Django server after installation
