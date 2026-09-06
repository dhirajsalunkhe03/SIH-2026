#!/usr/bin/env python3
"""
Inspect JSON files for legal document extraction quality.
Reports statistics on documents, pages, sections, and potential issues.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter
from dataclasses import dataclass, asdict


@dataclass
class InspectionReport:
    file_path: str
    num_documents: int
    num_pages: int
    num_sections: int
    num_empty_title_sections: int
    num_empty_content_sections: int
    num_pages_raw_text_no_sections: int
    num_definitions: int
    num_amendments: int
    num_schedules: int
    num_forms: int
    page_type_counts: Dict[str, int]
    num_continuation_pages: int
    num_suspicious_pages: int
    avg_text_length_per_page: float
    avg_section_length: float
    suspicious_page_details: List[Dict[str, Any]]


class JSONInspector:
    LEGAL_PATTERNS = [
        r'\bsection\s+\d+',
        r'\bsection\s+\(?\d+\)?',
        r'\bsub[-\s]?section\s+\(?\d+\)?',
        r'\bclause\s+\(?[a-z]\)?',
        r'\bprovided\s+that',
        r'\bprovided\s+further\s+that',
        r'\bexplanation',
        r'\bmeans\b',
        r'\bshall\b',
        r'\bmay\b',
        r'\bsubject\s+to',
        r'\bnotwithstanding',
        r'\bschedule\s+[ivx]+',
        r'\bform\s+[a-z0-9]+',
        r'\b\d+\.\s+[A-Z]',
        r'\(\d+\)',
        r'\([a-z]\)',
    ]

    def __init__(self):
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.LEGAL_PATTERNS]

    def inspect_file(self, file_path: Path) -> InspectionReport:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        pages = data.get('pages', [])
        if not pages and 'document' in data:
            pages = [data]

        num_documents = 1
        num_pages = len(pages)
        num_sections = 0
        num_empty_title_sections = 0
        num_empty_content_sections = 0
        num_pages_raw_text_no_sections = 0
        num_definitions = 0
        num_amendments = 0
        num_schedules = 0
        num_forms = 0
        page_type_counts = Counter()
        num_continuation_pages = 0
        suspicious_pages = []
        total_text_length = 0
        total_section_length = 0
        section_count_for_avg = 0

        for page in pages:
            page_num = page.get('page_number', 0)
            page_type = page.get('page_type', 'unknown')
            page_type_counts[page_type] += 1

            raw_text = page.get('raw_text', '') or ''
            total_text_length += len(raw_text)

            sections = page.get('sections', [])
            rules = page.get('rules', [])
            amendments = page.get('amendments', [])
            definitions = page.get('definitions', [])
            schedules = page.get('schedules', [])
            forms = page.get('forms', [])

            num_sections += len(sections)
            num_definitions += len(definitions)
            num_amendments += len(amendments)
            num_schedules += len(schedules)
            num_forms += len(forms)

            has_extracted_structures = bool(sections or rules or amendments or definitions or schedules or forms)

            if raw_text.strip() and not has_extracted_structures:
                num_pages_raw_text_no_sections += 1
                suspicious_pages.append({
                    'page_number': page_num,
                    'reason': 'raw_text exists but no extracted structures',
                    'page_type': page_type,
                    'text_length': len(raw_text)
                })

            for section in sections:
                title = section.get('section_title', '') or ''
                content = section.get('content', '') or ''

                if not title.strip():
                    num_empty_title_sections += 1
                if not content.strip():
                    num_empty_content_sections += 1

                if content.strip():
                    total_section_length += len(content)
                    section_count_for_avg += 1

                if section.get('is_continuation'):
                    num_continuation_pages += 1

            if self._is_suspicious_page(page, raw_text, sections):
                suspicious_pages.append({
                    'page_number': page_num,
                    'reason': 'suspicious content patterns',
                    'page_type': page_type,
                    'text_length': len(raw_text),
                    'section_count': len(sections)
                })

        num_suspicious_pages = len(suspicious_pages)
        avg_text_length = total_text_length / num_pages if num_pages > 0 else 0
        avg_section_length = total_section_length / section_count_for_avg if section_count_for_avg > 0 else 0

        return InspectionReport(
            file_path=str(file_path),
            num_documents=num_documents,
            num_pages=num_pages,
            num_sections=num_sections,
            num_empty_title_sections=num_empty_title_sections,
            num_empty_content_sections=num_empty_content_sections,
            num_pages_raw_text_no_sections=num_pages_raw_text_no_sections,
            num_definitions=num_definitions,
            num_amendments=num_amendments,
            num_schedules=num_schedules,
            num_forms=num_forms,
            page_type_counts=dict(page_type_counts),
            num_continuation_pages=num_continuation_pages,
            num_suspicious_pages=num_suspicious_pages,
            avg_text_length_per_page=round(avg_text_length, 2),
            avg_section_length=round(avg_section_length, 2),
            suspicious_page_details=suspicious_pages
        )

    def _is_suspicious_page(self, page: Dict, raw_text: str, sections: List) -> bool:
        page_type = page.get('page_type', '')

        if page_type == 'form' and self._looks_like_legal_provisions(raw_text):
            return True

        if page_type == 'schedule' and not self._has_schedule_heading(raw_text):
            return True

        if raw_text and not sections:
            if self._has_legal_patterns(raw_text):
                return True

        for section in sections:
            title = section.get('section_title', '') or ''
            content = section.get('content', '') or ''
            if title and not content:
                return True
            if content and len(content.strip()) < 10:
                return True

        return False

    def _looks_like_legal_provisions(self, text: str) -> bool:
        legal_indicators = ['section', 'subsection', 'clause', 'provided that', 'shall', 'explanation']
        text_lower = text.lower()
        return sum(1 for ind in legal_indicators if ind in text_lower) >= 3

    def _has_schedule_heading(self, text: str) -> bool:
        return bool(re.search(r'schedule\s+[ivx]+', text, re.IGNORECASE))

    def _has_legal_patterns(self, text: str) -> bool:
        return any(p.search(text) for p in self.compiled_patterns)


def print_summary(report: InspectionReport):
    print(f"\n{'='*60}")
    print(f"INSPECTION REPORT: {Path(report.file_path).name}")
    print(f"{'='*60}")
    print(f"Documents:              {report.num_documents}")
    print(f"Pages:                  {report.num_pages}")
    print(f"Sections:               {report.num_sections}")
    print(f"  Empty titles:         {report.num_empty_title_sections}")
    print(f"  Empty content:        {report.num_empty_content_sections}")
    print(f"Pages with raw_text but no sections: {report.num_pages_raw_text_no_sections}")
    print(f"Definitions:            {report.num_definitions}")
    print(f"Amendments:             {report.num_amendments}")
    print(f"Schedules:              {report.num_schedules}")
    print(f"Forms:                  {report.num_forms}")
    print(f"Page types:             {dict(report.page_type_counts)}")
    print(f"Continuation pages:     {report.num_continuation_pages}")
    print(f"Suspicious pages:       {report.num_suspicious_pages}")
    print(f"Avg text length/page:   {report.avg_text_length_per_page:.0f} chars")
    print(f"Avg section length:     {report.avg_section_length:.0f} chars")

    if report.suspicious_page_details:
        print(f"\nSuspicious page details:")
        for sp in report.suspicious_page_details[:10]:
            print(f"  Page {sp['page_number']} ({sp['page_type']}): {sp['reason']}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python inspect_json.py <input.json> [output.json]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('inspection_report.json')

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    inspector = JSONInspector()
    report = inspector.inspect_file(input_path)

    print_summary(report)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False)

    print(f"\nReport saved to: {output_path}")


if __name__ == '__main__':
    main()