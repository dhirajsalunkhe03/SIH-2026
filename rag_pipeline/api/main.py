#!/usr/bin/env python3
"""
FastAPI main application for SIH 2026 Legal RAG API.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging

from api.routes import routers
from api.dependencies import get_rag_engine, get_config_instance
from config import get_config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("legal_rag_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("Starting SIH PS45 Legal RAG API...")
    try:
        # Pre-load the RAG engine
        engine = get_rag_engine()
        logger.info("LegalRAG engine loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load RAG engine: {e}")
        # Don't fail startup - let health checks handle it
    
    yield
    
    # Shutdown
    logger.info("Shutting down SIH PS45 Legal RAG API...")


# Create FastAPI app
app = FastAPI(
    title="SIH 2026 PS45 Legal RAG API",
    description="""
    AI-powered multilingual legal intelligence system for Indian legal provisions.
    
    Supports:
    - Traditional Knowledge (TK)
    - Biodiversity
    - Access & Benefit Sharing (ABS)
    - Patents
    - Geographical Indications (GI)
    - Trademarks
    - Industrial Designs
    - Indian legal provisions
    
    Features:
    - Multilingual queries (10 Indian languages + English)
    - Domain-specific retrieval
    - Source citations with section/rule/page references
    - Confidence scoring
    - Local-only AI processing (Ollama + qwen3:4b)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if str(exc) else "Unknown error"
        }
    )


# Include routers
for router in routers:
    app.include_router(router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "SIH 2026 PS45 Legal RAG API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


# API info endpoint
@app.get("/api/info")
async def api_info():
    from config import get_config
    config = get_config()
    return {
        "name": "SIH 2026 PS45 Legal RAG API",
        "version": "1.0.0",
        "embedding_model": "BAAI/bge-m3",
        "llm": "qwen3:4b via Ollama",
        "vector_db": "ChromaDB",
        "collection": "legal_knowledge",
        "documents": 10,
        "chunks": 1185,
        "supported_languages": list(config.language.supported_languages.keys()),
        "supported_domains": [
            "all", "biodiversity", "abs", "traditional_knowledge",
            "patents", "trademarks", "gi", "designs", "general_legal"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )