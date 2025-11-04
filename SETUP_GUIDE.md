# 🚀 Quick Setup Guide

This guide will help you get the Knowledge Management System up and running in minutes.

## ⚡ Quick Start (5 Minutes)

### 1. Install Ollama
```bash
# Linux/macOS
curl -fsSL https://ollama.ai/install.sh | sh

# Windows: Download from https://ollama.ai/download
```

### 2. Pull the LLM Model
```bash
ollama pull llama3.2:3b
```

### 3. Setup Python Environment
```bash
# Clone/navigate to project
cd knowledge_manager

# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
# Copy example config
cp .env.example .env

# Optional: Edit .env if needed
nano .env
```

### 5. Download Embedding Model (One-time, needs internet)
```bash
python manage.py shell
```

Then in the Python shell:
```python
from app_core.cache_manager import embedding_cache
print("Downloading embedding model...")
model = embedding_cache.get_model()
print("✓ Model cached successfully!")
exit()
```

### 6. Initialize Database
```bash
# Create database tables
python manage.py makemigrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser
# Enter: username, email (optional), password
```

### 7. Start the System
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start Django (in project directory)
python manage.py runserver
```

### 8. Access the Application
Open your browser: **http://localhost:8000**

Login with your superuser credentials!

---

## 📝 Creating Test Users

### Via Django Shell
```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
from app_core.models import UserProfile, UserRole

# Create a manager
manager = User.objects.create_user('manager1', 'manager@example.com', 'password123')
UserProfile.objects.create(user=manager, role=UserRole.MANAGER, department='Engineering')

# Create an employee
employee = User.objects.create_user('employee1', 'employee@example.com', 'password123')
UserProfile.objects.create(user=employee, role=UserRole.EMPLOYEE, department='Engineering')

print("✓ Test users created!")
exit()
```

### Via Admin Interface
1. Go to http://localhost:8000/admin
2. Login with superuser
3. Click "Users" → "Add User"
4. Fill in username and password
5. Save
6. Click "User profiles" → "Add User Profile"
7. Select the user, set role and department
8. Save

---

## 📚 First Document Upload

1. Login as admin or manager
2. Click "Upload Document" in sidebar
3. Select a file (PDF, DOCX, TXT, or XLSX)
4. Set title and access level
5. Click "Upload and Process"
6. Wait for processing (usually 5-15 seconds)
7. Document is ready for querying!

---

## 💬 First Query

1. Click "Chat / Query" in sidebar
2. Type a question about your document content
3. Click "Ask Question"
4. Get AI-powered answer with sources!

---

## 🔧 Troubleshooting

### Issue: "Ollama connection failed"
**Solution:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

### Issue: "Model not available"
**Solution:**
```bash
# List available models
ollama list

# Pull the required model
ollama pull llama3.2:3b
```

### Issue: "Embedding model not cached"
**Solution:**
```bash
python manage.py shell
```
```python
from app_core.cache_manager import embedding_cache
embedding_cache.get_model()  # Downloads and caches
exit()
```

### Issue: Out of Memory
**Solution:** Edit `.env`:
```bash
EMBEDDING_BATCH_SIZE=4
CHUNK_SIZE=300
MAX_CONCURRENT_EMBEDDINGS=1
```

### Issue: Slow Processing
**Tips:**
- Reduce `CHUNK_SIZE` to 300-400
- Process documents one at a time
- Use smaller model if available
- Ensure Ollama runs natively (not in Docker)

---

## 🎯 System Architecture

```
User Request
    ↓
Django Views
    ↓
RAG Pipeline
    ↓
┌─────────────────┬──────────────────┬─────────────────┐
│ Document        │ Embedding Cache  │ FAISS Index     │
│ Processor       │ (Offline Model)  │ (Vector Store)  │
└─────────────────┴──────────────────┴─────────────────┘
    ↓
Ollama (Local LLM)
    ↓
Response to User
```

---

## 📊 Performance Tips

### For 8GB RAM Systems:
```bash
# .env settings
EMBEDDING_BATCH_SIZE=8
CHUNK_SIZE=400
CHUNK_OVERLAP=40
MAX_CONCURRENT_EMBEDDINGS=1
FAISS_TOP_K=5
```

### For Better Performance:
```bash
# .env settings
EMBEDDING_BATCH_SIZE=16
CHUNK_SIZE=500
CHUNK_OVERLAP=50
FAISS_TOP_K=7
ENABLE_QUERY_CACHE=True
QUERY_CACHE_SIZE=100
```

---

## 🔐 Access Control Examples

### Public Document (All users can access)
- Access Level: **Public**
- Department: *leave empty*

### Department Document (Only Engineering team)
- Access Level: **Department**
- Department: **Engineering**

### Manager Document (Managers and Admins only)
- Access Level: **Manager**
- Department: *leave empty or specify*

### Private Document (Admins only)
- Access Level: **Private**
- Department: *leave empty*

---

## 🔄 Going Fully Offline

After initial setup (which requires internet for model downloads):

1. ✅ Embedding model is cached in `./models_cache/`
2. ✅ Ollama model is downloaded
3. ✅ All Python dependencies are installed

**Now you can work 100% offline!**

Disconnect from internet and everything still works:
- Upload documents ✓
- Query documents ✓
- Process new files ✓
- Generate AI responses ✓

---

## 📦 Backup & Restore

### Backup Everything:
```bash
# Create backup directory
mkdir backup_$(date +%Y%m%d)
cd backup_$(date +%Y%m%d)

# Backup database
cp ../db.sqlite3 ./

# Backup uploaded documents
cp -r ../media ./

# Backup FAISS index
cp -r ../faiss_index ./

# Backup models (optional - can re-download)
cp -r ../models_cache ./
```

### Restore:
```bash
# Copy files back
cp backup_20241103/db.sqlite3 ./
cp -r backup_20241103/media ./
cp -r backup_20241103/faiss_index ./
```

---

## 🚀 Production Deployment

### Key Changes for Production:

1. **Security** - Update `.env`:
```bash
SECRET_KEY=<generate-strong-random-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

2. **Database** - Switch to PostgreSQL:
```bash
pip install psycopg2-binary
```

`.env`:
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/kms_db
```

3. **Static Files**:
```bash
python manage.py collectstatic
```

4. **Web Server** - Use Gunicorn + Nginx:
```bash
pip install gunicorn
gunicorn knowledge_manager.wsgi:application
```

5. **Systemd Service** (Linux):
```ini
[Unit]
Description=Knowledge Management System
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/knowledge_manager
ExecStart=/path/to/venv/bin/gunicorn knowledge_manager.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 📞 Need Help?

- Check `README.md` for detailed documentation
- Review system status at `/system/status/`
- Check logs in `knowledge_manager.log`
- Verify Ollama: `ollama list`
- Test embedding: Go to system status page

---

## ✨ What's Next?

1. **Upload Documents** - Add your company docs
2. **Create Users** - Set up team members with appropriate roles
3. **Start Querying** - Ask questions about your documents
4. **Monitor System** - Check system status regularly
5. **Backup Data** - Set up regular backups

Enjoy your fully offline, AI-powered knowledge management system! 🎉