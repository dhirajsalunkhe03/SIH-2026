#!/usr/bin/env python3
"""
RAG-Ready Data Utilities
Common operations on RAG-prepared JSON data
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional, Tuple
import re


class RAGDataLoader:
    """Load and access RAG-ready JSON data"""
    
    def __init__(self, json_path: str):
        with open(json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.json_path = json_path
    
    def get_all_sections(self) -> List[Dict]:
        """Extract all sections from all pages"""
        sections = []
        for page in self.data.get('pages', []):
            for section in page.get('sections', []):
                sections.append({
                    **section,
                    'page_number': page.get('page_number'),
                    'page_type': page.get('page_type'),
                    'document_name': self.data.get('document', {}).get('document_name'),
                })
        return sections
    
    def get_sections_by_number(self, section_number: str) -> List[Dict]:
        """Find all sections with given number"""
        sections = self.get_all_sections()
        return [s for s in sections if s.get('section_number') == section_number]
    
    def search_sections(self, query: str, case_sensitive: bool = False) -> List[Dict]:
        """Full-text search in section content"""
        sections = self.get_all_sections()
        results = []
        
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(re.escape(query), flags)
        
        for section in sections:
            content = section.get('content', '')
            if pattern.search(content):
                # Calculate relevance (# of matches)
                matches = len(pattern.findall(content))
                results.append({
                    **section,
                    'match_count': matches,
                    'relevance_score': matches
                })
        
        # Sort by relevance
        return sorted(results, key=lambda x: x['relevance_score'], reverse=True)
    
    def get_page(self, page_number: int) -> Dict:
        """Get specific page"""
        for page in self.data.get('pages', []):
            if page.get('page_number') == page_number:
                return page
        return None
    
    def get_raw_text(self, page_number: int) -> str:
        """Get raw OCR text from page"""
        page = self.get_page(page_number)
        return page.get('raw_text', '') if page else ""
    
    def get_sections_by_page(self, page_number: int) -> List[Dict]:
        """Get all sections from specific page"""
        page = self.get_page(page_number)
        return page.get('sections', []) if page else []
    
    def get_statistics(self) -> Dict:
        """Get document statistics"""
        pages = self.data.get('pages', [])
        all_sections = self.get_all_sections()
        
        # Calculate text statistics
        total_chars = 0
        total_words = 0
        for section in all_sections:
            content = section.get('content', '')
            total_chars += len(content)
            total_words += len(content.split())
        
        # Page type distribution
        page_types = {}
        for page in pages:
            ptype = page.get('page_type', 'unknown')
            page_types[ptype] = page_types.get(ptype, 0) + 1
        
        return {
            'total_pages': len(pages),
            'total_sections': len(all_sections),
            'total_characters': total_chars,
            'total_words': total_words,
            'average_section_length': total_chars // len(all_sections) if all_sections else 0,
            'page_types': page_types,
            'document_name': self.data.get('document', {}).get('document_name'),
            'processing_stage': self.data.get('metadata', {}).get('processing_stage'),
        }
    
    def export_sections_csv(self, output_path: str):
        """Export sections to CSV for analysis"""
        import csv
        sections = self.get_all_sections()
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'page_number', 'page_type', 'section_number', 'section_title',
                'content_length', 'is_continuation', 'document_name'
            ])
            writer.writeheader()
            
            for section in sections:
                writer.writerow({
                    'page_number': section.get('page_number'),
                    'page_type': section.get('page_type'),
                    'section_number': section.get('section_number'),
                    'section_title': section.get('section_title', ''),
                    'content_length': len(section.get('content', '')),
                    'is_continuation': section.get('is_continuation', False),
                    'document_name': section.get('document_name'),
                })


class RAGDataValidator:
    """Validate RAG-ready data quality"""
    
    def __init__(self, loader: RAGDataLoader):
        self.loader = loader
        self.issues = []
    
    def validate_all(self) -> Tuple[bool, List[str]]:
        """Run all validations"""
        self.issues = []
        
        self._validate_section_content()
        self._validate_cross_references()
        self._validate_continuation_chains()
        
        return len(self.issues) == 0, self.issues
    
    def _validate_section_content(self):
        """Check for empty or very short sections"""
        sections = self.loader.get_all_sections()
        
        for section in sections:
            content = section.get('content', '').strip()
            if not content:
                self.issues.append(
                    f"Empty content: Section {section.get('section_number')} "
                    f"(Page {section.get('page_number')})"
                )
            elif len(content) < 20:
                self.issues.append(
                    f"Very short content ({len(content)} chars): "
                    f"Section {section.get('section_number')} (Page {section.get('page_number')})"
                )
    
    def _validate_cross_references(self):
        """Check for broken cross-section references"""
        sections = self.loader.get_all_sections()
        section_numbers = {s.get('section_number') for s in sections if s.get('section_number')}
        
        # Look for section references in content
        for section in sections:
            content = section.get('content', '')
            # Find patterns like "Section 5" or "Sec. 3"
            matches = re.findall(r'[Ss]ection\s+(\d+[\w\.\-]*)', content)
            
            for match in matches:
                if match not in section_numbers:
                    self.issues.append(
                        f"Broken reference to Section {match} "
                        f"in Section {section.get('section_number')}"
                    )
    
    def _validate_continuation_chains(self):
        """Check continuation flags are properly chained"""
        pages = self.loader.data.get('pages', [])
        
        for page_idx, page in enumerate(pages):
            for section_idx, section in enumerate(page.get('sections', [])):
                if section.get('is_continuation'):
                    # Check if this section appears elsewhere
                    sec_num = section.get('section_number')
                    if sec_num:
                        matches = self.loader.get_sections_by_number(sec_num)
                        if len(matches) <= 1:
                            self.issues.append(
                                f"Orphaned continuation: Section {sec_num} "
                                f"marked as continuation but no primary section found"
                            )


class RAGDataComparator:
    """Compare multiple RAG-ready documents"""
    
    def __init__(self, *loaders: RAGDataLoader):
        self.loaders = loaders
    
    def compare_documents(self) -> Dict:
        """Compare statistics across documents"""
        stats = {}
        for loader in self.loaders:
            doc_name = Path(loader.json_path).name
            stats[doc_name] = loader.get_statistics()
        
        return stats
    
    def find_overlapping_sections(self, min_overlap_chars: int = 100) -> List[Dict]:
        """Find similar sections across documents"""
        overlaps = []
        
        for i, loader1 in enumerate(self.loaders):
            sections1 = loader1.get_all_sections()
            for j, loader2 in enumerate(self.loaders[i+1:], i+1):
                sections2 = loader2.get_all_sections()
                
                for s1 in sections1:
                    for s2 in sections2:
                        overlap = self._calculate_overlap(
                            s1.get('content', ''),
                            s2.get('content', '')
                        )
                        if overlap > min_overlap_chars:
                            overlaps.append({
                                'doc1': Path(loader1.json_path).name,
                                'section1': s1.get('section_number'),
                                'doc2': Path(loader2.json_path).name,
                                'section2': s2.get('section_number'),
                                'overlap_chars': overlap,
                            })
        
        return sorted(overlaps, key=lambda x: x['overlap_chars'], reverse=True)
    
    @staticmethod
    def _calculate_overlap(text1: str, text2: str, min_ngram: int = 5) -> int:
        """Calculate character-level overlap using n-grams"""
        if not text1 or not text2:
            return 0
        
        ngrams1 = {text1[i:i+min_ngram] for i in range(len(text1)-min_ngram+1)}
        overlap = sum(1 for ng in ngrams1 if ng in text2)
        
        return overlap * min_ngram


# Example usage
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 rag_utils.py <json_file> [command]")
        print("\nCommands:")
        print("  stats        - Show document statistics")
        print("  search TEXT  - Search sections")
        print("  validate     - Validate data quality")
        print("  export PATH  - Export sections to CSV")
        sys.exit(1)
    
    json_file = sys.argv[1]
    loader = RAGDataLoader(json_file)
    
    command = sys.argv[2] if len(sys.argv) > 2 else 'stats'
    
    if command == 'stats':
        stats = loader.get_statistics()
        print("\nDocument Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    elif command == 'search' and len(sys.argv) > 3:
        query = sys.argv[3]
        results = loader.search_sections(query)
        print(f"\nFound {len(results)} matches for '{query}':")
        for r in results[:5]:
            print(f"  Section {r.get('section_number')} (Page {r.get('page_number')}): "
                  f"{r.get('content', '')[:100]}...")
    
    elif command == 'validate':
        validator = RAGDataValidator(loader)
        is_valid, issues = validator.validate_all()
        print(f"\nValidation: {'✓ PASS' if is_valid else '✗ FAIL'}")
        if issues:
            print(f"Issues found ({len(issues)}):")
            for issue in issues[:10]:
                print(f"  - {issue}")
    
    elif command == 'export' and len(sys.argv) > 3:
        output = sys.argv[3]
        loader.export_sections_csv(output)
        print(f"✓ Exported to {output}")
