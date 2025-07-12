# Alert RCA Management System

A comprehensive system for automated alert grouping and Root Cause Analysis (RCA) generation using AI/ML technologies.

## 🚀 Features

- **Automated Alert Grouping**: Intelligently groups similar alerts using machine learning similarity algorithms
- **AI-Powered RCA Generation**: Uses OLLAMA/LLAMA3 LLM with RAG (Retrieval-Augmented Generation) for root cause analysis
- **Vector Database Integration**: ChromaDB for storing and retrieving historical incident data
- **Interactive Web UI**: Streamlit-based frontend for alert and RCA management
- **RESTful API**: FastAPI backend with comprehensive endpoints
- **Status Management**: Track RCA lifecycle from open → in-progress → closed
- **Historical Search**: Find similar past incidents using vector similarity search

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Monitoring    │    │   Alert RCA     │    │    Vector DB    │
│    Systems      │───▶│   Management    │───▶│   (ChromaDB)    │
│                 │    │     System      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  LLM (OLLAMA/   │
                    │     LLAMA3)     │
                    └─────────────────┘
```

### Components

- **Backend**: FastAPI with PostgreSQL database
- **Frontend**: Streamlit web application
- **LLM Engine**: OLLAMA running LLAMA3 model
- **Vector Database**: ChromaDB for RAG functionality
- **Alert Grouping**: Sentence Transformers for similarity analysis

## 📋 Prerequisites

- **Python 3.10+**
- **PostgreSQL 12+**
- **OLLAMA** with LLAMA3 model
- **Ubuntu 20.04+** (or compatible Linux distribution)

## ⚡ Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd alert-rca-system

# Make setup script executable and run
chmod +x setup.sh
./setup.sh
```

The setup script will:
- Install PostgreSQL (if needed)
- Install OLLAMA and pull LLAMA3 model
- Create Python virtual environment
- Install dependencies
- Setup database and ChromaDB
- Create environment configuration

### 2. Configure Environment

```bash
# Copy and edit environment configuration
cp .env.example .env
# Edit .env with your specific settings
```

### 3. Start Services

**Terminal 1 - Backend API:**
```bash
cd backend
source ../venv/bin/activate
python main.py
```

**Terminal 2 - Frontend UI:**
```bash
cd frontend
source ../venv/bin/activate
streamlit run main.py
```

### 4. Access the Application

- **Frontend UI**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📖 Usage Guide

### Creating Alerts

#### Via API
```bash
curl -X POST "http://localhost:8000/api/alerts/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "High CPU Usage",
    "description": "CPU usage exceeded 85%",
    "severity": "high",
    "source_system": "prometheus",
    "metric_name": "cpu_usage",
    "metric_value": 87.5,
    "threshold": 85.0
  }'
```

#### Via Web UI
1. Navigate to **Alerts** → **Create Alert**
2. Fill in alert details
3. Submit to automatically group with similar alerts

### Generating RCA

#### Automatic Generation
When alerts are grouped, you can generate RCA:

1. Go to **Alerts** → **Alert Groups**
2. Find the relevant group
3. Click **Generate RCA**
4. Check **RCA Details** for the generated analysis

#### API Endpoint
```bash
curl -X POST "http://localhost:8000/api/rca/generate?group_id=<group-id>"
```

### Managing RCA Lifecycle

1. **Open**: Newly generated RCA
2. **In Progress**: Analyst working on the RCA
3. **Closed**: RCA completed and stored in vector DB

Update status via:
- Web UI: **RCA Details** → **Edit** tab
- API: PUT `/api/rca/{rca_id}`

### Searching Historical Incidents

Use the vector database to find similar past incidents:

```bash
curl -X GET "http://localhost:8000/api/rca/search/historical?query=database%20performance&limit=5"
```

Or via Web UI: **RCA Dashboard** → **Search Historical**

## 🛠️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `alert_rca_db` |
| `OLLAMA_BASE_URL` | OLLAMA API URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | LLM model name | `llama3` |
| `CHROMADB_PERSIST_DIR` | ChromaDB data directory | `./chromadb_data` |
| `SIMILARITY_THRESHOLD` | Alert grouping threshold | `0.8` |
| `ALERT_GROUPING_WINDOW_MINUTES` | Grouping time window | `5` |

### Alert Grouping Configuration

Adjust similarity thresholds and time windows in `.env`:

```bash
SIMILARITY_THRESHOLD=0.8  # 80% similarity required for grouping
ALERT_GROUPING_WINDOW_MINUTES=5  # Group alerts within 5 minutes
```

## 🔧 API Reference

### Core Endpoints

