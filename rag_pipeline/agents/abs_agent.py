#!/usr/bin/env python3
"""
ABS (Access & Benefit Sharing) / Biodiversity Agent - Handles queries about:
- Access and Benefit Sharing (ABS)
- Biological resources
- Associated knowledge
- National Biodiversity Authority (NBA)
- State Biodiversity Boards (SBB)
- Biodiversity Management Committees (BMC)
- Benefit-sharing obligations
- Access permissions
- Biodiversity-related compliance
- Biological Diversity Act, 2002 and Rules
"""

from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent, AgentResult, normalize_words
from retriever import LegalRetriever
from ollama_utils import OllamaClient
from config import Phase4Config


# Keywords that indicate ABS/Biodiversity domain queries
ABS_KEYWORDS = {
    # Core ABS terms
    'access and benefit sharing', 'abs', 'benefit sharing', 'benefit-sharing',
    'fair and equitable sharing', 'mutually agreed terms', 'mat',
    'prior informed consent', 'pic', 'prior informed consent',
    
    # Biological resources
    'biological resource', 'biological resources', 'genetic resource', 'genetic resources',
    'bioresource', 'bioresources', 'associated knowledge', 'traditional knowledge associated',
    'derivative', 'derivatives', 'value added product',
    
    # Access & permissions
    'access permission', 'access permit', 'access application', 'form i', 'form ii', 'form iii',
    'national biodiversity authority', 'nba', 'state biodiversity board', 'sbb',
    'biodiversity management committee', 'bmc', 'local biodiversity fund',
    'national biodiversity fund', 'approval', 'authorization', 'consent',
    
    # Compliance & obligations
    'compliance', 'obligation', 'benefit sharing obligation', 'monetary benefit',
    'non-monetary benefit', 'royalty', 'license fee', 'milestone payment',
    'technology transfer', 'capacity building', 'research collaboration',
    
    # Specific provisions
    'biological diversity act', 'biodiversity act', 'biodiversity rules', 'abs rules',
    'section 3', 'section 4', 'section 6', 'section 7', 'section 19', 'section 20',
    'section 21', 'section 22', 'section 23', 'section 24', 'section 25',
    'exempt', 'exemption', 'normally traded as commodity', 'ntac',
    'collaborative research', 'international agreement', 'convention on biological diversity', 'cbd',
    'nagoya protocol', 'nagoya protocol on access and benefit sharing',
    
    # Offences & penalties
    'offence', 'penalty', 'contravention', 'punishment', 'fine', 'imprisonment',
    'section 55', 'section 56', 'section 57', 'section 58',
}


class ABSAgent(BaseAgent):
    """Agent for Access & Benefit Sharing / Biodiversity queries."""
    
    def __init__(
        self,
        retriever: LegalRetriever,
        ollama: OllamaClient,
        config: Optional[Phase4Config] = None
    ):
        super().__init__(
            name='abs',
            domain='abs',
            retriever=retriever,
            ollama=ollama,
            config=config
        )
    
    def can_handle(self, query: str) -> float:
        """Score based on ABS/Biodiversity keyword presence."""
        query_lower = query.lower()
        words = normalize_words(query)
        
        matches = len(words & ABS_KEYWORDS)
        
        # Check for multi-word phrases (higher weight)
        phrase_matches = sum(1 for phrase in ABS_KEYWORDS if ' ' in phrase and phrase in query_lower)
        matches += phrase_matches * 2
        
        # Boost for specific ABS contexts
        import re
        if re.search(r'access\s+and\s+benefit\s+sharing', query_lower):
            matches += 3
        if re.search(r'biological\s+resource', query_lower):
            matches += 2
        if re.search(r'prior\s+informed\s+consent', query_lower):
            matches += 2
        if re.search(r'benefit\s+sharing', query_lower):
            matches += 2
        if re.search(r'national\s+biodiversity\s+authority|state\s+biodiversity\s+board', query_lower):
            matches += 3
        if re.search(r'biodiversity\s+management\s+committee', query_lower):
            matches += 2
        
        score = min(1.0, matches / 7.0)
        return score
    
    def get_retrieval_filters(self, query: str) -> Dict[str, Any]:
        """ABS agent focuses on Biodiversity domain."""
        return {
            'domain': ['Biodiversity']
        }
    
    def get_system_prompt_suffix(self) -> str:
        return """SPECIALIZATION: You are an ABS/Biodiversity Agent specializing in 
Access and Benefit Sharing under the Biological Diversity Act, 2002.
Focus on: Biological resources access, prior informed consent (PIC), mutually agreed terms (MAT),
benefit sharing (monetary & non-monetary), National Biodiversity Authority (NBA),
State Biodiversity Boards (SBB), Biodiversity Management Committees (BMC),
exemptions (normally traded as commodities), offences and penalties.
Cite specific Sections from Biological Diversity Act, 2002 and Biological Diversity Rules.
Distinguish between commercial utilization and non-commercial research.
If corpus lacks specific ABS evidence, explicitly state insufficient evidence."""


if __name__ == '__main__':
    from rag_engine import create_rag_engine
    engine = create_rag_engine()
    
    agent = ABSAgent(
        retriever=engine.retriever,
        ollama=engine.ollama,
        config=engine.config
    )
    
    test_queries = [
        "What is access and benefit sharing?",
        "What permissions are required to access a biological resource?",
        "What are the benefit sharing obligations under the Biological Diversity Act?",
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