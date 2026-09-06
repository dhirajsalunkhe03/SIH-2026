from typing import Dict, List, Any, Optional, Tuple
#!/usr/bin/env python3
"""
Create canonical legal JSON from normalized data.
Output follows the canonical structure specification.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from copy import deepcopy


@dataclass
class CanonicalReport:
    file_path: str
    documents_processed: int
    pages_processed: int
    sections_processed: int
    amendments_processed: int
    definitions_processed: int
    schedules_processed: int
    forms_processed: int


class Canonicalizer:
    DOC_TYPE_MAP = {
        'act': 'Act',
        'amendment act': 'Amendment Act',
        'amendment': 'Amendment Act',
        'rule': 'Rule',
        'regulation': 'Regulation',
        'notification': 'Notification',
        'order': 'Order',
        'schedule': 'Schedule',
        'form': 'Form',
    }

    DOMAIN_KEYWORDS = {
        'Biodiversity': ['biological diversity', 'biological resources', 'biodiversity', 'genetic resources', 'national biodiversity authority', 'state biodiversity board', 'biodiversity management committee'],
        'Access and Benefit Sharing': ['access', 'benefit sharing', 'benefit claimers', 'prior approval', 'mutually agreed terms', 'fair and equitable'],
        'Traditional Knowledge': ['traditional knowledge', 'codified traditional knowledge', 'indigenous knowledge', 'local communities', 'folk variety', 'landrace', 'cultivar', "farmers' variety"],
        'Patents': ['patent', 'invention', 'patentable', 'patentee', 'controller of patents', 'patent office', 'specification', 'claims'],
        'Intellectual Property': ['intellectual property', 'ip rights', 'copyright', 'trademark', 'design', 'geographical indication'],
        'Environment': ['environment', 'conservation', 'sustainable use', 'ecosystem', 'species', 'habitat'],
        'General Legal': ['shall', 'may', 'provided that', 'notwithstanding', 'subject to', 'herein', 'hereby'],
    }

    def __init__(self):
        pass

    def canonicalize(self, file_path: Path) -> Tuple[Dict, CanonicalReport]:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        pages = data.get('pages', [])
        if not pages and 'document' in data:
            pages = [data]

        doc_meta = data.get('document', {})
        doc_name = doc_meta.get('document_name', '')

        canonical = {
            'document': self._build_document_metadata(doc_meta, pages),
            'pages': []
        }

        pages_processed = 0
        sections_processed = 0
        amendments_processed = 0
        definitions_processed = 0
        schedules_processed = 0
        forms_processed = 0

        for page in pages:
            canonical_page = self._build_canonical_page(page)
            canonical['pages'].append(canonical_page)
            pages_processed += 1

            sections_processed += len(page.get('sections', []))
            amendments_processed += len(page.get('amendments', []))
            definitions_processed += len(page.get('definitions', []))
            schedules_processed += len(page.get('schedules', []))
            forms_processed += len(page.get('forms', []))

        report = CanonicalReport(
            file_path=str(file_path),
            documents_processed=1,
            pages_processed=pages_processed,
            sections_processed=sections_processed,
            amendments_processed=amendments_processed,
            definitions_processed=definitions_processed,
            schedules_processed=schedules_processed,
            forms_processed=forms_processed
        )

        return canonical, report

    def _build_document_metadata(self, doc_meta: Dict, pages: List[Dict]) -> Dict:
        doc_name = doc_meta.get('document_name', '')
        doc_type = doc_meta.get('document_type') or self._infer_document_type(doc_name, pages)
        year = doc_meta.get('year') or self._extract_year(doc_name, pages)
        jurisdiction = 'India'
        
        # Use domain from metadata if available, otherwise classify from text
        primary_domain = doc_meta.get('domain')
        secondary_domains = doc_meta.get('secondary_domains', [])
        if not primary_domain:
            primary_domain, secondary_domains = self._classify_domains(pages)
        
        # Preserve language from metadata
        language = doc_meta.get('language', 'unknown')

        return {
            'document_name': doc_name or None,
            'document_type': doc_type,
            'document_number': None,
            'year': year,
            'date': None,
            'jurisdiction': jurisdiction,
            'issuing_authority': None,
            'ministry': None,
            'department': None,
            'source': doc_meta.get('source', 'India Code') or 'India Code',
            'primary_domain': primary_domain,
            'secondary_domains': secondary_domains,
            'language': language
        }

    def _infer_document_type(self, doc_name: str, pages: List[Dict]) -> str:
        name_lower = doc_name.lower()
        for key, val in self.DOC_TYPE_MAP.items():
            if key in name_lower:
                return val

        for page in pages:
            raw = (page.get('raw_text', '') or '').lower()
            if 'amendment act' in raw:
                return 'Amendment Act'
            if 'act no' in raw or 'an act to' in raw:
                return 'Act'
            if 'rules' in raw and 'made under' in raw:
                return 'Rule'

        return 'Other'

    def _extract_year(self, doc_name: str, pages: List[Dict]) -> Optional[int]:
        match = re.search(r'\b(19|20)\d{2}\b', doc_name)
        if match:
            return int(match.group(0))

        for page in pages[:3]:
            raw = page.get('raw_text', '') or ''
            match = re.search(r'\b(19|20)\d{2}\b', raw)
            if match:
                return int(match.group(0))
        return None

    def _classify_domains(self, pages: List[Dict]) -> Tuple[Optional[str], List[str]]:
        all_text = ' '.join(page.get('raw_text', '') or '' for page in pages).lower()
        domain_scores = {}

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in all_text)
            if score > 0:
                domain_scores[domain] = score

        if not domain_scores:
            return None, []

        sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_domains[0][0]
        secondary = [d for d, s in sorted_domains[1:4] if s > 0]

        return primary, secondary

    def _build_canonical_page(self, page: Dict) -> Dict:
        page_num = page.get('page_number', 0)
        page_type = page.get('page_type', 'content')

        part_num, part_title = self._extract_part(page)
        chapter_num, chapter_title = self._extract_chapter(page)

        sections = []
        for section in page.get('sections', []):
            canonical_section = self._canonicalize_section(section)
            sections.append(canonical_section)

        amendments = []
        for amend in page.get('amendments', []):
            canonical_amend = self._canonicalize_amendment(amend)
            amendments.append(canonical_amend)

        definitions = page.get('definitions', [])
        schedules = page.get('schedules', [])
        forms = page.get('forms', [])
        tables = page.get('tables', [])

        dates = self._extract_page_dates(page)
        authorities = self._extract_page_authorities(page)
        cross_refs = self._extract_page_cross_refs(page)
        legal_entities = self._extract_page_entities(page)
        keywords = self._extract_page_keywords(page)

        ocr_notes = self._generate_ocr_notes(page, sections)

        return {
            'page_number': page_num,
            'page_type': page_type,
            'part_number': part_num,
            'part_title': part_title,
            'chapter_number': chapter_num,
            'chapter_title': chapter_title,
            'sections': sections,
            'rules': [],
            'amendments': amendments,
            'definitions': definitions,
            'schedules': schedules,
            'forms': forms,
            'tables': tables,
            'dates': dates,
            'authorities': authorities,
            'cross_references': cross_refs,
            'legal_entities': legal_entities,
            'keywords': keywords,
            'raw_text': page.get('raw_text', ''),
            'ocr_notes': ocr_notes
        }

    def _extract_part(self, page: Dict) -> Tuple[Optional[str], Optional[str]]:
        raw = page.get('raw_text', '') or ''
        match = re.search(r'CHAPTER\s+([IVX]+)\s*[.\-]?\s*([^\n]+)', raw, re.IGNORECASE)
        if match:
            return match.group(1), match.group(2).strip()
        return None, None

    def _extract_chapter(self, page: Dict) -> Tuple[Optional[str], Optional[str]]:
        raw = page.get('raw_text', '') or ''
        match = re.search(r'CHAPTER\s+([IVX]+)\s*[.\-]?\s*([^\n]+)', raw, re.IGNORECASE)
        if match:
            return match.group(1), match.group(2).strip()
        return None, None

    def _canonicalize_section(self, section: Dict) -> Dict:
        return {
            'section_number': section.get('section_number', ''),
            'section_title': section.get('section_title', '') or None,
            'content': section.get('content', '') or None,
            'subsections': section.get('subsections', []),
            'provisos': section.get('provisos', []),
            'explanations': section.get('explanations', []),
            'cross_references': section.get('cross_references', []),
            'keywords': section.get('keywords', []),
            'legal_entities': section.get('legal_entities', []),
            'dates': section.get('dates', []),
            'authorities': section.get('authorities', []),
            'is_continuation': section.get('is_continuation', False),
            'source_pages': section.get('source_pages', []),
            'is_amendment': section.get('is_amendment', False),
            'amendment_action': section.get('amendment_action'),
            'target_section': section.get('target_section'),
            'merge_status': section.get('_merge_status')
        }

    def _canonicalize_amendment(self, amend: Dict) -> Dict:
        return {
            'amendment_number': amend.get('amendment_number', amend.get('section_number', '')),
            'target_section': amend.get('target_section', ''),
            'amendment_action': amend.get('amendment_action', 'amendment'),
            'amendment_text': amend.get('content', amend.get('amendment_text', '')),
            'source_page': amend.get('source_page', amend.get('_source_page', 0))
        }

    def _extract_page_dates(self, page: Dict) -> List[str]:
        dates = []
        for section in page.get('sections', []):
            dates.extend(section.get('dates', []))
        return list(set(dates))

    def _extract_page_authorities(self, page: Dict) -> List[str]:
        authorities = []
        for section in page.get('sections', []):
            authorities.extend(section.get('authorities', []))
        return list(set(authorities))

    def _extract_page_cross_refs(self, page: Dict) -> List[Dict]:
        refs = []
        for section in page.get('sections', []):
            refs.extend(section.get('cross_references', []))
        return refs

    def _extract_page_entities(self, page: Dict) -> List[str]:
        entities = []
        for section in page.get('sections', []):
            entities.extend(section.get('legal_entities', []))
        return list(set(entities))

    def _extract_page_keywords(self, page: Dict) -> List[str]:
        keywords = []
        for section in page.get('sections', []):
            keywords.extend(section.get('keywords', []))
        return list(set(keywords))[:30]

    def _generate_ocr_notes(self, page: Dict, sections: List[Dict]) -> List[str]:
        notes = []
        raw = page.get('raw_text', '') or ''

        if not raw.strip():
            notes.append('Page has no raw_text')

        empty_sections = [s for s in sections if not s.get('content')]
        if empty_sections:
            notes.append(f'{len(empty_sections)} sections with empty content')

        if page.get('page_type') == 'form' and self._looks_like_provisions(raw):
            notes.append('Page classified as form but contains legal provisions')

        if page.get('page_type') == 'schedule' and 'schedule' not in raw.lower():
            notes.append('Page classified as schedule but no schedule heading found')

        return notes

    def _looks_like_provisions(self, text: str) -> bool:
        indicators = ['section', 'subsection', 'clause', 'provided that', 'shall', 'explanation']
        text_lower = text.lower()
        return sum(1 for ind in indicators if ind in text_lower) >= 3


def print_canonical_summary(report: CanonicalReport):
    print(f"\n{'='*60}")
    print(f"CANONICAL REPORT: {Path(report.file_path).name}")
    print(f"{'='*60}")
    print(f"Documents:      {report.documents_processed}")
    print(f"Pages:          {report.pages_processed}")
    print(f"Sections:       {report.sections_processed}")
    print(f"Amendments:     {report.amendments_processed}")
    print(f"Definitions:    {report.definitions_processed}")
    print(f"Schedules:      {report.schedules_processed}")
    print(f"Forms:          {report.forms_processed}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python canonicalize.py <input.json> [output.json]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(input_path.stem + '_CANONICAL.json')

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    canonicalizer = Canonicalizer()
    canonical_data, report = canonicalizer.canonicalize(input_path)

    print_canonical_summary(report)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(canonical_data, f, indent=2, ensure_ascii=False)

    with open(output_path.with_suffix('.canonical_report.json'), 'w', encoding='utf-8') as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False, default=str)

    print(f"\nCanonical JSON saved to: {output_path}")
    print(f"Canonical report saved to: {output_path.with_suffix('.canonical_report.json')}")


if __name__ == '__main__':
    main()