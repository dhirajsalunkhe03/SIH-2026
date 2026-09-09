#!/usr/bin/env python3
"""
FastAPI main application for SIH 2026 Legal RAG API.
Production-hardened with monitoring, error handling, and configuration.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging
from typing import Dict, Any
from collections import defaultdict

from api.routes import routers
from api.dependencies import get_rag_engine, get_config_instance
from config import get_config, Phase8Config


# Configure logging
def setup_logging(config: Phase8Config):
    """Setup application logging."""
    log_dir = config.logging.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, config.logging.log_level),
        format=config.logging.log_format,
        handlers=[
            logging.FileHandler(log_dir / "api.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("legal_rag_api")


logger = logging.getLogger("legal_rag_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    config = get_config()
    setup_logging(config)
    
    # Startup
    logger.info("Starting SIH PS45 Legal RAG API...")
    try:
        # Pre-load the RAG engine
        engine = get_rag_engine()
        logger.info("LegalRAG engine loaded successfully")
        app.state.rag_engine_ready = True
    except Exception as e:
        logger.error(f"Failed to load RAG engine on startup: {e}")
        app.state.rag_engine_ready = False
    
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


# Add CORS middleware
@app.on_event("startup")
async def setup_cors():
    """Setup CORS from configuration."""
    config = get_config()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.get_cors_origins_list(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )


# Request timing and monitoring middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header and log request metrics."""
    start_time = time.time()
    
    # Track request
    app.state.request_count = getattr(app.state, 'request_count', 0) + 1
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log metrics
        logger.info(
            f"Request: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Latency: {process_time:.3f}s"
        )
        
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request failed: {request.method} {request.url.path} - Latency: {process_time:.3f}s - Error: {e}")
        raise


# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple in-memory rate limiting per client IP."""
    config = get_config()
    
    # Skip rate limiting for health checks
    if request.url.path.startswith("/health") or request.url.path in ["/", "/api/info", "/api/metrics", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    # Get rate limit config
    rate_limit = config.api.rate_limit_requests
    rate_window = config.api.rate_limit_window
    
    if rate_limit <= 0:
        # Rate limiting disabled
        return await call_next(request)
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Initialize rate limit storage
    if not hasattr(app.state, 'rate_limit_store'):
        app.state.rate_limit_store = defaultdict(list)
    
    now = time.time()
    window_start = now - rate_window
    
    # Clean old entries
    app.state.rate_limit_store[client_ip] = [
        ts for ts in app.state.rate_limit_store[client_ip] if ts > window_start
    ]
    
    # Check rate limit
    if len(app.state.rate_limit_store[client_ip]) >= rate_limit:
        logger.warning(f"Rate limit exceeded for {client_ip}")
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "error": "Rate limit exceeded",
                "detail": f"Maximum {rate_limit} requests per {rate_window} seconds"
            }
        )
    
    # Record request
    app.state.rate_limit_store[client_ip].append(now)
    
    return await call_next(request)


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
    config = get_config()
    return {
        "name": "SIH 2026 PS45 Legal RAG API",
        "version": "1.0.0",
        "embedding_model": config.embedder.model_name,
        "llm": f"{config.ollama.model} via Ollama",
        "vector_db": "ChromaDB",
        "collection": config.retriever.collection_name,
        "supported_languages": list(config.language.supported_languages.keys()),
        "supported_domains": [
            "all", "biodiversity", "abs", "traditional_knowledge",
            "patents", "trademarks", "gi", "designs", "general_legal"
        ],
        "config": {
            "api_host": config.api.host,
            "api_port": config.api.port,
            "translation_enabled": config.translation.enabled
        }
    }


# API metrics endpoint (lightweight monitoring)
@app.get("/api/metrics")
async def api_metrics():
    """Lightweight monitoring endpoint with request metrics."""
    return {
        "request_count": getattr(app.state, 'request_count', 0),
        "rag_engine_ready": getattr(app.state, 'rag_engine_ready', False),
        "uptime_seconds": time.time() - getattr(app.state, 'start_time', time.time())
    }


if __name__ == "__main__":
    import uvicorn
    config = get_config()
    uvicorn.run(
        "api.main:app",
        host=config.api.host,
        port=config.api.port,
        reload=False,  # Disable reload in production
        log_level=config.logging.log_level.lower(),
        workers=config.api.workers,
        timeout_keep_alive=config.api.request_timeout
    )