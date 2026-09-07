#!/usr/bin/env python3
"""
Orchestrator for Phase 6 Multi-Agent Architecture.

Responsibilities:
1. Receive normalized English query
2. Determine relevant domain(s) using agent can_handle scores
3. Select one or more agents (avoid unnecessary calls)
4. Call selected agents
5. Collect and deduplicate evidence
6. Synthesize final answer using Qwen3
7. Return structured response with routing metadata
"""

import time
import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict

from retriever import LegalRetriever
from ollama_utils import OllamaClient, OllamaResponse
from prompts import build_rag_prompt
from agents.base_agent import BaseAgent, AgentResult
from agents.legal_agent import LegalAgent
from agents.tk_agent import TKAgent
from agents.abs_agent import ABSAgent
from agents.ip_agent import IPAgent
from config import get_config, Phase4Config


@dataclass
class RoutingDecision:
    """Records the routing decision for debugging/transparency."""
    query: str
    agent_scores: Dict[str, float]
    selected_agents: List[str]
    primary_agent: Optional[str]
    is_multi_domain: bool
    routing_reason: str


@dataclass
class OrchestratorResult:
    """Final result from orchestrator."""
    success: bool
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    agents_used: List[str]
    routing: RoutingDecision
    retrieval_time_ms: int
    generation_time_ms: int
    synthesis_time_ms: int
    total_time_ms: int
    error: Optional[str] = None


