#!/usr/bin/env python3
"""
Base Agent class for Phase 6 multi-agent architecture.

All specialized agents inherit from this base class.
Agents use the existing shared RAG infrastructure.
"""

import time
import logging
import re
import string
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

from retriever import LegalRetriever
from ollama_utils import OllamaClient, OllamaResponse
from prompts import build_rag_prompt
from config import get_config, Phase4Config


def normalize_words(text: str) -> set:
    """Normalize text into a set of words, stripping punctuation."""
    # Replace punctuation with spaces, then split
    translator = str.maketrans(string.punctuation, ' ' * len(string.punctuation))
    normalized = text.translate(translator)
    return set(normalized.lower().split())


@dataclass
class AgentResult:
    """Structured result from an agent."""
    agent: str                    # Agent name: 'legal', 'tk', 'abs', 'ip'
    status: str                   # 'success', 'insufficient_evidence', 'error'
    answer: str                   # Generated answer (empty if insufficient evidence)
    confidence: float             # 0.0 - 1.0
    sources: List[Dict[str, Any]] # Source citations with metadata
    evidence: List[Dict[str, Any]] # Raw retrieved chunks
    domain: str                   # Agent's domain
    retrieval_time_ms: int
    generation_time_ms: int
    total_time_ms: int
    error: Optional[str] = None
    routing_reason: Optional[str] = None


