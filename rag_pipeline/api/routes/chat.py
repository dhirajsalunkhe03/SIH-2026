#!/usr/bin/env python3
"""
Chat routes for the Legal RAG API.
Production-hardened with better error handling and monitoring.
"""

import time
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List

from api.schemas import (
    ChatRequest, ChatResponse, SourceCitation, LatencyInfo, DetectedLanguage,
    LanguageCode, DomainCode, DocumentTypeCode
)
from api.dependencies import get_rag_engine, handle_rag_error
from rag_engine import LegalRAG
from agents.orchestrator import OrchestratorResult
from config import get_config

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


def format_sources_for_response(evidence: List[dict]) -> List[SourceCitation]:
    """Format evidence as source citations for API response."""
    sources = []
    for chunk in evidence:
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
    rag_engine: LegalRAG = Depends(get_rag_engine)
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
    domain_value = request.domain.value if hasattr(request.domain, 'value') else request.domain
    doc_type_value = request.document_type.value if request.document_type and hasattr(request.document_type, 'value') else request.document_type
    language_value = request.language.value if hasattr(request.language, 'value') else request.language
    
    domain = map_domain_code(domain_value)
    doc_type = map_document_type(doc_type_value)
    answer_language = language_value
    
    start_time = time.time()
    
    try:
        # Use the orchestrator if available (Phase 6), fallback to direct RAG
        if rag_engine.orchestrator:
            # Step 1: Detect and translate query to English (reuse existing logic)
            from translation_service import get_translation_service
            from language_utils import detect_language
            
            query = request.query.strip()
            lang_info = detect_language(query)
            detected_lang = lang_info.code
            
            if answer_language == 'auto':
                target_lang = detected_lang if detected_lang != 'unknown' else 'en'
            else:
                target_lang = answer_language
            
            # Translate query to English if needed
            english_query = query
            translation_to_english_ms = 0
            if target_lang != 'en' and rag_engine.translation_service and rag_engine.config.translation.enabled:
                trans_start = time.time()
                trans_result = rag_engine.translation_service.translate_to_english(query, target_lang)
                translation_to_english_ms = int((time.time() - trans_start) * 1000)
                
                if trans_result.success:
                    english_query = trans_result.text
                else:
                    pass  # Continue with original query
            
            # Step 2: Run orchestrator on English query
            orchestrator_result: OrchestratorResult = rag_engine.orchestrator.run(
                query=english_query,
                top_k=request.top_k,
                concise=True
            )
            
            # Step 3: Translate answer to target language if needed
            final_answer = orchestrator_result.answer
            translation_to_target_ms = 0
            if target_lang != 'en' and rag_engine.translation_service and rag_engine.config.translation.enabled:
                trans_start = time.time()
                trans_result = rag_engine.translation_service.translate_from_english(orchestrator_result.answer, target_lang)
                translation_to_target_ms = int((time.time() - trans_start) * 1000)
                
                if trans_result.success:
                    final_answer = trans_result.text
                else:
                    pass  # Fall back to English answer
            
            total_time = int((time.time() - start_time) * 1000)
            
            # Format sources for response
            sources = format_sources_for_response(orchestrator_result.sources)
            
            # Build routing info for response
            routing_info = {
                "agents_used": orchestrator_result.agents_used,
                "routing_domain": orchestrator_result.routing.primary_agent,
                "routing_reason": orchestrator_result.routing.routing_reason,
                "is_multi_domain": orchestrator_result.routing.is_multi_domain
            }
            
            # Build response
            return ChatResponse(
                success=True,
                query=request.query,
                detected_language=DetectedLanguage(
                    code=lang_info.code,
                    name=lang_info.name,
                    confidence=lang_info.confidence
                ),
                answer_language=target_lang,
                domain=domain_value,
                answer=final_answer,
                confidence=str(orchestrator_result.confidence) if orchestrator_result.confidence <= 1.0 else orchestrator_result.confidence,
                sources=sources,
                latency=LatencyInfo(
                    retrieval_ms=orchestrator_result.retrieval_time_ms,
                    generation_ms=orchestrator_result.generation_time_ms,
                    translation_to_english_ms=translation_to_english_ms,
                    translation_to_target_ms=translation_to_target_ms,
                    total_ms=total_time
                ),
                error=None,
                agents_used=orchestrator_result.agents_used,
                routing_domain=orchestrator_result.routing.primary_agent,
                routing_reason=orchestrator_result.routing.routing_reason,
                is_multi_domain=orchestrator_result.routing.is_multi_domain
            )
        else:
            # Fallback to original RAG engine
            result = rag_engine.answer(
                query=request.query.strip(),
                answer_language=answer_language if answer_language != "auto" else "auto",
                top_k=request.top_k,
                domain=domain,
                language=None,
                document_type=doc_type,
                document=request.document,
                concise=True
            )
            
            total_time = int((time.time() - start_time) * 1000)
            
            sources = format_sources_for_response(result.retrieved_chunks)
            
            return ChatResponse(
                success=True,
                query=request.query,
                detected_language=result.detected_language,
                answer_language=result.answer_language,
                domain=domain_value,
                answer=result.answer,
                confidence=result.confidence,
                sources=sources,
                latency=LatencyInfo(
                    retrieval_ms=result.retrieval_time_ms,
                    generation_ms=result.generation_time_ms,
                    translation_to_english_ms=result.translation_to_english_ms,
                    translation_to_target_ms=result.translation_to_target_ms,
                    total_ms=total_time
                ),
                agents_used=result.agents_used if hasattr(result, 'agents_used') else [],
                routing_domain=result.routing_domain if hasattr(result, 'routing_domain') else None,
                routing_reason=result.routing_reason if hasattr(result, 'routing_reason') else None,
                is_multi_domain=result.is_multi_domain if hasattr(result, 'is_multi_domain') else False
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Convert to HTTP exception with structured error
        import traceback
        traceback.print_exc()
        raise await handle_rag_error(e)


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