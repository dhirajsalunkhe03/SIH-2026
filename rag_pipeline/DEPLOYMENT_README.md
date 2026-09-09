# SIH 2026 PS45 - Legal RAG Pipeline Deployment Guide

## Quick Start (Development)

### Prerequisites
- Python 3.10+
- Ollama with `qwen3:4b` model
- NVIDIA GPU with 6GB+ VRAM (or CPU fallback)
- 16GB+ RAM recommended

### Install Dependencies
```bash
cd /home/dhiraj/Desktop/SIH/rag_pipeline
pip install -r requirements-prod.txt
```

### Start Ollama
```bash
ollama serve
# In another terminal:
ollama pull qwen3:4b
```

### Start API Server
```bash
cd /home/dhiraj/Desktop/SIH/rag_pipeline
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

### Start Streamlit Frontend
```bash
cd /home/dhiraj/Desktop/SIH/rag_pipeline
streamlit run app.py --server.port 8501
```

### Access
- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs
- Frontend: http://127.0.0.1:8501

---

## Production Deployment

### Environment Configuration
```bash
cp .env.example .env
# Edit .env with production values
```

### Using Gunicorn (Production WSGI)
```bash
cd /home/dhiraj/Desktop/SIH/rag_pipeline
gunicorn api.main:app \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 180 \
    --log-level info \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log
```

### Docker Deployment

#### Build Image
```bash
cd /home/dhiraj/Desktop/SIH/rag_pipeline
docker build -t sih-legal-rag:latest .
```

#### Run Container
```bash
docker run -d \
    --name sih-legal-rag \
    --gpus all \
    -p 8000:8000 \
    -v /path/to/vector_db:/app/vector_db \
    -v /path/to/logs:/app/logs \
    -v /path/to/.env:/app/.env \
    sih-legal-rag:latest
```

### Systemd Service (Linux)
```ini
# /etc/systemd/system/sih-legal-rag.service
[Unit]
Description=SIH PS45 Legal RAG API
After=network.target ollama.service
Requires=ollama.service

[Service]
Type=exec
User=dhiraj
WorkingDirectory=/home/dhiraj/Desktop/SIH/rag_pipeline
EnvironmentFile=/home/dhiraj/Desktop/SIH/rag_pipeline/.env
ExecStart=/usr/local/bin/gunicorn api.main:app \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 180 \
    --log-level info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable sih-legal-rag
sudo systemctl start sih-legal-rag
```

---

## Configuration Reference

### Required Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `RAG_OLLAMA_MODEL` | `qwen3:4b` | Ollama model name |
| `RAG_VECTOR_DB_PATH` | `./vector_db` | ChromaDB path |
| `RAG_API_HOST` | `127.0.0.1` | API bind address |
| `RAG_API_PORT` | `8000` | API port |

### Optional Variables
See `.env.example` for complete list including:
- Embedding model/device settings
- Translation model/device settings
- Retrieval thresholds
- CORS origins
- Logging level

---

## API Endpoints

### Health Checks
- `GET /health` - Basic health
- `GET /health/detailed` - Component diagnostics
- `GET /health/ready` - Kubernetes readiness
- `GET /health/live` - Kubernetes liveness

### Chat
- `POST /api/chat` - Main query endpoint
- `GET /api/chat/suggestions` - Query autocomplete

### Monitoring
- `GET /api/metrics` - Request metrics

---

## Smoke Testing

```bash
# Run smoke tests
cd /home/dhiraj/Desktop/SIH/rag_pipeline
python3 -m pytest tests/test_smoke.py -v
```

Or run the standalone test:
```bash
python3 tests/test_smoke.py
```

---

## Monitoring & Logs

### Key Log Files
- `logs/api.log` - API requests and errors
- `logs/rag_engine.log` - RAG pipeline details

### Metrics to Watch
- Request count (`/api/metrics`)
- Average latency per component
- Error rates by type
- GPU memory usage

### Health Check Automation
```bash
#!/bin/bash
# health_check.sh
curl -f http://127.0.0.1:8000/health/ready || exit 1
```

---

## Troubleshooting

### Common Issues

**Ollama not available**
```bash
ollama serve
ollama pull qwen3:4b
```

**CUDA Out of Memory**
```bash
# Set in .env
RAG_EMBEDDING_USE_CPU=true
RAG_TRANSLATION_CPU_FALLBACK=true
```

**Slow first request**
- Translation model loads on first request (~10s)
- Consider pre-loading in startup script

**ChromaDB connection failed**
```bash
# Check path and permissions
ls -la /home/dhiraj/Desktop/SIH/rag_pipeline/vector_db
```

---

## SIH Demo Setup

For the final SIH demonstration:

1. **Pre-load everything**:
   ```bash
   # Start Ollama
   ollama serve &
   sleep 5
   ollama pull qwen3:4b
   
   # Pre-load translation model
   python3 -c "from translation_service import get_translation_service; get_translation_service().load_models()"
   
   # Start API
   gunicorn api.main:app --workers 1 --bind 0.0.0.0:8000
   
   # Start Streamlit
   streamlit run app.py --server.port 8501 --server.headless true
   ```

2. **Demo queries to test**:
   - English: "What does Section 11 of the Patents Act deal with?"
   - Hindi: "पेटेंट क्या है?"
   - Marathi: "पारंपरिक ज्ञान काय आहे?"
   - Multi-domain: "Can traditional knowledge be protected through patents?"

3. **Verify health**:
   - API: http://localhost:8000/health
   - Frontend: http://localhost:8501

---

## Security Notes

- API runs locally only (127.0.0.1) by default
- No authentication in current version - add if exposing publicly
- No sensitive data stored in logs
- All processing local (no external API calls)

---

## Support

For issues:
1. Check logs in `logs/`
2. Verify Ollama is running: `ollama list`
3. Check GPU memory: `nvidia-smi`
4. Verify ChromaDB: `ls -la vector_db/`