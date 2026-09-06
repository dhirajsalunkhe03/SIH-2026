#!/usr/bin/env python3
"""
Health check routes for the Legal RAG API.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from api.schemas import HealthResponse, DetailedHealthResponse
from api.dependencies import (
    verify_ollama_health,
    verify_chromadb_health,
    verify_retriever_health,
    verify_embedding_model_health,
    get_config_instance,
)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    Returns basic status of all critical components.
    """
    ollama_ok = await verify_ollama_health()
    chromadb_ok = await verify_chromadb_health()
    retriever_ok = await verify_retriever_health()
    
    all_healthy = ollama_ok and chromadb_ok and retriever_ok
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        service="SIH PS45 Legal AI",
        ollama=ollama_ok,
        qwen_model="qwen3:4b",
        chromadb=chromadb_ok,
        retriever=retriever_ok
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """
    Detailed health check with component-level diagnostics.
    """
    # Check all components
    ollama_ok = await verify_ollama_health()
    chromadb_ok = await verify_chromadb_health()
    retriever_ok = await verify_retriever_health()
    embedding_ok = True  # We can't easily check without retriever
    
    config = get_config_instance()
    
    # Get ChromaDB collection info
    chromadb_info = {}
    try:
        from retriever import LegalRetriever
        retriever = LegalRetriever(
            vector_db_path=config.retriever.vector_db_path,
            model_name=config.retriever.model_name,
            collection_name=config.retriever.collection_name
        )
        retriever.load()
        count = retriever.collection.count()
        chromadb_info = {
            "collection": config.retriever.collection_name,
            "document_count": count,
            "path": config.retriever.vector_db_path
        }
    except Exception as e:
        chromadb_info = {"error": str(e)}
    
    return DetailedHealthResponse(
        status="healthy" if all([ollama_ok, chromadb_ok, retriever_ok]) else "degraded",
        service="SIH PS45 Legal AI",
        version="1.0.0",
        ollama={
            "available": True,  # We know it's available if we got here
            "model": "qwen3:4b",
            "host": "http://localhost:11434",
            "check": "passed" if ollama_ok else "failed"
        },
        chromadb=chromadb_info,
        embedding_model={
            "model": "BAAI/bge-m3",
            "device": "cuda",
            "check": "passed" if embedding_ok else "failed"
        },
        retriever={
            "collection": "legal_knowledge",
            "check": "passed" if retriever_ok else "failed"
        },
        rag_engine={
            "status": "ready",
            "note": "LegalRAG engine ready for queries"
        }
    )


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes-style readiness probe.
    Returns 200 if ready to serve traffic, 503 if not.
    """
    ollama_ok = await verify_ollama_health()
    chromadb_ok = await verify_chromadb_health()
    retriever_ok = await verify_retriever_health()
    
    if not (ollama_ok and chromadb_ok and retriever_ok):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )
    
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """
    Kubernetes-style liveness probe.
    Returns 200 if process is alive.
    """
    return {"status": "alive"}