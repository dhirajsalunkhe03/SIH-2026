#!/usr/bin/env python3
"""
Traditional Knowledge (TK) Agent - Handles queries about:
- Traditional Knowledge
- Traditional medicinal knowledge
- Community knowledge
- Traditional practices
- TK protection
- TK documentation
- Relationship between TK and IP
- TK-related legal protection
"""

from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent, AgentResult, normalize_words
from retriever import LegalRetriever
from ollama_utils import OllamaClient
from config import Phase4Config


# Keywords that indicate TK domain queries
TK_KEYWORDS = {
    # Core TK terms
    'traditional knowledge', 'traditional medicinal knowledge', 'indigenous knowledge',
    'community knowledge', 'folk knowledge', 'local knowledge', 'ancestral knowledge',
    'traditional practice', 'traditional medicine', 'ayurveda', 'yoga', 'unani',
    'siddha', 'homeopathy', 'herbal medicine', 'medicinal plant',
    
    # TK protection
    'tk protection', 'protection of traditional knowledge', 'traditional knowledge protection',
    'prior informed consent', 'pic', 'mutually agreed terms', 'mat',
    'benefit sharing', 'fair and equitable', 'access and benefit sharing',
    'digital library', 'traditional knowledge digital library', 'tkdl',
    'documentation', 'register', 'database', 'repository',
    
    # TK & IP
    'traditional knowledge patent', 'patent traditional knowledge', 'biopiracy',
    'misappropriation', 'defensive protection', 'positive protection',
    'disclosure requirement', 'origin disclosure', 'source disclosure',
    'prior art', 'traditional knowledge prior art',
    
    # Communities & rights
    'indigenous community', 'local community', 'tribal community',
    'community rights', 'collective rights', 'customary law',
    'traditional cultural expression', 'tce', 'folklore',
    
    # Legal frameworks
    'biological diversity act', 'biodiversity act', 'traditional knowledge act',
    'patents act traditional knowledge', 'traditional knowledge bill',
    'national biodiversity authority', 'state biodiversity board',
    'biodiversity management committee', 'bmc',
}


class TKAgent(BaseAgent):
    """Agent for Traditional Knowledge queries."""
    
    def __init__(
        self,
        retriever: LegalRetriever,
        ollama: OllamaClient,
        config: Optional[Phase4Config] = None
    ):
        super().__init__(
            name='tk',
            domain='tk',
            retriever=retriever,
            ollama=ollama,
            config=config
        )
    
    def can_handle(self, query: str) -> float:
        """Score based on TK keyword presence."""
        query_lower = query.lower()
        words = normalize_words(query)
        
        matches = len(words & TK_KEYWORDS)
        
        # Check for multi-word phrases
        phrase_matches = sum(1 for phrase in TK_KEYWORDS if ' ' in phrase and phrase in query_lower)
        matches += phrase_matches * 2
        
        # Boost for specific TK contexts
        import re
        if re.search(r'traditional\s+knowledge', query_lower):
            matches += 3
        if re.search(r'prior\s+informed\s+consent', query_lower):
            matches += 2
        if re.search(r'benefit\s+sharing', query_lower):
            matches += 2
        if re.search(r'biopiracy|misappropriation', query_lower):
            matches += 3
        
        score = min(1.0, matches / 7.0)
        return score
    
    def get_retrieval_filters(self, query: str) -> Dict[str, Any]:
        """TK agent focuses on Biodiversity and Traditional Knowledge domains."""
        return {
            'domain': ['Biodiversity', 'Traditional Knowledge']
        }
    
    def get_system_prompt_suffix(self) -> str:
        return """SPECIALIZATION: You are a Traditional Knowledge (TK) Agent.
Focus on: Traditional Knowledge definitions, protection mechanisms, community rights,
prior informed consent, benefit sharing, documentation, TK-Patent relationships,
biopiracy prevention, TK Digital Library (TKDL).
Cite specific provisions from Biological Diversity Act, 2002 and related Rules.
Always distinguish between defensive protection (preventing patents) and 
positive protection (recognizing TK rights).
If corpus lacks specific TK evidence, explicitly state insufficient evidence."""


if __name__ == '__main__':
    from rag_engine import create_rag_engine
    engine = create_rag_engine()
    
    agent = TKAgent(
        retriever=engine.retriever,
        ollama=engine.ollama,
        config=engine.config
    )
    
    test_queries = [
        "What is traditional knowledge?",
        "What is prior informed consent under the Biological Diversity Act?",
        "Can traditional knowledge be protected through patents?",
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