#!/usr/bin/env python3
"""
Legal Agent - Handles queries about Acts, Sections, Rules, legal definitions,
legal procedures, permissions, obligations, prohibitions, authorities, penalties.
"""

from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent, AgentResult, normalize_words
from retriever import LegalRetriever
from ollama_utils import OllamaClient
from config import Phase4Config


# Keywords that indicate legal domain queries
LEGAL_KEYWORDS = {
    # Core legal terms
    'section', 'sections', 'rule', 'rules', 'act', 'acts', 'article', 'articles', 'clause', 'clauses', 'provision', 'provisions', 'statute', 'statutes',
    'regulation', 'regulations', 'notification', 'notifications', 'order', 'orders', 'amendment', 'amendments', 'schedule', 'schedules',
    
    # Legal actions
    'penalty', 'penalties', 'punishment', 'fine', 'fines', 'imprisonment', 'offence', 'offences', 'violation', 'violations',
    'compliance', 'obligation', 'obligations', 'requirement', 'requirements', 'mandatory', 'prohibited',
    'permission', 'permissions', 'authorisation', 'authorisations', 'approval', 'approvals', 'licence', 'licences', 'license', 'licenses',
    'registration', 'filing', 'application', 'applications', 'procedure', 'procedures', 'process', 'processes',
    'apply', 'applies', 'applying', 'applicable', 'applicability',
    'enforce', 'enforcement', 'enforced', 'enforcing',
    'liable', 'liability', 'responsible', 'responsibility',
    
    # Legal entities
    'authority', 'authorities', 'tribunal', 'tribunals', 'court', 'courts', 'board', 'boards', 'committee', 'committees', 'registry', 'registries',
    'controller', 'controllers', 'registrar', 'registrars', 'examiner', 'examiners', 'government', 'central government',
    'state government', 'minister', 'ministers', 'secretary', 'secretaries', 'director', 'directors',
    
    # Legal concepts
    'jurisdiction', 'appeal', 'appeals', 'revision', 'review', 'stay', 'injunction',
    'limitation', 'prescription', 'retrospective', 'prospective',
    'definition', 'definitions', 'interpretation', 'construction', 'meaning',
    'rights', 'right', 'duty', 'duties', 'power', 'powers', 'function', 'functions',
    
    # Specific acts referenced
    'patents act', 'trade marks act', 'designs act', 'geographical indications',
    'biological diversity act', 'copyright act', 'plant varieties',
}


class LegalAgent(BaseAgent):
    """Agent for general legal queries about Acts, Sections, Rules, procedures."""
    
    def __init__(
        self,
        retriever: LegalRetriever,
        ollama: OllamaClient,
        config: Optional[Phase4Config] = None
    ):
        super().__init__(
            name='legal',
            domain='legal',
            retriever=retriever,
            ollama=ollama,
            config=config
        )
    
    def can_handle(self, query: str) -> float:
        """Score based on legal keyword presence."""
        query_lower = query.lower()
        words = normalize_words(query)
        
        # Count matching legal keywords
        matches = len(words & LEGAL_KEYWORDS)
        
        # Boost for explicit section/rule references
        import re
        if re.search(r'section\s+\d+', query_lower):
            matches += 3
        if re.search(r'rule\s+\d+', query_lower):
            matches += 3
        if re.search(r'article\s+\d+', query_lower):
            matches += 2
        if re.search(r'act\s+\d{4}', query_lower):
            matches += 2
        
        # Boost for key legal action terms
        if re.search(r'\bobligations?\b', query_lower):
            matches += 2
        if re.search(r'\bapply\b', query_lower):
            matches += 2
        if re.search(r'\benforc(e|ement)\b', query_lower):
            matches += 2
        if re.search(r'\bliab(le|ility)\b', query_lower):
            matches += 2
        
        # Normalize (max reasonable matches ~10)
        score = min(1.0, matches / 8.0)
        return score
    
    def get_retrieval_filters(self, query: str) -> Dict[str, Any]:
        """Legal agent searches across all legal domains."""
        # No domain filter - search all legal documents
        return {}
    
    def get_system_prompt_suffix(self) -> str:
        return """SPECIALIZATION: You are a Legal Agent specializing in Indian statutory law.
Focus on: Acts, Sections, Rules, legal procedures, penalties, authorities, compliance requirements.
Always cite specific Section/Rule numbers. Preserve exact legal terminology.
If asked about a specific Section, quote or paraphrase it directly from context.
Do not provide legal advice - only state what the law says."""


if __name__ == '__main__':
    # Quick test
    from rag_engine import create_rag_engine
    engine = create_rag_engine()
    
    agent = LegalAgent(
        retriever=engine.retriever,
        ollama=engine.ollama,
        config=engine.config
    )
    
    test_queries = [
        "What does Section 11 of the Patents Act deal with?",
        "What is the penalty for patent infringement?",
        "What is the procedure for trademark registration?",
    ]
    
    for q in test_queries:
        print(f"\n{'='*60}")
        print(f"QUERY: {q}")
        print(f"Can handle score: {agent.can_handle(q):.2f}")
        result = agent.run(q, top_k=3)
        print(f"Status: {result.status}")
        print(f"Confidence: {result.confidence}")
        print(f"Sources: {len(result.sources)}")
        if result.answer:
            print(f"Answer: {result.answer[:300]}...")