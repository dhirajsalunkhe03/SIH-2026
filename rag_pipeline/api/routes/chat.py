#!/usr/bin/env python3
"""
Chat routes for the Legal RAG API.
"""

import time
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List

from api.schemas import (
    ChatRequest, ChatResponse, SourceCitation, LatencyInfo, DetectedLanguage,
    LanguageCode, DomainCode, DocumentTypeCode
)
from api.dependencies import get_rag_engine
from rag_engine import LegalRAG

router = APIRouter(prefix="/api", tags=["Chat"])


def map_domain_code(domain: Optional[str]) -> Optional[str]:
    """Map domain code to internal domain name (capitalized to match database)."""
    if not domain or domain == "all":
        return None
    # Domain codes are lowercase in enum, but database stores capitalized
    domain_map = {
        "biodiversity": "Biodiversity",
        "abs": "Access & Benefit Sharing",
        "traditional_knowledge": "Traditional Knowledge",
        "patents": "Patents",
        "trademarks": "Trademarks",
        "gi": "Geographical Indications",
        "designs": "Designs",
        "general_legal": "General Legal",
    }
    return domain_map.get(domain.lower(), domain)


def map_document_type(doc_type: Optional[str]) -> Optional[str]:
    """Map document type code to internal name."""
    if not doc_type:
        return None
    type_map = {
        "Act": "Act",
        "Rules": "Rules",
        "Amendment Act": "Amendment Act",
        "Notification": "Notification",
        "Order": "Order",
        "Other": "Other"
    }
    return type_map.get(doc_type, doc_type)


def format_sources_for_response(retrieved_chunks: List[dict]) -> List[SourceCitation]:
    """Format retrieved chunks as source citations for API response."""
    sources = []
    for chunk in retrieved_chunks:
        source = SourceCitation(
            document=chunk.get('document', ''),
            document_type=chunk.get('document_type', ''),
            document_year=chunk.get('document_year') if chunk.get('document_year') else None,
            section=chunk.get('section_number') if chunk.get('section_number') else None,
            section_title=chunk.get('section_title') if chunk.get('section_title') else None,
            rule=chunk.get('rule_number') if chunk.get('rule_number') else None,
            rule_title=chunk.get('rule_title') if chunk.get('rule_title') else None,
            pages=chunk.get('source_pages', []),
            language=chunk.get('language', ''),
            domain=chunk.get('domain', ''),
            score=chunk.get('score', 0.0)
        )
        sources.append(source)
    return sources


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    rag_engine = Depends(get_rag_engine)
):
    """
    Main chat endpoint for legal queries.
    
    Accepts a legal query in any supported language and returns
    a grounded answer with source citations.
    """
    # Validate query
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty"
        )
    
    # Map domain and document type
    domain = map_domain_code(request.domain.value if hasattr(request.domain, 'value') else request.domain)
    doc_type = map_document_type(request.document_type.value if request.document_type and hasattr(request.document_type, 'value') else request.document_type)
    
    # Determine answer language
    answer_language = request.language.value if hasattr(request.language, 'value') else request.language
    
    try:
        start_time = time.time()
        
        # Use the RAG engine to answer
        result = rag_engine.answer(
            query=request.query.strip(),
            answer_language=answer_language if answer_language != "auto" else "auto",
            top_k=request.top_k,
            domain=domain,
            language=None,  # Don't filter by document language unless specified
            document_type=doc_type,
            document=request.document,
            concise=True
        )
        
        total_time = int((time.time() - start_time) * 1000)
        
        # Format sources for response
        sources = format_sources_for_response(result.retrieved_chunks)
        
        # Build response
        return ChatResponse(
            success=True,
            query=request.query,
            detected_language=result.detected_language,
            answer_language=result.answer_language,
            domain=request.domain.value if hasattr(request.domain, 'value') else request.domain,
            answer=result.answer,
            confidence=result.confidence,
            sources=sources,
            latency=LatencyInfo(
                retrieval_ms=result.retrieval_time_ms,
                generation_ms=result.generation_time_ms,
                total_ms=total_time
            )
        )
        
    except Exception as e:
        # Log the error for debugging
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )


@router.get("/chat/suggestions")
async def get_query_suggestions(
    query: str,
    limit: int = 5
):
    """
    Get query suggestions based on partial input.
    This is a placeholder for future autocomplete functionality.
    """
    # For now, return some common legal queries
    suggestions = [
        "What is a patent?",
        "What is a geographical indication?",
        "What is a trade mark?",
        "What is a design?",
        "What is biological diversity?",
        "What is access and benefit sharing?",
        "What is traditional knowledge?",
        "Patent infringement penalties",
        "Trade mark registration process",
        "Geographical indication registration"
    ]
    
    # Filter by query prefix
    filtered = [s for s in suggestions if query.lower() in s.lower()][:limit]
    
    return {"suggestions": filtered}