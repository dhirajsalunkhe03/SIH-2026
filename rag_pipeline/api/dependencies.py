#!/usr/bin/env python3
"""
FastAPI dependencies for the Legal RAG API.
"""

from functools import lru_cache
from typing import Optional
from fastapi import Depends, HTTPException, status
from contextlib import asynccontextmanager

from rag_engine import LegalRAG, create_rag_engine, RAGAnswer
from retriever import LegalRetriever
from config import get_config, Phase4Config


# Global instances (initialized at startup)
_rag_engine: Optional[LegalRAG] = None
_config: Optional[object] = None


def get_config_instance() -> Phase4Config:
    """Get the global configuration instance."""
    from config import get_config
    return get_config()


@lru_cache(maxsize=1)
def get_retriever() -> LegalRetriever:
    """Get or create the LegalRetriever instance."""
    config = get_config_instance()
    retriever = LegalRetriever(
        vector_db_path=config.retriever.vector_db_path,
        model_name=config.retriever.model_name,
        collection_name=config.retriever.collection_name
    )
    retriever.load()
    return retriever


def get_rag_engine() -> LegalRAG:
    """Get or create the LegalRAG engine instance."""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = create_rag_engine()
    return _rag_engine


async def verify_ollama_health() -> bool:
    """Check if Ollama is available and model is loaded."""
    from ollama_utils import OllamaClient
    from config import get_config
    try:
        config = get_config()
        client = OllamaClient(model=config.ollama.model, host=config.ollama.host)
        return client.check_availability()
    except Exception:
        return False


async def verify_chromadb_health() -> bool:
    """Check if ChromaDB is accessible."""
    try:
        retriever = get_retriever()
        # Try a simple query
        _ = retriever.collection.count()
        return True
    except Exception:
        return False


async def verify_retriever_health() -> bool:
    """Check if retriever is working."""
    try:
        retriever = get_retriever()
        # Test with a simple query
        results = retriever.search("test", top_k=1)
        return True
    except Exception:
        return False


async def verify_embedding_model_health() -> bool:
    """Check if embedding model is loaded."""
    try:
        retriever = get_retriever()
        # Check if model is loaded
        return retriever.model is not None
    except Exception:
        return False