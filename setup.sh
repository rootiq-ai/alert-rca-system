#!/bin/bash

# Alert RCA Management System Setup Script
# Compatible with Ubuntu and Python 3.10

set -e

echo "🚀 Setting up Alert RCA Management System..."

# Check Python version
python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.10+ required. Current version: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL not found. Installing..."
    sudo apt update
    sudo apt install -y postgresql postgresql-contrib
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
else
    echo "✅ PostgreSQL found"
fi

# Check if OLLAMA is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ OLLAMA not found. Installing..."
    curl -fsSL https://ollama.ai/install.sh | sh
    echo "📥 Pulling LLAMA3 model..."
    ollama pull llama3
else
    echo "✅ OLLAMA found"
    # Ensure llama3 model is available
    if ! ollama list | grep -q llama3; then
        echo "📥 Pulling LLAMA3 model..."
        ollama pull llama3
    fi
fi

# Create virtual environment
echo "🐍 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Create environment file
if [ ! -f .env ]; then
    echo "📄 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please update .env with your configuration"
fi

# Setup PostgreSQL database
echo "🗄️  Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE DATABASE alert_rca_db;" 2>/dev/null || echo "Database already exists"
sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'password';" 2>/dev/null || echo "User already exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE alert_rca_db TO postgres;" 2>/dev/null || echo "Privileges already granted"

# Initialize database
echo "🗄️  Initializing database schema..."
python scripts/init_db.py

# Setup ChromaDB
echo "🔍 Setting up ChromaDB..."
python scripts/setup_chromadb.py

# Create log directory
mkdir -p logs

echo "✅ Setup complete!"
echo ""
echo "🚀 To start the application:"
echo "1. Backend: cd backend && python main.py"
echo "2. Frontend: cd frontend && streamlit run main.py"
echo ""
echo "🌐 Access URLs:"
echo "- Backend API: http://localhost:8000"
echo "- Frontend UI: http://localhost:8501"
echo "- API Docs: http://localhost:8000/docs"
