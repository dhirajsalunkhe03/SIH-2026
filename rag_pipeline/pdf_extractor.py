#!/usr/bin/env python3
"""
PDF text extraction with Marathi Unicode preservation.
Extracts page-by-page text with metadata for legal documents.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class PageData:
    page_number: int
    page_type: str
    title: Optional[str]
    chapter: Optional[str]
    sections: List[Dict]
    rules: List[Dict]
    definitions: List[Dict]
    amendments: List[Dict]
    schedules: List[Dict]
    forms: List[Dict]
    tables: List[Dict]
    raw_text: str
    language: str
    language_confidence: Optional[float]


@dataclass
class DocumentData:
    document_name: str
    document_type: str
    source: str
    total_pages: int
    language: str
    domain: str
    year: Optional[int]
    pages: List[PageData]


class LegalPDFExtractor:
    def __init__(self):
        self.language_detector = None
        self._init_language_detector()
    
    def _init_language_detector(self):
        try:
            from language_detector import LanguageDetector
            self.language_detector = LanguageDetector()
        except ImportError:
            pass
    
    def extract(self, pdf_path: Path, doc_metadata: Dict = None) -> DocumentData:
        import pdfplumber
        
        if doc_metadata is None:
            doc_metadata = self._infer_metadata_from_filename(pdf_path)
        
        doc_type = doc_metadata.get('document_type', 'Other')
        is_act = doc_type in ('Act', 'Amendment Act')
        is_rules = doc_type == 'Rules'
        
        pages = []
        all_text = ""
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                raw_text = page.extract_text() or ""
                
                # Clean OCR artifacts but preserve Unicode
                cleaned_text = self._clean_ocr_artifacts(raw_text)
                
                # Detect language for this page
                lang_result = None
                if self.language_detector:
                    lang_result = self.language_detector.detect(cleaned_text)
                
                page_lang = lang_result.language if lang_result else 'unknown'
                page_lang_conf = lang_result.language_confidence if lang_result else None
                
                # Classify page type
                page_type = self._classify_page_type(cleaned_text, page_num, total_pages)
                
                # Extract structural elements based on document type
                sections = []
                rules = []
                
                if page_type == 'table_of_contents':
                    # Skip extraction on TOC pages
                    pass
                elif is_act:
                    sections = self._extract_sections(cleaned_text)
                elif is_rules:
                    rules = self._extract_rules(cleaned_text)
                else:
                    # Unknown type - extract both but mark page_type
                    sections = self._extract_sections(cleaned_text)
                    rules = self._extract_rules(cleaned_text)
                
                definitions = self._extract_definitions(cleaned_text)
                amendments = self._extract_amendments(cleaned_text)
                schedules = self._extract_schedules(cleaned_text)
                forms = self._extract_forms(cleaned_text)
                tables = self._extract_tables(cleaned_text)
                
                page_data = PageData(
                    page_number=page_num,
                    page_type=page_type,
                    title=None,
                    chapter=None,
                    sections=sections,
                    rules=rules,
                    definitions=definitions,
                    amendments=amendments,
                    schedules=schedules,
                    forms=forms,
                    tables=tables,
                    raw_text=cleaned_text,
                    language=page_lang,
                    language_confidence=page_lang_conf
                )
                pages.append(page_data)
                all_text += cleaned_text + "\n"
        
        # Determine overall document language
        doc_lang_result = None
        if self.language_detector:
            doc_lang_result = self.language_detector.detect(all_text)
        doc_language = doc_lang_result.language if doc_lang_result else 'unknown'
        
        return DocumentData(
            document_name=doc_metadata.get('document_name', pdf_path.stem),
            document_type=doc_metadata.get('document_type', 'Other'),
            source=doc_metadata.get('source', 'India Code'),
            total_pages=total_pages,
            language=doc_language,
            domain=doc_metadata.get('domain', 'General Legal'),
            year=doc_metadata.get('year'),
            pages=pages
        )
    
    def _clean_ocr_artifacts(self, text: str) -> str:
        """Clean obvious OCR artifacts while preserving Unicode text."""
        if not text:
            return ""
        
        # Fix common OCR issues but preserve Devanagari
        # Fix broken words split across lines
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        # Fix spacing around punctuation (but not in Devanagari)
        text = re.sub(r'\s+([.,;:!?)])', r'\1', text)
        text = re.sub(r'([({])\s+', r'\1', text)
        
        # Normalize whitespace but preserve paragraph breaks
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove obvious OCR noise patterns
        text = re.sub(r'[|]{2,}', '', text)
        text = re.sub(r'[_]{3,}', '', text)
        
        # Mark unclear text
        text = re.sub(r'[^\w\s\u0900-\u097F.,;:!?()\[\]{}\-\'"\/]+', '[UNCLEAR]', text)
        
        return text.strip()
    
    def _classify_page_type(self, text: str, page_num: int, total_pages: int) -> str:
        text_lower = text.lower()
        
        if page_num <= 5:
            if any(kw in text_lower for kw in ['preamble', 'arrangement of sections', 'arrangement of rules', 'table of contents', 'contents']):
                return 'table_of_contents'
        
        if any(kw in text_lower for kw in ['schedule i', 'schedule ii', 'schedule iii', 'schedule iv', 'first schedule', 'second schedule']):
            return 'schedule'
        
        if any(kw in text_lower for kw in ['form ', 'form no', 'form no.']):
            return 'form'
        
        if 'definition' in text_lower and len(text) < 5000:
            return 'definition'
        
        return 'content'
    
    def _infer_metadata_from_filename(self, pdf_path: Path) -> Dict:
        name = pdf_path.stem
        folder = pdf_path.parent.name
        
        # Default values
        metadata = {
            'document_name': name.replace('_', ' ').replace('-', ' '),
            'document_type': 'Other',
            'domain': 'General Legal',
            'year': None,
            'source': 'India Code'
        }
        
        # Extract year
        year_match = re.search(r'(19|20)\d{2}', name)
        if year_match:
            metadata['year'] = int(year_match.group(0))
        
        # Classify by folder and filename
        name_lower = name.lower()
        folder_lower = folder.lower()
        
        if 'biological' in name_lower or 'biodiversity' in name_lower:
            metadata['domain'] = 'Biodiversity'
            if 'amendment' in name_lower:
                metadata['document_type'] = 'Amendment Act'
            else:
                metadata['document_type'] = 'Act'
        elif 'patent' in name_lower:
            metadata['domain'] = 'Patents'
            if 'rule' in name_lower:
                metadata['document_type'] = 'Rules'
            else:
                metadata['document_type'] = 'Act'
        elif 'design' in name_lower:
            metadata['domain'] = 'Designs'
            if 'rule' in name_lower:
                metadata['document_type'] = 'Rules'
            else:
                metadata['document_type'] = 'Act'
        elif 'geographical' in name_lower or 'gi_' in name_lower or 'gi ' in name_lower:
            metadata['domain'] = 'Geographical Indications'
            if 'rule' in name_lower:
                metadata['document_type'] = 'Rules'
            else:
                metadata['document_type'] = 'Act'
        elif 'trade_mark' in name_lower or 'trademark' in name_lower:
            metadata['domain'] = 'Trademarks'
            if 'rule' in name_lower:
                metadata['document_type'] = 'Rules'
            else:
                metadata['document_type'] = 'Act'
        elif 'copyright' in name_lower:
            metadata['domain'] = 'Copyright'
            if 'rule' in name_lower:
                metadata['document_type'] = 'Rules'
            else:
                metadata['document_type'] = 'Act'
        
        # Refine document name
        if metadata['document_type'] == 'Act':
            metadata['document_name'] = self._format_act_name(name, metadata['domain'], metadata['year'])
        elif metadata['document_type'] == 'Rules':
            metadata['document_name'] = self._format_rules_name(name, metadata['domain'], metadata['year'])
        
        return metadata
    
    def _format_act_name(self, name: str, domain: str, year: Optional[int]) -> str:
        domain_map = {
            'Biodiversity': 'Biological Diversity Act',
            'Patents': 'Patents Act',
            'Designs': 'Designs Act',
            'Geographical Indications': 'Geographical Indications of Goods Act',
            'Trademarks': 'Trade Marks Act',
            'Copyright': 'Copyright Act'
        }
        base = domain_map.get(domain, name.replace('_', ' ').replace('-', ' '))
        if year:
            return f"{base}, {year}"
        return base
    
    def _format_rules_name(self, name: str, domain: str, year: Optional[int]) -> str:
        domain_map = {
            'Biodiversity': 'Biological Diversity Rules',
            'Patents': 'Patents Rules',
            'Designs': 'Designs Rules',
            'Geographical Indications': 'Geographical Indications of Goods Rules',
            'Trademarks': 'Trade Marks Rules',
            'Copyright': 'Copyright Rules'
        }
        base = domain_map.get(domain, name.replace('_', ' ').replace('-', ' '))
        if year:
            return f"{base}, {year}"
        return base
    
    def _extract_sections(self, text: str) -> List[Dict]:
        """Extract sections from Acts."""
        sections = []
        # Pattern: Section number followed by title/content
        pattern = re.compile(
            r'(?:^|\n)\s*(\d+)\.\s*([^\n]{5,200})',
            re.MULTILINE
        )
        matches = list(pattern.finditer(text))
        
        for i, match in enumerate(matches):
            section_num = match.group(1)
            title_text = match.group(2).strip()
            
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            
            title = self._clean_title(title_text)
            
            sections.append({
                'section_number': section_num,
                'section_title': title,
                'content': content,
                'is_continuation': False,
                'subsections': [],
                'source_page': None
            })
        return sections
    
    def _extract_rules(self, text: str) -> List[Dict]:
        """Extract rules from Rules documents."""
        rules = []
        pattern = re.compile(
            r'(?:^|\n)\s*(\d+)\.\s*([^\n]{5,200})',
            re.MULTILINE
        )
        matches = list(pattern.finditer(text))
        
        for i, match in enumerate(matches):
            rule_num = match.group(1)
            title_text = match.group(2).strip()
            
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            
            title = self._clean_title(title_text)
            
            rules.append({
                'rule_number': rule_num,
                'rule_title': title,
                'content': content,
                'is_continuation': False,
                'subrules': [],
                'clauses': [],
                'provisos': [],
                'explanations': [],
                'source_page': None
            })
        return rules
    
    def _extract_definitions(self, text: str) -> List[Dict]:
        """Extract definitions."""
        definitions = []
        # Look for definition patterns
        pattern = re.compile(
            r'(?:^|\n)\s*[\(\[]([a-z])\)\s+["\']?([^"\']+)["\']?\s+means',
            re.MULTILINE | re.IGNORECASE
        )
        for match in pattern.finditer(text):
            definitions.append({
                'clause': match.group(1),
                'term': match.group(2).strip(),
                'definition_text': match.group(0).strip(),
                'source_page': None
            })
        return definitions
    
    def _extract_amendments(self, text: str) -> List[Dict]:
        """Extract amendment provisions."""
        amendments = []
        pattern = re.compile(
            r'(?:^|\n)\s*(\d+)\.\s+(?:Amendment|Substitution|Insertion|Omission|Repeal)\s+of\s+section\s+(\d+)',
            re.MULTILINE | re.IGNORECASE
        )
        for match in pattern.finditer(text):
            amendments.append({
                'amendment_number': match.group(1),
                'target_section': match.group(2),
                'amendment_action': match.group(0).split()[1].lower(),
                'amendment_text': match.group(0).strip(),
                'source_page': None
            })
        return amendments
    
    def _extract_schedules(self, text: str) -> List[Dict]:
        """Extract schedules."""
        schedules = []
        pattern = re.compile(
            r'(?:^|\n)\s*(?:Schedule|SCHEDULE)\s+([IVX]+|\d+)[\s\.\-:]*([^\n]*)',
            re.MULTILINE | re.IGNORECASE
        )
        for match in pattern.finditer(text):
            schedules.append({
                'schedule_number': match.group(1),
                'schedule_title': match.group(2).strip() if match.group(2) else None,
                'content': match.group(0).strip(),
                'source_page': None
            })
        return schedules
    
    def _extract_forms(self, text: str) -> List[Dict]:
        """Extract forms."""
        forms = []
        pattern = re.compile(
            r'(?:^|\n)\s*(?:Form|FORM)\s+([A-Z0-9]+)[\s\.\-:]*([^\n]*)',
            re.MULTILINE | re.IGNORECASE
        )
        for match in pattern.finditer(text):
            forms.append({
                'form_number': match.group(1),
                'form_title': match.group(2).strip() if match.group(2) else None,
                'content': match.group(0).strip(),
                'source_page': None
            })
        return forms
    
    def _extract_tables(self, text: str) -> List[Dict]:
        """Extract table references."""
        tables = []
        pattern = re.compile(
            r'(?:^|\n)\s*(?:Table|TABLE)\s+(\d+)[\s\.\-:]*([^\n]*)',
            re.MULTILINE | re.IGNORECASE
        )
        for match in pattern.finditer(text):
            tables.append({
                'table_number': match.group(1),
                'table_title': match.group(2).strip() if match.group(2) else None,
                'content': match.group(0).strip(),
                'source_page': None
            })
        return tables
    
    def _clean_title(self, title: str) -> str:
        title = re.sub(r'\s+', ' ', title)
        title = re.sub(r'[.]+$', '', title)
        title = re.sub(r'^["\']|["\']$', '', title)
        return title.strip()


def main():
    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor.py <pdf_path> [output.json]")
        return 1
    
    pdf_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(pdf_path.stem + '_EXTRACTED.json')
    
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        return 1
    
    extractor = LegalPDFExtractor()
    doc_data = extractor.extract(pdf_path)
    
    output = {
        'document': {
            'document_name': doc_data.document_name,
            'document_type': doc_data.document_type,
            'source': doc_data.source,
            'total_pages': doc_data.total_pages,
            'language': doc_data.language,
            'domain': doc_data.domain,
            'year': doc_data.year
        },
        'pages': [asdict(p) for p in doc_data.pages]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Extracted {doc_data.total_pages} pages")
    print(f"Document: {doc_data.document_name}")
    print(f"Type: {doc_data.document_type}")
    print(f"Domain: {doc_data.domain}")
    print(f"Language: {doc_data.language}")
    print(f"Output saved to: {output_path}")
    
    return 0


if __name__ == '__main__':
    main()