#### Alerts
- `POST /api/alerts/` - Create alert
- `GET /api/alerts/` - List alerts with filters
- `GET /api/alerts/{alert_id}` - Get specific alert
- `PUT /api/alerts/{alert_id}` - Update alert
- `GET /api/alerts/groups/` - List alert groups
- `POST /api/alerts/regroup` - Regroup alerts

#### RCA Management
- `POST /api/rca/generate` - Generate RCA for group
- `GET /api/rca/` - List RCAs with filters
- `GET /api/rca/{rca_id}` - Get specific RCA
- `PUT /api/rca/{rca_id}` - Update RCA
- `GET /api/rca/{rca_id}/alerts` - Get related alerts
- `GET /api/rca/{rca_id}/history` - Get status history

#### Vector Operations
- `POST /api/rca/bulk-vectorize` - Store closed RCAs in vector DB
- `GET /api/rca/search/historical` - Search historical incidents

#### System
- `GET /health` - System health check
- `GET /api/system/info` - System information

### Sample API Calls

**Create Multiple Alerts:**
```bash
curl -X POST "http://localhost:8000/api/alerts/bulk" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "title": "Database Connection Issues",
      "severity": "critical",
      "source_system": "db-monitor"
    },
    {
      "title": "High Memory Usage",
      "severity": "high", 
      "source_system": "system-monitor"
    }
  ]'
```

**Update RCA Status:**
```bash
curl -X PUT "http://localhost:8000/api/rca/{rca_id}" \
  -H "Content-Type: application/json" \
  -d '{"status": "closed"}' \
  --data-urlencode "changed_by=analyst" \
  --data-urlencode "change_reason=Analysis completed"
```

## 🧪 Testing with Sample Data

Generate sample data for testing:

```bash
# Create sample alerts and RCAs
python scripts/sample_data.py

# Create only alerts
python scripts/sample_data.py --alerts-only

# Clear all data
python scripts/sample_data.py --clear
```

## 🔍 Monitoring and Maintenance

### Database Management

```bash
# Reset database
python scripts/init_db.py --reset

# Initialize fresh database
python scripts/init_db.py
```

### ChromaDB Management

```bash
# Setup ChromaDB
python scripts/setup_chromadb.py

# Test ChromaDB functionality
python scripts/setup_chromadb.py --test

# Reset vector database
python scripts/setup_chromadb.py --reset
```

### Health Checks

Monitor system health via:
- API: `GET /health`
- Web UI: Status indicators in sidebar

## 📊 System Workflow

1. **Alert Ingestion**: Monitoring systems send alerts to API
2. **Automatic Grouping**: Similar alerts grouped using ML similarity
3. **RCA Generation**: LLM analyzes grouped alerts with RAG context
4. **Status Management**: RCAs progress through open → in-progress → closed
5. **Vector Storage**: Closed RCAs stored for future similarity matching
6. **Historical Analysis**: Past incidents help improve future RCAs

## 🔧 Troubleshooting

### Common Issues

**OLLAMA Not Available:**
```bash
# Check OLLAMA status
ollama list

# Pull LLAMA3 model if missing
ollama pull llama3

# Check OLLAMA service
curl http://localhost:11434/api/tags
```

**Database Connection Issues:**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Restart PostgreSQL
sudo systemctl restart postgresql

# Check database connection
python -c "from backend.database import engine; engine.connect()"
```

**ChromaDB Issues:**
```bash
# Reset ChromaDB
python scripts/setup_chromadb.py --reset

# Check ChromaDB directory permissions
ls -la ./chromadb_data/
```

### Log Files

- Backend logs: Console output from `python main.py`
- Database logs: PostgreSQL logs in `/var/log/postgresql/`
- OLLAMA logs: Check with `journalctl -u ollama`

## 🚀 Production Deployment

### Security Considerations

1. **Change default passwords** in `.env`
2. **Configure CORS** properly in `backend/main.py`
3. **Use HTTPS** with reverse proxy (nginx/Apache)
4. **Restrict database access** to application only
5. **Enable authentication** for production use

### Scaling

- **Database**: Consider PostgreSQL clustering for high availability
- **LLM**: Deploy OLLAMA on separate GPU-enabled servers
- **Vector DB**: ChromaDB supports distributed deployment
- **Application**: Use load balancers for multiple FastAPI instances

### Backup Strategy

```bash
# Database backup
pg_dump alert_rca_db > backup.sql

# ChromaDB backup
tar -czf chromadb_backup.tar.gz chromadb_data/

# Restore database
psql alert_rca_db < backup.sql
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Create Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review API documentation at `/docs`
3. Create an issue in the repository
4. Check system health at `/health`

## 🔄 Version History

- **v1.0.0**: Initial release with core functionality
  - Alert ingestion and grouping
  - LLM-powered RCA generation
  - Vector database integration
  - Web UI and API

---

**Built with ❤️ using FastAPI, Streamlit, OLLAMA, and ChromaDB**
