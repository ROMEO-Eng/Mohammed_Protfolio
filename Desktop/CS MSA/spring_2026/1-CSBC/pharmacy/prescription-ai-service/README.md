# Prescription AI Service

AI-powered prescription analysis microservice for the pharmacy management system. Provides OCR extraction, LLM-based entity extraction, and product matching capabilities.

## Features

- **Prescription Upload API** - Accept prescription images for analysis
- **OCR Pipeline** - Extract text from prescription images using PaddleOCR
- **LLM Processing** - Analyze medical text using Qwen3 8B or Llama 3.1 8B
- **Entity Extraction** - Extract drug names, dosages, frequencies, and durations
- **Product Matching** - Match extracted medications with pharmacy inventory
- **Confidence Scoring** - Provide confidence scores for all extractions
- **Async Processing** - Background job processing with Celery
- **Comprehensive APIs** - RESTful APIs with OpenAPI documentation

## Tech Stack

- **Framework:** FastAPI (Python 3.12)
- **Database:** MongoDB (async with Motor)
- **Caching:** Redis
- **OCR:** PaddleOCR
- **LLM:** Qwen3 8B (primary) / Llama 3.1 8B (fallback)
- **Task Queue:** Celery with Redis
- **Deployment:** Docker & Docker Compose

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- 8GB RAM (for LLM models)

### Development Setup

1. **Clone and navigate to project:**
```bash
cd prescription-ai-service
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements/dev.txt
```

4. **Setup environment variables:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Start services with Docker Compose:**
```bash
docker-compose up -d
```

6. **Run application:**
```bash
uvicorn app.main:app --reload
```

Application will be available at: `http://localhost:8001`

API Documentation: `http://localhost:8001/api/docs`

### Docker Deployment

1. **Build and run with Docker Compose:**
```bash
docker-compose up --build
```

2. **Access services:**
- API: `http://localhost:8001`
- MongoDB: `mongodb://root:password@localhost:27017`
- Redis: `redis://localhost:6379`

## Project Structure

```
prescription-ai-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point
│   ├── config/                 # Configuration
│   │   ├── settings.py
│   │   ├── database.py
│   │   └── __init__.py
│   ├── api/                    # API endpoints
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── health.py
│   │   │   │   └── prescriptions.py
│   │   │   └── api.py
│   │   ├── deps.py
│   │   └── __init__.py
│   ├── core/                   # Core functionality
│   │   ├── security.py
│   │   ├── exceptions.py
│   │   └── __init__.py
│   ├── models/                 # Pydantic models
│   │   ├── prescription.py
│   │   ├── analysis.py
│   │   └── __init__.py
│   ├── services/               # Business logic (to implement)
│   ├── utils/                  # Utilities (to implement)
│   └── repositories/           # Data access (to implement)
├── tests/                      # Test suite
├── docker/                     # Docker configuration
├── requirements/               # Python dependencies
├── pyproject.toml
├── .env.example
└── README.md
```

## API Endpoints

### Health Check
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed diagnostics

### Prescriptions
- `POST /api/v1/prescriptions/analyze` - Upload prescription for analysis
- `GET /api/v1/prescriptions/{id}/status` - Check analysis status
- `GET /api/v1/prescriptions/{id}/results` - Get analysis results

## Configuration

Edit `.env` file for configuration:

```env
# Application
APP_NAME=Prescription AI Service
DEBUG=false
ENVIRONMENT=development

# Database
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=pharmacy_ai

# Redis
REDIS_URL=redis://localhost:6379/0

# OCR Settings
OCR_LANGUAGE=en
OCR_USE_GPU=false

# LLM Settings
LLM_MODEL_TYPE=qwen
QWEN_MODEL_NAME=Qwen/Qwen1.5-7B-Chat
```

## Development

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app

# Specific test file
pytest tests/unit/test_health.py

# Watch mode
pytest-watch
```

### Code Quality

```bash
# Format code
black app tests

# Sort imports
isort app tests

# Lint
flake8 app tests

# Type checking
mypy app

# Security check
bandit -r app
```

### Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

## Integration with Pharmacy System

### Spring Boot Backend Integration

The AI service integrates with Spring Boot via REST APIs:

1. **Prescription Submission:**
   - Frontend uploads image to Spring Boot
   - Spring Boot proxies to AI service `POST /api/v1/prescriptions/analyze`
   - AI service returns `prescription_id`

2. **Status Polling:**
   - Frontend polls Spring Boot
   - Spring Boot queries AI service `GET /api/v1/prescriptions/{id}/status`

3. **Results Retrieval:**
   - Once completed, fetch results from AI service
   - Spring Boot integrates with inventory for product matching
   - Add matched products to cart

### React Frontend Integration

1. **Upload Component** - `PrescriptionUpload.jsx`
   - File upload with preview
   - Progress tracking

2. **Results Display** - `PrescriptionResults.jsx`
   - Show extracted medications
   - Confidence scores
   - Matched products with add-to-cart

3. **History Page** - `PrescriptionHistory.jsx`
   - List of analyzed prescriptions
   - Re-analyze capabilities

## Performance Targets

- **Processing Time:** <30 seconds per prescription
- **Accuracy:** >90% for common medications
- **Throughput:** 100 concurrent analyses
- **Availability:** 99.9% uptime

## Security

- JWT authentication for all endpoints
- HTTPS recommended for production
- Sensitive data encrypted at rest
- HIPAA-compliant audit logging
- Input validation and sanitization

## Troubleshooting

### MongoDB connection fails
```bash
# Check MongoDB is running
docker-compose logs mongodb

# Verify connection string in .env
MONGODB_URL=mongodb://root:password@mongodb:27017/pharmacy_ai?authSource=admin
```

### Redis connection fails
```bash
# Check Redis is running
docker-compose logs redis

# Test connection
redis-cli ping
```

### OCR not working
```bash
# Check GPU availability
nvidia-smi

# Force CPU mode in .env
OCR_USE_GPU=false
```

## Production Deployment

1. **Update environment variables** for production
2. **Use Kubernetes manifests** in `/k8s`
3. **Configure monitoring** with Prometheus
4. **Setup log aggregation** with ELK or similar
5. **Use SSL certificates** for HTTPS
6. **Scale replicas** based on load

## Next Steps

- Phase 2: Implement OCR pipeline (TASK-AI-006 to TASK-AI-010)
- Phase 3: Implement LLM integration (TASK-AI-011 to TASK-AI-015)
- Phase 4: Implement product matching (TASK-AI-016 to TASK-AI-020)
- Phase 5: Frontend integration (TASK-AI-021 to TASK-AI-025)
- Phase 6: Production deployment (TASK-AI-026 to TASK-AI-030)

## License

MIT

## Support

For issues, questions, or contributions, please refer to the main pharmacy project repository.