class Orchestrator:
    """Routes queries to appropriate agents and synthesizes final answers."""
    
    # Minimum score for an agent to be considered
    MIN_AGENT_SCORE = 0.25
    
    # Score threshold for single vs multi-agent routing
    DOMINANT_THRESHOLD = 0.4
    
    def __init__(
        self,
        retriever: LegalRetriever,
        ollama: OllamaClient,
        config: Optional[Phase4Config] = None
    ):
        self.retriever = retriever
        self.ollama = ollama
        self.config = config or get_config()
        self.logger = logging.getLogger("orchestrator")
        
        # Initialize all agents
        self.agents: Dict[str, BaseAgent] = {
            'legal': LegalAgent(retriever, ollama, self.config),
            'tk': TKAgent(retriever, ollama, self.config),
            'abs': ABSAgent(retriever, ollama, self.config),
            'ip': IPAgent(retriever, ollama, self.config),
        }
    
    def _score_agents(self, query: str) -> Dict[str, float]:
        """Get relevance scores from all agents."""
        scores = {}
        for name, agent in self.agents.items():
            try:
                scores[name] = agent.can_handle(query)
            except Exception as e:
                self.logger.warning(f"Agent {name} scoring failed: {e}")
                scores[name] = 0.0
        return scores
    
    def _select_agents(self, query: str, scores: Dict[str, float]) -> List[str]:
        """Select agents based on scores - avoid unnecessary calls."""
        # Filter agents above minimum threshold
        eligible = {name: score for name, score in scores.items() 
                   if score >= self.MIN_AGENT_SCORE}
        
        if not eligible:
            # Fallback: use agent with highest score
            best_agent = max(scores, key=scores.get)
            return [best_agent]
        
        # Check for dominant agent (single-domain optimization)
        max_score = max(eligible.values())
        best_agents = [name for name, score in eligible.items() if score == max_score]
        
        # MULTI-DOMAIN DETECTION: If multiple agents have significant scores (>0.25),
        # treat as multi-domain even if one agent dominates
        significant_agents = {name: score for name, score in eligible.items() 
                             if score >= 0.3}
        
        if len(significant_agents) > 1:
            # Multiple agents have meaningful relevance - multi-domain query
            return sorted(significant_agents.keys(), key=lambda x: significant_agents[x], reverse=True)
        
        if max_score >= self.DOMINANT_THRESHOLD and len(best_agents) == 1:
            # Single agent clearly dominates and no other agent is significant
            return best_agents
        
        # Multi-domain: return all eligible agents sorted by score
        return sorted(eligible.keys(), key=lambda x: eligible[x], reverse=True)
    
    def _create_routing_decision(
        self, 
        query: str, 
        scores: Dict[str, float], 
        selected: List[str]
    ) -> RoutingDecision:
        """Create routing decision record."""
        primary = selected[0] if selected else None
        is_multi = len(selected) > 1
        
        reason_parts = []
        for name in selected:
            reason_parts.append(f"{name}({scores[name]:.2f})")
        
        return RoutingDecision(
            query=query,
            agent_scores=scores,
            selected_agents=selected,
            primary_agent=primary,
            is_multi_domain=is_multi,
            routing_reason="; ".join(reason_parts) if reason_parts else "No agent met threshold"
        )
    
    def _deduplicate_evidence(self, all_evidence: List[Dict]) -> List[Dict]:
        """Deduplicate evidence by chunk_id while preserving all metadata."""
        seen = set()
        unique = []
        for ev in all_evidence:
            chunk_id = ev.get('chunk_id')
            if chunk_id and chunk_id not in seen:
                seen.add(chunk_id)
                unique.append(ev)
            elif not chunk_id:
                # No chunk_id - use text hash as fallback
                text_hash = hash(ev.get('text', '')[:200])
                if text_hash not in seen:
                    seen.add(text_hash)
                    unique.append(ev)
        return unique
    
    def _synthesize_answer(
        self,
        query: str,
        agent_results: List[AgentResult],
        routing: RoutingDecision
    ) -> tuple:
        """Synthesize final answer from multiple agent results using Qwen3."""
        if not agent_results:
            return ("I could not find sufficient supporting information in the available legal knowledge base.", 
                    0.0, [], [])
        
        # Collect all unique evidence
        all_evidence = []
        all_sources = []
        agent_names = []
        
        for result in agent_results:
            if result.evidence:
                all_evidence.extend(result.evidence)
            if result.sources:
                all_sources.extend(result.sources)
            agent_names.append(result.agent)
        
        # Deduplicate
        unique_evidence = self._deduplicate_evidence(all_evidence)
        unique_sources = self._deduplicate_evidence(all_sources)
        
        if not unique_evidence:
            return ("I could not find sufficient supporting information in the available legal knowledge base.",
                    0.0, [], [])
        
        # Build context
        context = self._build_synthesis_context(unique_evidence)
        
        # Build synthesis prompt
        agent_list = ", ".join(agent_names)
        system_prompt = f"""You are an Indian legal research assistant. Answer ONLY from the provided context.
Synthesize information from multiple legal domains: {agent_list}
Format your response exactly as:
**Answer**: your answer
**Sources**: your sources
**Confidence**: High/Medium/Low

If context lacks the answer:
**Answer**: I could not find sufficient supporting information in the available legal knowledge base.
**Sources**: None
**Confidence**: Low"""

        user_prompt = f"""CONTEXT:
{context}

QUESTION: {query}"""
        
        # Generate synthesis
        start = time.time()
        response = self.ollama.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=self.config.ollama.temperature,
            top_p=self.config.ollama.top_p,
            max_tokens=self.config.ollama.max_tokens,
            timeout=self.config.ollama.timeout
        )
        synthesis_time = int((time.time() - start) * 1000)
        
        if not response.success:
            # Fallback: use best single agent answer
            best_result = max(agent_results, key=lambda r: r.confidence)
            return (best_result.answer, best_result.confidence, 
                    best_result.sources, best_result.evidence)
        
        # Parse synthesis response for confidence
        answer_text = response.text
        confidence = self._extract_confidence(answer_text, agent_results)
        
        return (answer_text, confidence, unique_sources, unique_evidence)
    
    def _build_synthesis_context(self, evidence: List[Dict]) -> str:
        """Build context for multi-agent synthesis."""
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
    
    def _extract_confidence(self, answer_text: str, agent_results: List[AgentResult]) -> float:
        """Extract confidence from synthesized answer."""
        # Check for explicit confidence marker
        import re
        conf_match = re.search(r'\*\*Confidence\*\*:\s*(High|Medium|Low)', answer_text, re.IGNORECASE)
        if conf_match:
            conf_map = {'high': 0.9, 'medium': 0.6, 'low': 0.3}
            return conf_map.get(conf_match.group(1).lower(), 0.5)
        
        # Fallback: average of agent confidences
        if agent_results:
            return sum(r.confidence for r in agent_results) / len(agent_results)
        return 0.5
    
    def run(
        self, 
        query: str, 
        top_k: int = 5,
        concise: bool = True
    ) -> OrchestratorResult:
        """Main entry point: route query, call agents, synthesize answer."""
        total_start = time.time()
        
        # Step 1: Score all agents
        scores = self._score_agents(query)
        
        # Step 2: Select agents
        selected = self._select_agents(query, scores)
        
        # Step 3: Create routing decision
        routing = self._create_routing_decision(query, scores, selected)
        
        self.logger.info(f"Routing: {routing.routing_reason} | Multi-domain: {routing.is_multi_domain}")
        
        # Step 4: Call selected agents
        agent_results = []
        total_retrieval = 0
        total_generation = 0
        
        for agent_name in selected:
            agent = self.agents[agent_name]
            try:
                result = agent.run(query, top_k=top_k, concise=concise)
                agent_results.append(result)
                total_retrieval += result.retrieval_time_ms
                total_generation += result.generation_time_ms
            except Exception as e:
                self.logger.error(f"Agent {agent_name} failed: {e}")
        
        # Step 5: Filter successful results
        successful_results = [r for r in agent_results if r.status == 'success']
        
        if not successful_results:
            # All agents failed or had insufficient evidence
            # Return best attempt
            best_result = max(agent_results, key=lambda r: r.confidence) if agent_results else None
            if best_result:
                return OrchestratorResult(
                    success=False,
                    answer=best_result.answer or "I could not find sufficient supporting information in the available legal knowledge base.",
                    confidence=best_result.confidence,
                    sources=best_result.sources,
                    evidence=best_result.evidence,
                    agents_used=selected,
                    routing=routing,
                    retrieval_time_ms=total_retrieval,
                    generation_time_ms=total_generation,
                    synthesis_time_ms=0,
                    total_time_ms=int((time.time() - total_start) * 1000),
                    error=f"All agents failed. Best: {best_result.agent} ({best_result.status})"
                )
            else:
                return OrchestratorResult(
                    success=False,
                    answer="I could not find sufficient supporting information in the available legal knowledge base.",
                    confidence=0.0,
                    sources=[],
                    evidence=[],
                    agents_used=selected,
                    routing=routing,
                    retrieval_time_ms=total_retrieval,
                    generation_time_ms=total_generation,
                    synthesis_time_ms=0,
                    total_time_ms=int((time.time() - total_start) * 1000),
                    error="No agents returned evidence"
                )
        
        # Step 6: Synthesize final answer
        if len(successful_results) == 1:
            # Single agent - use its answer directly
            result = successful_results[0]
            synthesis_time = 0
            final_answer = result.answer
            final_confidence = result.confidence
            final_sources = result.sources
            final_evidence = result.evidence
        else:
            # Multi-agent - synthesize
            final_answer, final_confidence, final_sources, final_evidence = self._synthesize_answer(
                query, successful_results, routing
            )
            synthesis_time = 0  # Will be updated below
        
        total_time = int((time.time() - total_start) * 1000)
        
        return OrchestratorResult(
            success=True,
            answer=final_answer,
            confidence=final_confidence,
            sources=final_sources,
            evidence=final_evidence,
            agents_used=selected,
            routing=routing,
            retrieval_time_ms=total_retrieval,
            generation_time_ms=total_generation,
            synthesis_time_ms=synthesis_time,
            total_time_ms=total_time
        )
    
    def run_with_debug(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Run with detailed debug information."""
        result = self.run(query, top_k)
        
        debug_info = {
            'query': query,
            'routing': asdict(result.routing),
            'agents_used': result.agents_used,
            'agent_results': [],
            'final_answer': result.answer,
            'final_confidence': result.confidence,
            'sources_count': len(result.sources),
            'evidence_count': len(result.evidence),
            'latency': {
                'retrieval_ms': result.retrieval_time_ms,
                'generation_ms': result.generation_time_ms,
                'synthesis_ms': result.synthesis_time_ms,
                'total_ms': result.total_time_ms
            }
        }
        
        # Add per-agent debug info
        scores = self._score_agents(query)
        for name, agent in self.agents.items():
            debug_info['agent_results'].append({
                'agent': name,
                'can_handle_score': scores[name],
                'selected': name in result.agents_used,
            })
        
        return debug_info


if __name__ == '__main__':
    from rag_engine import create_rag_engine
    engine = create_rag_engine()
    
    orchestrator = Orchestrator(
        retriever=engine.retriever,
        ollama=engine.ollama,
        config=engine.config
    )
    
    # Test queries
    test_queries = [
        "What is a patent?",
        "What is traditional knowledge?",
        "What is access and benefit sharing?",
        "What does Section 11 of the Patents Act deal with?",
        "Can traditional knowledge be protected through patents?",
        "What obligations apply when accessing biological resources with traditional knowledge?",
    ]
    
    for q in test_queries:
        print(f"\n{'='*60}")
        print(f"QUERY: {q}")
        result = orchestrator.run(q, top_k=3)
        print(f"Agents used: {result.agents_used}")
        print(f"Routing: {result.routing.routing_reason}")
        print(f"Status: {'Success' if result.success else 'Failed'}")
        print(f"Confidence: {result.confidence}")
        print(f"Sources: {len(result.sources)}")
        print(f"Latency: ret={result.retrieval_time_ms}ms gen={result.generation_time_ms}ms syn={result.synthesis_time_ms}ms total={result.total_time_ms}ms")
        if result.answer:
            print(f"Answer: {result.answer[:300]}...")