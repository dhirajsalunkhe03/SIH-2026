#!/usr/bin/env python3
"""
IP Agent - Handles queries about:
- Patents
- Trademarks
- Geographical Indications (GI)
- Designs
- Copyright
- Plant Variety Protection
- IP registration/protection
- Patent/TK relationships
- GI/TK relationships
"""

from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent, AgentResult, normalize_words
from retriever import LegalRetriever
from ollama_utils import OllamaClient
from config import Phase4Config


# Keywords that indicate IP domain queries
IP_KEYWORDS = {
    # Patents
    'patent', 'patents', 'patentability', 'patentable', 'invention', 'inventive step',
    'novelty', 'industrial application', 'non-obviousness', 'prior art', 'state of the art',
    'patent application', 'patent grant', 'patent term', 'patent infringement',
    'compulsory license', 'compulsory licence', 'patent revocation', 'patent opposition',
    'patent office', 'controller of patents', 'patent agent', 'specification',
    'claim', 'claims', 'provisional specification', 'complete specification',
    'section 2', 'section 3', 'section 4', 'section 5', 'section 6', 'section 7',
    'section 8', 'section 9', 'section 10', 'section 11', 'section 12', 'section 13',
    'section 14', 'section 15', 'section 25', 'section 64', 'section 84', 'section 85',
    'section 86', 'section 87', 'section 88', 'section 89', 'section 90',
    
    # Trademarks
    'trade mark', 'trademark', 'trade marks', 'trademarks', 'mark', 'brand',
    'distinctive', 'distinctiveness', 'deceptively similar', 'identical mark',
    'trade mark registration', 'trademark registration', 'trade mark infringement',
    'trademark infringement', 'passing off', 'well known trade mark', 'well-known mark',
    'trade marks registry', 'registrar of trade marks', 'trade mark class',
    'nice classification', 'section 9', 'section 11', 'section 18', 'section 29',
    'section 30', 'section 31', 'section 134', 'section 135',
    
    # Geographical Indications
    'geographical indication', 'gi', 'geographical indications', 'indication of origin',
    'appellation of origin', 'protected geographical indication', 'pgi',
    'gi registration', 'gi tag', 'geographical indication tag', 'producer',
    'authorised user', 'registered proprietor', 'geographical indication registry',
    'section 2', 'section 11', 'section 15', 'section 21', 'section 22', 'section 23',
    'section 24', 'section 37', 'section 38', 'section 39', 'section 67',
    
    # Designs
    'design', 'designs', 'industrial design', 'design registration', 'design protection',
    'design infringement', 'piracy of design', 'article', 'features of shape',
    'configuration', 'pattern', 'ornament', 'composition of lines', 'composition of colours',
    'designs act', 'designs rules', 'controller of designs', 'design office',
    'section 2', 'section 4', 'section 5', 'section 6', 'section 11', 'section 19',
    'section 22', 'section 53',
    
    # Copyright (limited - not in corpus but handle queries)
    'copyright', 'copyright act', 'literary work', 'artistic work', 'musical work',
    'dramatic work', 'cinematograph film', 'sound recording', 'computer program',
    'author', 'owner', 'assignment', 'licence', 'fair dealing', 'moral rights',
    
    # Plant Varieties
    'plant variety', 'plant varieties', 'plant variety protection', 'ppvfr',
    'protection of plant varieties and farmers rights', 'farmers rights',
    'breeder', 'farmer', 'extant variety', 'new variety', 'essentially derived variety',
    
    # IP-TK-GI relationships
    'traditional knowledge patent', 'patent traditional knowledge', 'biopiracy',
    'tkdl', 'traditional knowledge digital library', 'prior art',
    'gi traditional knowledge', 'geographical indication traditional knowledge',
    'community rights', 'collective mark', 'certification mark',
}


class IPAgent(BaseAgent):
    """Agent for Intellectual Property queries."""
    
    def __init__(
        self,
        retriever: LegalRetriever,
        ollama: OllamaClient,
        config: Optional[Phase4Config] = None
    ):
        super().__init__(
            name='ip',
            domain='ip',
            retriever=retriever,
            ollama=ollama,
            config=config
        )
    
    def can_handle(self, query: str) -> float:
        """Score based on IP keyword presence."""
        query_lower = query.lower()
        words = normalize_words(query)
        
        matches = len(words & IP_KEYWORDS)
        
        # Check for multi-word phrases
        phrase_matches = sum(1 for phrase in IP_KEYWORDS if ' ' in phrase and phrase in query_lower)
        matches += phrase_matches * 2
        
        # Boost for specific IP contexts - HIGH VALUE TERMS
        import re
        if re.search(r'\bpatents?\b', query_lower):
            matches += 3  # Core patent term - high weight
        if re.search(r'trade\s*mark|trademark', query_lower):
            matches += 3
        if re.search(r'geographical\s+indication', query_lower):
            matches += 3
        if re.search(r'\bdesigns?\b', query_lower):
            matches += 3
        if re.search(r'plant\s+variet', query_lower):
            matches += 3
        if re.search(r'copyright', query_lower):
            matches += 2
        if re.search(r'section\s+\d+', query_lower):
            # Check if it's a known IP section
            ip_sections = ['2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13',
                          '14', '15', '18', '19', '21', '22', '23', '24', '25', '29',
                          '30', '31', '37', '38', '39', '53', '64', '67', '84', '85',
                          '86', '87', '88', '89', '90', '134', '135']
            for sec in ip_sections:
                if f'section {sec}' in query_lower:
                    matches += 2
                    break
        
        score = min(1.0, matches / 8.0)
        return score
    
    def get_retrieval_filters(self, query: str) -> Dict[str, Any]:
        """IP agent searches Patents, Trademarks, GI, Designs domains."""
        return {
            'domain': ['Patents', 'Trademarks', 'Geographical Indications', 'Designs']
        }
    
    def get_system_prompt_suffix(self) -> str:
        return """SPECIALIZATION: You are an IP Agent specializing in Indian Intellectual Property law.
Focus on: Patents (Patents Act, 1970), Trademarks (Trade Marks Act, 1999),
Geographical Indications (GI Act, 1999), Designs (Designs Act, 2000),
Plant Varieties (PPVFR Act, 2001).
Cover: Registration procedures, infringement, compulsory licensing,
revocation/cancellation, well-known marks, GI registration, design piracy.
Always cite specific Section/Rule numbers from the relevant Act.
For patent queries, reference Patents Act sections.
For trademark queries, reference Trade Marks Act sections.
For GI queries, reference GI Act sections.
For design queries, reference Designs Act sections.
Preserve exact legal terminology. Do not conflate different IP regimes."""


if __name__ == '__main__':
    from rag_engine import create_rag_engine
    engine = create_rag_engine()
    
    agent = IPAgent(
        retriever=engine.retriever,
        ollama=engine.ollama,
        config=engine.config
    )
    
    test_queries = [
        "What is a patent?",
        "What is a geographical indication?",
        "What does Section 11 of the Patents Act deal with?",
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