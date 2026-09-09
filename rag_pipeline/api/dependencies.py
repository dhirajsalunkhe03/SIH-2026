#!/usr/bin/env python3
"""
FastAPI dependencies for the Legal RAG API.
Production-hardened with proper error handling and caching.
"""

from functools import lru_cache
from typing import Optional
from fastapi import Depends, HTTPException, status

from rag_engine import LegalRAG, create_rag_engine
from retriever import LegalRetriever
from config import get_config, Phase8Config


# Global instances (initialized at startup)
_rag_engine: Optional[LegalRAG] = None
_retriever: Optional[LegalRetriever] = None


def get_config_instance() -> Phase8Config:
    """Get the global configuration instance."""
    return get_config()


@lru_cache(maxsize=1)
def get_retriever() -> LegalRetriever:
    """Get or create the LegalRetriever instance."""
    global _retriever
    if _retriever is None:
        config = get_config_instance()
        _retriever = LegalRetriever(
            vector_db_path=config.retriever.vector_db_path,
            model_name=config.retriever.model_name,
            collection_name=config.retriever.collection_name,
            device=config.retriever.device,
            use_cpu=config.retriever.use_cpu
        )
        _retriever.load()
    return _retriever


def get_rag_engine() -> LegalRAG:
    """Get or create the LegalRAG engine instance."""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = create_rag_engine()
    return _rag_engine


async def verify_ollama_health() -> bool:
    """Check if Ollama is available and model is loaded."""
    from ollama_utils import OllamaClient
    try:
        config = get_config_instance()
        client = OllamaClient(model=config.ollama.model, host=config.ollama.host)
        return client.check_availability()
    except Exception as e:
        return False


async def verify_chromadb_health() -> bool:
    """Check if ChromaDB is accessible."""
    try:
        retriever = get_retriever()
        _ = retriever.collection.count()
        return True
    except Exception:
        return False


async def verify_retriever_health() -> bool:
    """Check if retriever is working."""
    try:
        retriever = get_retriever()
        results = retriever.search("test", top_k=1)
        return True
    except Exception:
        return False


async def verify_embedding_model_health() -> bool:
    """Check if embedding model is loaded."""
    try:
        retriever = get_retriever()
        return retriever.model is not None
    except Exception:
        return False


# Error handling helpers
class RAGError(Exception):
    """Custom exception for RAG processing errors."""
    def __init__(self, message: str, error_type: str = "processing_error", details: dict = None):
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        super().__init__(message)


async def handle_rag_error(e: Exception) -> HTTPException:
    """Convert RAG errors to appropriate HTTP exceptions."""
    if isinstance(e, RAGError):
        if e.error_type == "translation_error":
            return HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "Translation service unavailable",
                    "message": e.message,
                    "details": e.details
                }
            )
        elif e.error_type == "retrieval_error":
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Retrieval failed",
                    "message": e.message,
                    "details": e.details
                }
            )
        elif e.error_type == "generation_error":
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Generation failed",
                    "message": e.message,
                    "details": e.details
                }
            )
        elif e.error_type == "validation_error":
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Invalid request",
                    "message": e.message,
                    "details": e.details
                }
            )
    
    # Generic error
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "error": "Internal server error",
            "message": str(e),
            "details": {}
        }
    )