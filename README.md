# 📚 Knowledge Management System with RAG

A fully local, offline-capable Django application implementing Retrieval-Augmented Generation (RAG) for internal company document management and querying using Ollama (Llama 3.2 1B).

## 🎯 Features

- **100% Offline Operation** - Works without internet after initial setup
- **Multi-format Document Support** - PDF, DOCX, TXT, XLSX
- **RAG-Powered Q&A** - Ask questions, get answers from your documents
- **Access Control** - Multi-tier document authorization (Public, Department, Manager, Private)
- **Low Resource Requirements** - Optimized for ≤8GB RAM, CPU-only
- **Local LLM** - Uses Ollama with Llama 3.2 1B model
- **Cached Embeddings** - Download embedding model once, use offline forever
- **FAISS Vector Search** - Fast similarity search for relevant chunks

## 📋 Prerequisites

### System Requirements
- **RAM:** 8 GB minimum
- **CPU:** Any modern CPU (no GPU required)
- **Storage:** ~5 GB for models and data
- **OS:** Linux, macOS, or Windows

### Software Requirements
- Python 3.11+
- Ollama (for local LLM inference)

## 🚀 Installation

### Step 1: Install Ollama

**Linux/macOS:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download from [https://ollama.ai/download](https://ollama.ai/download)

### Step 2: Pull Llama 3.2 3B Model

```bash
ollama pull llama3.2:3b
```

Verify the model is available:
```bash
ollama list
```

### Step 3: Clone and Setup Project

```bash
# Clone the repository
git clone <your-repo-url>
cd knowledge_manager

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings (optional - defaults work)
nano .env
```

Key settings:
- `SECRET_KEY`: Change for production
- `OLLAMA_HOST`: Default is `http://localhost:11434`
- `EMBEDDING_MODEL`: Default is `sentence-transformers/all-MiniLM-L6-v2`

### Step 5: Download Embedding Model (One-time, requires internet)

```bash
python manage.py shell
```

In the Python shell:
```python
from app_core.cache_manager import embedding_cache
embedding_cache.get_model()  # Downloads and caches the model
exit()
```

This downloads the embedding model to `./models_cache/`. After this, the system works fully offline.

### Step 6: Initialize Database

```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# If you want to try it with demo users use this command:
python manage.py setup_system --create-demo-users

# And use the demo users created by setup:

# Admin: admin / admin123
# Manager: manager / manager123
# Employee: employee / employee123
```

### Step 7: Run the Application

```bash
# Start Ollama (if not running)
ollama serve

# In another terminal, start Django
python manage.py runserver
```

Visit: `http://localhost:8000`

## 📁 Project Structure

```
knowledge_manager/
├── manage.py
├── requirements.txt
├── .env
├── README.md
│
├── knowledge_manager/           # Project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── app_core/                    # Main application
│   ├── models.py                # Document, User, Chunk models
│   ├── views.py                 # Django views
│   ├── forms.py                 # Django forms
│   ├── urls.py                  # URL routing
│   │
│   ├── cache_manager.py         # Embedding model caching
│   ├── document_processor.py    # Text extraction & chunking
│   ├── faiss_manager.py         # FAISS vector store
│   ├── ollama_client.py         # Ollama API client
│   ├── rag_pipeline.py          # Complete RAG orchestration
│   │
│   ├── templates/               # HTML templates
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── upload.html
│   │   ├── chat.html
│   │   └── documents.html
│   │
│   └── static/                  # CSS, JS
│       ├── css/
│       └── js/
│
├── media/                       # Uploaded documents
├── models_cache/                # Cached embedding model
├── faiss_index/                 # Vector store
└── db.sqlite3                   # Database
```

## 🔧 Usage

### 1. User Management

**Create Users:**
- Admin users can create new users via Django admin: `http://localhost:8000/admin`
- Or programmatically:

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
from app_core.models import UserProfile, UserRole

# Create user
user = User.objects.create_user('employee1', 'email@example.com', 'password123')

# Create profile with role
profile = UserProfile.objects.create(
    user=user,
    role=UserRole.EMPLOYEE,
    department='Engineering'
)
```

**User Roles:**
- **Admin**: Full access, manage users and documents
- **Manager**: Upload documents, access department documents
- **Employee**: Read-only access to authorized documents

### 2. Upload Documents

1. Login as Manager or Admin
2. Navigate to "Upload Document"
3. Select file (PDF, DOCX, TXT, XLSX)
4. Set title and access level
5. For department-level docs, specify department
6. Click "Upload"

The system will:
- Extract text from the document
- Split into chunks
- Generate embeddings (cached model, CPU-only)
- Store in FAISS index
- Ready for querying!

### 3. Query Documents

1. Navigate to "Chat" or "Query"
2. Type your question
3. Click "Ask"

The system will:
- Embed your query
- Search FAISS for relevant chunks (respecting access control)
- Send context + query to Ollama
- Display answer with source documents

### 4. System Dashboard

Access at `/dashboard/` to view:
- Total documents and processing status
- FAISS index statistics
- Embedding model cache status
- Ollama connection status
- Recent queries

## 🔒 Access Control

Documents have four access levels:

1. **Public**: All authenticated users
2. **Department**: Users in the same department
3. **Manager**: Only managers and admins
4. **Private**: Only admins

Access control is enforced in:
- Document listing
- FAISS retrieval (filters results)
- Direct document access

## ⚙️ Configuration

### Memory Optimization

In `.env`:
```bash
# Reduce batch size for lower RAM usage
EMBEDDING_BATCH_SIZE=8

# Smaller chunks reduce memory
CHUNK_SIZE=400
CHUNK_OVERLAP=40

# Limit concurrent operations
MAX_CONCURRENT_EMBEDDINGS=1
```

### Query Performance

```bash
# Number of chunks to retrieve
FAISS_TOP_K=5

# Enable caching for repeated queries
ENABLE_QUERY_CACHE=True
QUERY_CACHE_SIZE=50
```

### Ollama Settings

```bash
# Timeout for LLM inference (seconds)
OLLAMA_TIMEOUT=3600

# Change model (must be pulled first)
OLLAMA_MODEL=llama3.2:1b
```

## 🛠️ Troubleshooting

### Issue: Ollama connection failed

**Solution:**
```bash
# Start Ollama server
ollama serve

# Check if model is available
ollama list

# Test generation
ollama run llama3.2:1b "Hello"
```

### Issue: Out of memory

**Solution:**
1. Reduce `EMBEDDING_BATCH_SIZE` to 4 or 8
2. Reduce `CHUNK_SIZE` to 300-400
3. Set `MAX_CONCURRENT_EMBEDDINGS=1`
4. Process documents one at a time

### Issue: Embedding model download fails

**Solution:**
1. Check internet connection
2. Manually download model:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', cache_folder='./models_cache')
```

### Issue: Slow query responses

**Solution:**
1. Ensure Ollama is running locally (not in Docker)
2. Reduce `FAISS_TOP_K` to 3
3. Use smaller model if 3B is too slow
4. Enable query caching

## 📊 Performance

### Typical Performance (8GB RAM, i5 CPU):
- **Document Processing**: 5-15 seconds per document
- **Embedding Generation**: ~50 chunks/second
- **FAISS Retrieval**: <100ms for 10,000 chunks
- **LLM Inference**: 2-5 seconds for 500 tokens

### Memory Usage:
- **Base Django**: ~100 MB
- **Embedding Model**: ~100 MB
- **FAISS Index**: ~10 MB per 10,000 chunks
- **Ollama**: ~2-3 GB for Llama 3.2 3B

## 🔄 Maintenance

### Reindex All Documents

```bash
python manage.py shell
```

```python
from app_core.models import Document
from app_core.rag_pipeline import rag_pipeline

for doc in Document.objects.all():
    print(f"Reindexing {doc.title}...")
    rag_pipeline.reindex_document(doc)
```

### Clear Query Cache

```bash
python manage.py shell
```

```python
from app_core.rag_pipeline import rag_pipeline
rag_pipeline.clear_cache()
```

### Backup

```bash
# Backup database
cp db.sqlite3 db.sqlite3.backup

# Backup FAISS index
cp -r faiss_index faiss_index.backup

# Backup uploaded documents
cp -r media media.backup
```

## 🚦 Production Deployment

### Security

1. Change `SECRET_KEY` in `.env`
2. Set `DEBUG=False`
3. Configure `ALLOWED_HOSTS`
4. Use PostgreSQL instead of SQLite
5. Serve static files with nginx/Apache
6. Use HTTPS
7. Implement rate limiting

### Database Migration to PostgreSQL

In `.env`:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/knowledge_db
```

Install psycopg2:
```bash
pip install psycopg2-binary
```

## 📝 License

GNU Affero General Public License v3.0

## 🤝 Contributing

Contributions welcome! Please follow these guidelines:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📧 Support

For issues and questions:
- GitHub Issues: Send me issues
- Documentation: Look up into repos files, there are a lot!

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai/) - Local LLM inference
- [Sentence Transformers](https://www.sbert.net/) - Embedding models
- [FAISS](https://github.com/facebookresearch/faiss) - Vector similarity search

- [Django](https://www.djangoproject.com/) - Web framework


