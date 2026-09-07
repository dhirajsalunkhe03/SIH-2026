#!/usr/bin/env python3
"""
Main Legal RAG Engine.
Orchestrates retrieval, context building, and Qwen3 generation.
With Phase 5B: Multilingual input/output translation layer.
With Phase 6: Multi-agent architecture (Legal, TK, ABS, IP agents + Orchestrator).
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from retriever import LegalRetriever, RetrievalResult
from context_builder import ContextBuilder, format_sources_for_citation
from ollama_utils import OllamaClient, OllamaResponse
from prompts import build_rag_prompt, get_language_instruction
from language_utils import detect_language, LanguageInfo
from translation_service import (
    get_translation_service, 
    translate_to_english, 
    translate_from_english,
    TranslationResult,
    get_language_config
)
from agents.orchestrator import Orchestrator, OrchestratorResult, RoutingDecision
from config import get_config, Phase4Config


@dataclass
class RAGAnswer:
    """Complete answer from the RAG system."""
    query: str
    detected_language: Dict[str, Any]
    answer_language: str
    answer: str
    sources: List[Dict[str, Any]]
    retrieved_chunks: List[Dict[str, Any]]
    confidence: str
    confidence_reason: str
    retrieval_time_ms: int
    generation_time_ms: int
    translation_to_english_ms: int
    translation_to_target_ms: int
    total_time_ms: int
    retrieval_confidence: str  # high/medium/low/none
    error: Optional[str] = None
    # Phase 6: Agent routing info
    agents_used: Optional[List[str]] = None
    routing_domain: Optional[str] = None
    routing_reason: Optional[str] = None
    is_multi_domain: bool = False


class LegalRAG:
    """Main Legal RAG Engine."""
    
    def __init__(self, config: Optional[Phase4Config] = None):
        self.config = config or get_config()
        self.retriever = None
        self.context_builder = None
        self.ollama = None
        self.translation_service = None
        self.logger = None
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging for the RAG engine."""
        log_dir = self.config.logging.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("LegalRAG")
        self.logger.setLevel(getattr(logging, self.config.logging.log_level))
        
        # File handler
        fh = logging.FileHandler(log_dir / "rag_engine.log", encoding='utf-8')
        fh.setLevel(getattr(logging, self.config.logging.log_level))
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(getattr(logging, self.config.logging.log_level))
        
        formatter = logging.Formatter(self.config.logging.log_format)
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)
    
    def load(self):
        """Load all components."""
        self.logger.info("Loading LegalRAG components...")
        
        # Load retriever
        self.retriever = LegalRetriever(
            vector_db_path=self.config.retriever.vector_db_path,
            model_name=self.config.retriever.model_name,
            collection_name=self.config.retriever.collection_name,
            device=self.config.retriever.device,
            use_cpu=self.config.retriever.use_cpu
        )
        self.retriever.load()
        
        # Initialize context builder
        self.context_builder = ContextBuilder(
            max_context_chars=self.config.context.max_context_chars
        )
        
        # Initialize Ollama client
        self.ollama = OllamaClient(
            model=self.config.ollama.model,
            host=self.config.ollama.host,
            temperature=self.config.ollama.temperature,
            top_p=self.config.ollama.top_p,
            max_tokens=self.config.ollama.max_tokens,
            timeout=self.config.ollama.timeout
        )
        
        # Initialize translation service if enabled
        if self.config.translation.enabled:
            try:
                self.translation_service = get_translation_service({
                    'model_name': self.config.translation.model_name,
                })
                self.logger.info("Translation service initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize translation service: {e}")
                self.translation_service = None
        
        # Verify Ollama
        if not self.ollama.check_availability():
            self.logger.warning(f"Ollama not available or model {self.config.ollama.model} not found")
        else:
            self.logger.info(f"Ollama ready with model {self.config.ollama.model}")
        
        # Initialize orchestrator (Phase 6)
        try:
            self.orchestrator = Orchestrator(
                retriever=self.retriever,
                ollama=self.ollama,
                config=self.config
            )
            self.logger.info("Orchestrator initialized with agents: legal, tk, abs, ip")
        except Exception as e:
            self.logger.warning(f"Failed to initialize orchestrator: {e}")
            self.orchestrator = None
        
        self.logger.info("LegalRAG loaded successfully")
    
    def detect_language(self, query: str) -> LanguageInfo:
        """Detect query language."""
        return detect_language(query)
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        domain: Optional[str] = None,
        language: Optional[str] = None,
        document_type: Optional[str] = None,
        document: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve relevant legal chunks."""
        start = time.time()
        
        result = self.retriever.search_multilingual(
            query=query,
            top_k=top_k,
            domain=domain,
            language=language,
            document_type=document_type,
            document=document
        )
        
        retrieval_time = int((time.time() - start) * 1000)
        result['retrieval_time_ms'] = retrieval_time
        
        self.logger.info(f"Retrieved {len(result['results'])} chunks in {retrieval_time}ms for query: {query[:50]}")
        
        return result
    
    def build_context(self, retrieval_result: Dict[str, Any]) -> str:
        """Build structured context from retrieval results."""
        return self.context_builder.build_context(retrieval_result.get('results', []))
    
    def _assess_retrieval_confidence(self, results: List[Dict]) -> tuple:
        """Assess retrieval confidence based on scores."""
        thresholds = self.config.thresholds
        
        if not results:
            return "none", "No results retrieved"
        
        top_score = results[0].get('score', 0)
        
        if top_score >= thresholds.high_confidence:
            return "high", f"Top score {top_score:.3f} >= {thresholds.high_confidence}"
        elif top_score >= thresholds.medium_confidence:
            return "medium", f"Top score {top_score:.3f} >= {thresholds.medium_confidence}"
        elif top_score >= thresholds.low_confidence:
            return "low", f"Top score {top_score:.3f} >= {thresholds.low_confidence}"
        else:
            return "none", f"Top score {top_score:.3f} below minimum threshold {thresholds.low_confidence}"
    
    def generate_answer(
        self,
        query: str,
        context: str,
        answer_language: str = 'auto',
        concise: bool = True
    ) -> OllamaResponse:
        """Generate answer using Qwen3."""
        # Build prompt
        prompt = build_rag_prompt(
            query=query,
            context=context,
            language=answer_language,
            concise=concise
        )
        
        # Generate
        response = self.ollama.generate(
            prompt=prompt,
            temperature=self.config.ollama.temperature,
            top_p=self.config.ollama.top_p,
            max_tokens=self.config.ollama.max_tokens,
            timeout=self.config.ollama.timeout
        )
        
        return response
    
    def format_sources(self, retrieved_results: List[Dict]) -> str:
        """Format sources for citation."""
        sources = self.context_builder.build_source_list(retrieved_results)
        return format_sources_for_citation(sources)
    
    def answer(
        self,
        query: str,
        answer_language: str = 'auto',
        top_k: int = 5,
        domain: Optional[str] = None,
        language: Optional[str] = None,
        document_type: Optional[str] = None,
        document: Optional[str] = None,
        concise: bool = True
    ) -> RAGAnswer:
        """
        Main entry point: answer a legal query with multilingual support.
        Uses Phase 6 orchestrator for multi-agent routing.
        """
        total_start = time.time()
        self.logger.info(f"Processing query: {query[:80]}...")
        
        translation_to_english_ms = 0
        translation_to_target_ms = 0
        
        # Step 1: Detect query language
        lang_info = self.detect_language(query)
        detected_lang = lang_info.code
        
        # Step 2: Determine target answer language
        if answer_language == 'auto':
            target_lang = detected_lang if detected_lang != 'unknown' else 'en'
        else:
            target_lang = answer_language
        
        # Step 3: Translate query to English if needed
        english_query = query
        if target_lang != 'en' and self.translation_service and self.config.translation.enabled:
            trans_start = time.time()
            trans_result = self.translation_service.translate_to_english(query, target_lang)
            translation_to_english_ms = int((time.time() - trans_start) * 1000)
            
            if trans_result.success:
                english_query = trans_result.text
                self.logger.info(f"Translated query to English: {english_query[:80]}...")
            else:
                self.logger.warning(f"Query translation failed: {trans_result.error}")
        
        # Step 4: Use orchestrator if available (Phase 6)
        if self.orchestrator:
            self.logger.info("Using orchestrator for multi-agent routing")
            orchestrator_result: OrchestratorResult = self.orchestrator.run(
                query=english_query,
                top_k=top_k,
                concise=concise
            )
            
            # Step 5: Translate answer to target language if needed
            final_answer = orchestrator_result.answer
            if target_lang != 'en' and self.translation_service and self.config.translation.enabled:
                trans_start = time.time()
                trans_result = self.translation_service.translate_from_english(orchestrator_result.answer, target_lang)
                translation_to_target_ms = int((time.time() - trans_start) * 1000)
                
                if trans_result.success:
                    final_answer = trans_result.text
                    self.logger.info(f"Translated answer to {target_lang}")
                else:
                    self.logger.warning(f"Answer translation failed: {trans_result.error}")
            
            total_time = int((time.time() - total_start) * 1000)
            
            self.logger.info(
                f"Query answered in {total_time}ms "
                f"(retrieval: {orchestrator_result.retrieval_time_ms}ms, "
                f"generation: {orchestrator_result.generation_time_ms}ms, "
                f"synthesis: {orchestrator_result.synthesis_time_ms}ms, "
                f"trans_to_en: {translation_to_english_ms}ms, "
                f"trans_to_target: {translation_to_target_ms}ms) "
                f"[agents: {orchestrator_result.agents_used}]"
            )
            
            return RAGAnswer(
                query=query,
                detected_language=asdict(lang_info),
                answer_language=target_lang,
                answer=final_answer,
                sources=orchestrator_result.sources,
                retrieved_chunks=orchestrator_result.evidence,
                confidence=str(orchestrator_result.confidence) if isinstance(orchestrator_result.confidence, float) else orchestrator_result.confidence,
                confidence_reason=f"Routed to: {', '.join(orchestrator_result.agents_used)} ({orchestrator_result.routing.routing_reason})",
                retrieval_time_ms=orchestrator_result.retrieval_time_ms,
                generation_time_ms=orchestrator_result.generation_time_ms,
                translation_to_english_ms=translation_to_english_ms,
                translation_to_target_ms=translation_to_target_ms,
                total_time_ms=total_time,
                retrieval_confidence="high" if orchestrator_result.confidence > 0.7 else "medium" if orchestrator_result.confidence > 0.4 else "low",
                error=orchestrator_result.error,
                agents_used=orchestrator_result.agents_used,
                routing_domain=orchestrator_result.routing.primary_agent,
                routing_reason=orchestrator_result.routing.routing_reason,
                is_multi_domain=orchestrator_result.routing.is_multi_domain
            )
        
        # Fallback: Original single-agent RAG pipeline (Phase 5)
        self.logger.info("Using legacy single-agent RAG pipeline")
        
        # Retrieve using English query
        retrieval_result = self.retrieve(
            query=english_query,
            top_k=top_k,
            domain=domain,
            language=language,
            document_type=document_type,
            document=document
        )
        
        retrieval_time = retrieval_result.get('retrieval_time_ms', 0)
        retrieved_chunks = retrieval_result.get('results', [])
        
        # Assess retrieval confidence
        retrieval_confidence, confidence_reason = self._assess_retrieval_confidence(retrieved_chunks)
        
        # Handle low/no confidence
        if retrieval_confidence == 'none':
            self.logger.warning(f"Low retrieval confidence for query: {query[:50]}")
            total_time = int((time.time() - total_start) * 1000)
            return RAGAnswer(
                query=query,
                detected_language=asdict(lang_info),
                answer_language=target_lang,
                answer="I could not find sufficient supporting information in the available legal knowledge base.",
                sources=[],
                retrieved_chunks=retrieved_chunks,
                confidence="low",
                confidence_reason=confidence_reason,
                retrieval_time_ms=retrieval_time,
                generation_time_ms=0,
                translation_to_english_ms=translation_to_english_ms,
                translation_to_target_ms=translation_to_target_ms,
                total_time_ms=total_time,
                retrieval_confidence=retrieval_confidence,
                error="No relevant context found"
            )
        
        # Build context
        context = self.build_context(retrieval_result)
        
        # Generate answer in English
        gen_start = time.time()
        ollama_response = self.generate_answer(
            query=english_query,
            context=context,
            answer_language='en',
            concise=concise
        )
        generation_time = int((time.time() - gen_start) * 1000)
        
        if not ollama_response.success:
            self.logger.error(f"Generation failed: {ollama_response.error}")
            total_time = int((time.time() - total_start) * 1000)
            return RAGAnswer(
                query=query,
                detected_language=asdict(lang_info),
                answer_language=target_lang,
                answer="I could not find sufficient supporting information in the available legal knowledge base.",
                sources=[],
                retrieved_chunks=retrieved_chunks,
                confidence="low",
                confidence_reason="Generation failed",
                retrieval_time_ms=retrieval_time,
                generation_time_ms=generation_time,
                translation_to_english_ms=translation_to_english_ms,
                translation_to_target_ms=translation_to_target_ms,
                total_time_ms=int((time.time() - total_start) * 1000),
                retrieval_confidence=retrieval_confidence,
                error=ollama_response.error
            )
        
        english_answer = ollama_response.text
        
        # Translate answer to target language if needed
        final_answer = english_answer
        if target_lang != 'en' and self.translation_service and self.config.translation.enabled:
            trans_start = time.time()
            trans_result = self.translation_service.translate_from_english(english_answer, target_lang)
            translation_to_target_ms = int((time.time() - trans_start) * 1000)
            
            if trans_result.success:
                final_answer = trans_result.text
                self.logger.info(f"Translated answer to {target_lang}")
            else:
                self.logger.warning(f"Answer translation failed: {trans_result.error}")
        
        # Format sources
        sources_text = self.format_sources(retrieved_chunks)
        sources_list = self.context_builder.build_source_list(retrieved_chunks)
        
        # Combine answer with sources
        final_answer_with_sources = f"{final_answer}\n\n{sources_text}"
        
        # Determine overall confidence
        if retrieval_confidence == 'high' and ollama_response.success:
            overall_confidence = "High"
        elif retrieval_confidence == 'medium':
            overall_confidence = "Medium"
        else:
            overall_confidence = "Low"
        
        total_time = int((time.time() - total_start) * 1000)
        
        self.logger.info(
            f"Query answered in {total_time}ms "
            f"(retrieval: {retrieval_time}ms, "
            f"generation: {generation_time}ms, "
            f"trans_to_en: {translation_to_english_ms}ms, "
            f"trans_to_target: {translation_to_target_ms}ms)"
        )
        
        return RAGAnswer(
            query=query,
            detected_language=asdict(lang_info),
            answer_language=target_lang,
            answer=final_answer_with_sources,
            sources=sources_list,
            retrieved_chunks=retrieved_chunks,
            confidence=overall_confidence,
            confidence_reason=confidence_reason,
            retrieval_time_ms=retrieval_time,
            generation_time_ms=generation_time,
            translation_to_english_ms=translation_to_english_ms,
            translation_to_target_ms=translation_to_target_ms,
            total_time_ms=total_time,
            retrieval_confidence=retrieval_confidence
        )
    
    def answer_simple(self, query: str, answer_language: str = 'auto') -> str:
        """Simple interface returning just the answer string."""
        result = self.answer(query, answer_language=answer_language)
        return result.answer


def create_rag_engine(config: Optional[Phase4Config] = None) -> LegalRAG:
    """Factory function to create and load RAG engine."""
    engine = LegalRAG(config)
    engine.load()
    return engine


if __name__ == '__main__':
    # Quick test
    engine = create_rag_engine()
    
    test_queries = [
        "What is a patent?",
        "पेटेंट क्या है?",
        "पेटंट म्हणजे काय?",
    ]
    
    for q in test_queries:
        print(f"\n{'='*60}")
        print(f"QUERY: {q}")
        result = engine.answer(q)
        print(f"Language: {result.answer_language} (detected: {result.detected_language['code']})")
        print(f"Confidence: {result.confidence} ({result.confidence_reason})")
        print(f"Retrieval: {result.retrieval_time_ms}ms, Generation: {result.generation_time_ms}ms")
        print(f"Answer:\n{result.answer[:500]}...")