class BaseAgent(ABC):
    """Base class for all specialized agents.
    
    Agents are reasoning/routing modules, NOT independent knowledge bases.
    They share the existing retriever, ChromaDB, and Qwen3.
    """
    
    def __init__(
        self,
        name: str,
        domain: str,
        retriever: LegalRetriever,
        ollama: OllamaClient,
        config: Optional[Phase4Config] = None
    ):
        self.name = name
        self.domain = domain
        self.retriever = retriever
        self.ollama = ollama
        self.config = config or get_config()
        self.logger = logging.getLogger(f"agent.{name}")
    
    @abstractmethod
    def can_handle(self, query: str) -> float:
        """Return confidence score (0.0-1.0) for handling this query.
        
        Higher score means this agent is more relevant.
        Used by orchestrator for routing decisions.
        """
        pass
    
    @abstractmethod
    def get_retrieval_filters(self, query: str) -> Dict[str, Any]:
        """Return ChromaDB filter dict for this agent's domain.
        
        Used to scope retrieval to relevant documents.
        """
        pass
    
    @abstractmethod
    def get_system_prompt_suffix(self) -> str:
        """Return agent-specific prompt suffix for Qwen3."""
        pass
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve evidence using shared retriever with agent-specific filters."""
        start = time.time()
        filters = self.get_retrieval_filters(query)
        
        result = self.retriever.search(
            query=query,
            top_k=top_k,
            domain=filters.get('domain'),
            language=filters.get('language'),
            document_type=filters.get('document_type'),
            document=filters.get('document')
        )
        
        retrieval_time = int((time.time() - start) * 1000)
        
        # Convert to dict format
        evidence = []
        for r in result:
            evidence.append({
                'rank': r.rank,
                'chunk_id': r.chunk_id,
                'score': r.score,
                'document': r.document,
                'document_type': r.document_type,
                'document_year': r.document_year,
                'language': r.language,
                'domain': r.domain,
                'section_number': r.section_number,
                'section_title': r.section_title,
                'rule_number': r.rule_number,
                'rule_title': r.rule_title,
                'text': r.text,
                'source_pages': r.source_pages,
                'keywords': r.keywords,
                'cross_references': r.cross_references,
                'retrieval_time_ms': retrieval_time
            })
        
        self.logger.info(f"Retrieved {len(evidence)} chunks in {retrieval_time}ms")
        return evidence
    
    def generate_answer(
        self, 
        query: str, 
        context: str,
        concise: bool = True
    ) -> OllamaResponse:
        """Generate answer using shared Qwen3 with agent-specific prompt."""
        # Build prompt with agent-specific suffix
        base_prompt = build_rag_prompt(query, context, 'en', concise)
        
        # Inject agent-specific instructions
        agent_instruction = self.get_system_prompt_suffix()
        # Replace the system prompt section with agent-enhanced version
        if "<|system|>" in base_prompt:
            parts = base_prompt.split("<|system|>", 1)
            if len(parts) == 2:
                system_part = parts[1].split("<|user|>", 1)
                if len(system_part) == 2:
                    enhanced_system = system_part[0] + "\n" + agent_instruction
                    base_prompt = f"<|system|>{enhanced_system}<|user|>{system_part[1]}"
        
        response = self.ollama.generate(
            prompt=base_prompt,
            temperature=self.config.ollama.temperature,
            top_p=self.config.ollama.top_p,
            max_tokens=self.config.ollama.max_tokens,
            timeout=self.config.ollama.timeout
        )
        
        return response
    
    def assess_evidence_relevance(self, evidence: List[Dict], query: str) -> float:
        """Assess if retrieved evidence is relevant to the query.
        
        Uses retrieval scores and keyword overlap as heuristics.
        """
        if not evidence:
            return 0.0
        
        # Use top retrieval score as primary indicator
        top_score = evidence[0].get('score', 0.0)
        
        # Check keyword overlap between query and top evidence
        query_words = set(query.lower().split())
        top_text = evidence[0].get('text', '').lower()
        evidence_words = set(top_text.split())
        
        overlap = len(query_words & evidence_words) / max(len(query_words), 1)
        
        # Combined relevance score
        relevance = (top_score * 0.7) + (overlap * 0.3)
        return min(1.0, relevance)
    
    def format_sources(self, evidence: List[Dict]) -> List[Dict[str, Any]]:
        """Format evidence as source citations preserving all metadata."""
        sources = []
        for ev in evidence:
            source = {
                'document': ev.get('document', ''),
                'document_type': ev.get('document_type', ''),
                'document_year': ev.get('document_year'),
                'section': ev.get('section_number') if ev.get('section_number') else None,
                'section_title': ev.get('section_title') if ev.get('section_title') else None,
                'rule': ev.get('rule_number') if ev.get('rule_number') else None,
                'rule_title': ev.get('rule_title') if ev.get('rule_title') else None,
                'pages': ev.get('source_pages', []),
                'language': ev.get('language', ''),
                'domain': ev.get('domain', ''),
                'score': ev.get('score', 0.0)
            }
            sources.append(source)
        return sources
    
    def run(
        self, 
        query: str, 
        top_k: int = 5,
        concise: bool = True
    ) -> AgentResult:
        """Main entry point: process query through retrieve -> assess -> generate."""
        total_start = time.time()
        
        # Step 1: Retrieve evidence
        evidence = self.retrieve(query, top_k)
        retrieval_time = sum(e.get('retrieval_time_ms', 0) for e in evidence) if evidence else 0
        
        if not evidence:
            return AgentResult(
                agent=self.name,
                status='insufficient_evidence',
                answer='',
                confidence=0.0,
                sources=[],
                evidence=[],
                domain=self.domain,
                retrieval_time_ms=retrieval_time,
                generation_time_ms=0,
                total_time_ms=int((time.time() - total_start) * 1000),
                error='No evidence retrieved'
            )
        
        # Step 2: Assess evidence relevance
        relevance = self.assess_evidence_relevance(evidence, query)
        
        if relevance < self.config.thresholds.min_score_for_generation:
            return AgentResult(
                agent=self.name,
                status='insufficient_evidence',
                answer='',
                confidence=relevance,
                sources=self.format_sources(evidence),
                evidence=evidence,
                domain=self.domain,
                retrieval_time_ms=retrieval_time,
                generation_time_ms=0,
                total_time_ms=int((time.time() - total_start) * 1000),
                error=f'Evidence relevance too low: {relevance:.2f}'
            )
        
        # Step 3: Build context from evidence
        context = self._build_context(evidence)
        
        # Step 4: Generate answer
        gen_start = time.time()
        ollama_response = self.generate_answer(query, context, concise)
        generation_time = int((time.time() - gen_start) * 1000)
        
        if not ollama_response.success:
            return AgentResult(
                agent=self.name,
                status='error',
                answer='',
                confidence=0.0,
                sources=self.format_sources(evidence),
                evidence=evidence,
                domain=self.domain,
                retrieval_time_ms=retrieval_time,
                generation_time_ms=generation_time,
                total_time_ms=int((time.time() - total_start) * 1000),
                error=ollama_response.error
            )
        
        # Step 5: Determine confidence
        confidence = self._calculate_confidence(relevance, ollama_response)
        
        total_time = int((time.time() - total_start) * 1000)
        
        return AgentResult(
            agent=self.name,
            status='success',
            answer=ollama_response.text,
            confidence=confidence,
            sources=self.format_sources(evidence),
            evidence=evidence,
            domain=self.domain,
            retrieval_time_ms=retrieval_time,
            generation_time_ms=generation_time,
            total_time_ms=total_time
        )
    
    def _build_context(self, evidence: List[Dict]) -> str:
        """Build structured context string from evidence."""
        if not evidence:
            return "No context available."
        
        context_parts = []
        for i, ev in enumerate(evidence, 1):
            parts = [f"SOURCE {i}"]
            doc_info = f"Document: {ev.get('document', '')} ({ev.get('document_year', '')})"
            parts.append(doc_info)
            
            if ev.get('section_number'):
                parts.append(f"Section: {ev.get('section_number')} - {ev.get('section_title', '')}")
            if ev.get('rule_number'):
                parts.append(f"Rule: {ev.get('rule_number')} - {ev.get('rule_title', '')}")
            
            if ev.get('source_pages'):
                parts.append(f"Pages: {', '.join(map(str, ev.get('source_pages', [])))}")
            
            parts.append(f"Text: {ev.get('text', '')}")
            context_parts.append("\n".join(parts))
        
        return "\n\n".join(context_parts)
    
    def _calculate_confidence(self, relevance: float, ollama_response: OllamaResponse) -> float:
        """Calculate overall confidence from relevance and generation success."""
        # Base confidence from evidence relevance
        confidence = relevance
        
        # Adjust based on response quality indicators
        if ollama_response.success and ollama_response.text:
            text = ollama_response.text.lower()
            # Boost if answer contains legal citations
            if any(term in text for term in ['section', 'rule', 'act', 'article']):
                confidence = min(1.0, confidence + 0.1)
            # Reduce if answer is very short (likely incomplete)
            if len(ollama_response.text) < 50:
                confidence = max(0.0, confidence - 0.1)
        
        return round(confidence, 2)