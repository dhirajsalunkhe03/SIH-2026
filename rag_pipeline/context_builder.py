#!/usr/bin/env python3
"""
Context builder for RAG system.
Constructs structured context from retrieved legal chunks for Qwen3.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ContextSource:
    """Structured source information for a retrieved chunk."""
    rank: int
    document: str
    document_type: str
    document_year: int
    domain: str
    language: str
    section_number: Optional[str]
    section_title: Optional[str]
    rule_number: Optional[str]
    rule_title: Optional[str]
    source_pages: List[int]
    score: float
    text: str
    keywords: List[str]
    cross_references: List[str]


class ContextBuilder:
    """Builds structured context for LLM from retrieved chunks."""
    
    def __init__(self, max_context_chars: int = 8000):
        self.max_context_chars = max_context_chars
    
    def build_context(self, retrieved_results: List[Dict]) -> str:
        """
        Build structured context string from retrieval results.
        
        Args:
            retrieved_results: List of result dicts from retriever.search_multilingual()
            
        Returns:
            Formatted context string with numbered sources
        """
        if not retrieved_results:
            return "No relevant legal provisions found in the knowledge base."
        
        sources = []
        total_chars = 0
        
        for result in retrieved_results:
            source = self._parse_result(result)
            source_text = self._format_source(source)
            
            if total_chars + len(source_text) > self.max_context_chars:
                # Truncate the last source if needed
                remaining = self.max_context_chars - total_chars
                if remaining > 200:
                    source_text = source_text[:remaining] + "\n[TRUNCATED]"
                    sources.append(source_text)
                break
            
            sources.append(source_text)
            total_chars += len(source_text)
        
        context = "\n\n".join(sources)
        
        # Add summary header
        header = f"RETRIEVED LEGAL SOURCES ({len(sources)} sources):\n"
        return header + context
    
    def _parse_result(self, result: Dict) -> ContextSource:
        """Parse retriever result into structured source."""
        return ContextSource(
            rank=result.get('rank', 0),
            document=result.get('document', ''),
            document_type=result.get('document_type', ''),
            document_year=result.get('document_year', 0),
            domain=result.get('domain', ''),
            language=result.get('language', ''),
            section_number=result.get('section_number') if result.get('section_number') else None,
            section_title=result.get('section_title') if result.get('section_title') else None,
            rule_number=result.get('rule_number') if result.get('rule_number') else None,
            rule_title=result.get('rule_title') if result.get('rule_title') else None,
            source_pages=result.get('source_pages', []),
            score=result.get('score', 0.0),
            text=result.get('text', ''),
            keywords=result.get('keywords', []),
            cross_references=result.get('cross_references', [])
        )
    
    def _format_source(self, source: ContextSource) -> str:
        """Format a single source as a numbered context block."""
        lines = []
        
        # Header
        lines.append(f"SOURCE {source.rank}")
        
        # Document info
        doc_line = f"Document: {source.document}"
        if source.document_year:
            doc_line += f" ({source.document_year})"
        lines.append(doc_line)
        
        # Type
        lines.append(f"Type: {source.document_type}")
        
        # Domain
        if source.domain:
            lines.append(f"Domain: {source.domain}")
        
        # Language
        if source.language:
            lines.append(f"Language: {source.language}")
        
        # Section or Rule
        if source.section_number:
            sec_line = f"Section: {source.section_number}"
            if source.section_title:
                sec_line += f" — {source.section_title}"
            lines.append(sec_line)
        elif source.rule_number:
            rule_line = f"Rule: {source.rule_number}"
            if source.rule_title:
                rule_line += f" — {source.rule_title}"
            lines.append(rule_line)
        else:
            lines.append("Section/Rule: Information unavailable in retrieved metadata")
        
        # Pages
        if source.source_pages:
            pages_str = ", ".join(str(p) for p in source.source_pages)
            lines.append(f"Pages: {pages_str}")
        
        # Score
        lines.append(f"Relevance Score: {source.score:.4f}")
        
        # Keywords
        if source.keywords:
            kw = ", ".join(source.keywords[:8])
            lines.append(f"Keywords: {kw}")
        
        # Cross-references
        if source.cross_references:
            xrefs = []
            for xr in source.cross_references[:5]:
                ref_text = xr.get('reference_text', '') if isinstance(xr, dict) else str(xr)
                xrefs.append(ref_text)
            if xrefs:
                lines.append(f"Cross-references: {', '.join(xrefs)}")
        
        lines.append("")  # Empty line before text
        
        # Legal text (preserved exactly)
        text = source.text.strip()
        if text:
            lines.append(text)
        else:
            lines.append("[No text content available]")
        
        return "\n".join(lines)
    
    def build_source_list(self, retrieved_results: List[Dict]) -> List[Dict]:
        """Build simplified source list for citation output."""
        sources = []
        for result in retrieved_results:
            source = {
                "rank": result.get('rank', 0),
                "document": result.get('document', ''),
                "document_type": result.get('document_type', ''),
                "document_year": result.get('document_year', 0),
                "section_number": result.get('section_number'),
                "section_title": result.get('section_title'),
                "rule_number": result.get('rule_number'),
                "rule_title": result.get('rule_title'),
                "source_pages": result.get('source_pages', []),
                "score": result.get('score', 0.0),
                "language": result.get('language', ''),
                "domain": result.get('domain', '')
            }
            sources.append(source)
        return sources


def format_sources_for_citation(sources: List[Dict]) -> str:
    """Format sources for final answer citation."""
    if not sources:
        return "No sources available."
    
    lines = ["Sources:"]
    for i, s in enumerate(sources, 1):
        parts = []
        
        # Document
        doc = s.get('document', 'Unknown Document')
        if s.get('document_year'):
            doc += f" ({s['document_year']})"
        parts.append(doc)
        
        # Section or Rule
        if s.get('section_number'):
            sec = f"Section {s['section_number']}"
            if s.get('section_title'):
                sec += f" — {s['section_title']}"
            parts.append(sec)
        elif s.get('rule_number'):
            rule = f"Rule {s['rule_number']}"
            if s.get('rule_title'):
                rule += f" — {s['rule_title']}"
            parts.append(rule)
        else:
            parts.append("Section/Rule information unavailable in retrieved metadata")
        
        # Pages
        pages = s.get('source_pages', [])
        if pages:
            pages_str = ", ".join(str(p) for p in pages)
            parts.append(f"Pages {pages_str}")
        
        lines.append(f"  {i}. {' | '.join(parts)}")
    
    return "\n".join(lines)


if __name__ == '__main__':
    # Test with sample data
    sample_results = [
        {
            "rank": 1,
            "document": "Patents Act, 1970",
            "document_type": "Act",
            "document_year": 1970,
            "domain": "Patents",
            "language": "en",
            "section_number": "3",
            "section_title": "What are not inventions",
            "rule_number": None,
            "rule_title": None,
            "source_pages": [2, 3],
            "score": 0.75,
            "text": "The following are not inventions within the meaning of this Act, — (a) an invention which is frivolous or which claims anything obviously contrary to well established natural laws; ...",
            "keywords": ["invention", "patent", "frivolous"],
            "cross_references": [{"reference_text": "section 3", "reference_type": "section", "target": "3"}]
        },
        {
            "rank": 2,
            "document": "Patents Rules, 2003",
            "document_type": "Rules",
            "document_year": 2003,
            "domain": "Patents",
            "language": "mr",
            "section_number": None,
            "section_title": None,
            "rule_number": "2",
            "rule_title": "Definitions",
            "source_pages": [1, 2],
            "score": 0.68,
            "text": "पेटंट नियम २००३ मधील परिभाषा...",
            "keywords": ["पेटंट", "नियम", "परिभाषा"],
            "cross_references": []
        }
    ]
    
    builder = ContextBuilder()
    context = builder.build_context(sample_results)
    print("=== CONTEXT ===")
    print(context)
    print("\n=== CITATIONS ===")
    sources = builder.build_source_list(sample_results)
    print(format_sources_for_citation(sources))