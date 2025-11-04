#!/bin/bash

# Knowledge Management System - Installation Script
# For Linux/macOS systems

set -e  # Exit on error

echo "========================================================"
echo "Knowledge Management System - Installation Script"
echo "========================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    echo "Please install Python 3.11 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
echo ""

# Check if Ollama is installed
echo "Checking Ollama installation..."
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}⚠ Ollama is not installed${NC}"
    echo "Would you like to install Ollama now? (y/n)"
    read -r install_ollama
    
    if [ "$install_ollama" = "y" ]; then
        echo "Installing Ollama..."
        curl -fsSL https://ollama.ai/install.sh | sh
        echo -e "${GREEN}✓ Ollama installed${NC}"
    else
        echo -e "${YELLOW}⚠ Skipping Ollama installation${NC}"
        echo "You can install it later with: curl -fsSL https://ollama.ai/install.sh | sh"
    fi
else
    echo -e "${GREEN}✓ Ollama is installed${NC}"
fi
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠ Virtual environment already exists${NC}"
    echo "Would you like to recreate it? (y/n)"
    read -r recreate_venv
    
    if [ "$recreate_venv" = "y" ]; then
        rm -rf venv
        python3 -m venv venv
        echo -e "${GREEN}✓ Virtual environment recreated${NC}"
    fi
else
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel
echo -e "${GREEN}✓ Pip upgraded${NC}"
echo ""

# Install dependencies
echo "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${RED}✗ requirements.txt not found${NC}"
    exit 1
fi
echo ""

# Create .env file if it doesn't exist
echo "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env from .env.example${NC}"
        echo -e "${YELLOW}⚠ Please review and update .env file with your settings${NC}"
    else
        echo -e "${RED}✗ .env.example not found${NC}"
    fi
else
    echo -e "${YELLOW}⚠ .env file already exists${NC}"
fi
echo ""

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p app_core/templates/app_core
mkdir -p app_core/static/{css,js,images}
mkdir -p app_core/management/commands
mkdir -p app_core/migrations
mkdir -p media/documents
mkdir -p models_cache
mkdir -p faiss_index
mkdir -p staticfiles
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Run migrations
echo "Setting up database..."
python manage.py makemigrations
python manage.py migrate
echo -e "${GREEN}✓ Database setup complete${NC}"
echo ""

# Ask to create superuser
echo "Would you like to create a superuser now? (y/n)"
read -r create_superuser

if [ "$create_superuser" = "y" ]; then
    python manage.py createsuperuser
fi
echo ""

# Ask to create demo users
echo "Would you like to create demo users? (admin, manager, employee) (y/n)"
read -r create_demo

if [ "$create_demo" = "y" ]; then
    python manage.py setup_system --create-demo-users
    echo ""
    echo -e "${GREEN}Demo users created:${NC}"
    echo "  - admin / admin123"
    echo "  - manager / manager123"
    echo "  - employee / employee123"
    echo ""
    echo -e "${YELLOW}⚠ Remember to change these passwords in production!${NC}"
fi
echo ""

# Check Ollama and pull model
if command -v ollama &> /dev/null; then
    echo "Checking Ollama status..."
    
    # Check if Ollama is running
    if ! pgrep -x "ollama" > /dev/null; then
        echo -e "${YELLOW}⚠ Ollama is not running${NC}"
        echo "Would you like to start Ollama in the background? (y/n)"
        read -r start_ollama
        
        if [ "$start_ollama" = "y" ]; then
            ollama serve &
            sleep 3
            echo -e "${GREEN}✓ Ollama started${NC}"
        fi
    else
        echo -e "${GREEN}✓ Ollama is running${NC}"
    fi
    
    # Check and pull model
    echo "Checking for llama3.2:3b model..."
    if ollama list | grep -q "llama3.2:3b"; then
        echo -e "${GREEN}✓ Model llama3.2:3b is available${NC}"
    else
        echo -e "${YELLOW}⚠ Model llama3.2:3b not found${NC}"
        echo "Would you like to pull it now? (This will download ~2GB) (y/n)"
        read -r pull_model
        
        if [ "$pull_model" = "y" ]; then
            echo "Pulling llama3.2:3b model..."
            ollama pull llama3.2:3b
            echo -e "${GREEN}✓ Model downloaded${NC}"
        else
            echo "You can pull it later with: ollama pull llama3.2:3b"
        fi
    fi
fi
echo ""

# Download embedding model
echo "Would you like to download the embedding model now? (Requires internet) (y/n)"
read -r download_embedding

if [ "$download_embedding" = "y" ]; then
    echo "Downloading embedding model..."
    python -c "
from app_core.cache_manager import embedding_cache
print('Downloading and caching embedding model...')
model = embedding_cache.get_model()
print('✓ Model cached successfully!')
"
    echo -e "${GREEN}✓ Embedding model downloaded and cached${NC}"
fi
echo ""

# Final summary
echo "========================================================"
echo "Installation Complete!"
echo "========================================================"
echo ""
echo -e "${GREEN}✓ All dependencies installed${NC}"
echo -e "${GREEN}✓ Database setup complete${NC}"
echo -e "${GREEN}✓ Directories created${NC}"
echo ""
echo "Next steps:"
echo "1. Review and update .env file if needed"
echo "2. Start Ollama (if not running): ollama serve"
echo "3. Start Django development server: python manage.py runserver"
echo "4. Open browser: http://localhost:8000"
echo ""
echo "Quick start command (in separate terminals):"
echo "  Terminal 1: ollama serve"
echo "  Terminal 2: source venv/bin/activate && python manage.py runserver"
echo ""
echo "For more information, see README.md and SETUP_GUIDE.md"
echo ""
echo -e "${YELLOW}Note: Make sure to activate the virtual environment before running Django:${NC}"
echo "  source venv/bin/activate"
echo ""