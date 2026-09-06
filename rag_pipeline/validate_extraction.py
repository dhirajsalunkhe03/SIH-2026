#!/usr/bin/env python3
"""
Validate legal extraction quality - not just JSON syntax.
Checks structural validity, content completeness, and legal pattern detection.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict, field
from collections import defaultdict


@dataclass
class ValidationIssue:
    severity: str  # 'error', 'warning', 'info'
    category: str  # 'structural', 'content', 'legal_pattern'
    page_number: int
    field: str
    message: str
    context: str = ''


@dataclass
class ValidationReport:
    file_path: str
    is_valid_json: bool
    is_valid_structure: bool
    issues: List[ValidationIssue]
    structural_errors: int
    structural_warnings: int
    content_errors: int
    content_warnings: int
    legal_pattern_flags: int
    pages_with_raw_text_no_structures: int
    sections_with_empty_title: int
    sections_with_empty_content: int
    sections_with_missing_legal_text: int
    duplicate_page_numbers: List[int]
    missing_page_numbers: List[int]
    invalid_page_types: List[str]


class ExtractionValidator:
    VALID_PAGE_TYPES = {
        'preamble', 'content', 'schedule', 'form', 'definition',
        'table_of_contents', 'appendix', 'annexure', 'index',
        'amendment', 'repeal', 'substitution', 'insertion', 'omission'
    }

    LEGAL_PATTERNS = [
        (r'\bsection\s+\d+\b', 'section_reference'),
        (r'\bsub[-\s]?section\s+\(?\d+\)?', 'subsection_reference'),
        (r'\bclause\s+\(?[a-z]\)?', 'clause_reference'),
        (r'\bprovided\s+that\b', 'proviso'),
        (r'\bprovided\s+further\s+that\b', 'further_proviso'),
        (r'\bexplanation\b', 'explanation'),
        (r'\bmeans\b', 'definition'),
        (r'\bshall\b', 'mandatory'),
        (r'\bmay\b', 'permissive'),
        (r'\bsubject\s+to\b', 'subject_to'),
        (r'\bnotwithstanding\b', 'notwithstanding'),
        (r'\bschedule\s+[ivx]+\b', 'schedule_reference'),
        (r'\bform\s+[a-z0-9]+\b', 'form_reference'),
        (r'^\d+\.\s+[A-Z]', 'numbered_section'),
        (r'^\(\d+\)', 'numbered_subsection'),
        (r'^\([a-z]\)', 'numbered_clause'),
        (r'\bamendment\s+(?:of|to)\s+section', 'amendment_action'),
        (r'\bsubstitution\s+(?:of|for)\s+section', 'substitution_action'),
        (r'\binsertion\s+(?:of|after)\s+section', 'insertion_action'),
        (r'\bomission\s+(?:of|from)\s+section', 'omission_action'),
        (r'\brepeal\s+(?:of|section)', 'repeal_action'),
    ]

    def __init__(self):
        self.compiled_patterns = [(re.compile(p, re.IGNORECASE | re.MULTILINE), cat) for p, cat in self.LEGAL_PATTERNS]

    def validate(self, file_path: Path) -> ValidationReport:
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            is_valid_json = True
        except json.JSONDecodeError as e:
            return ValidationReport(
                file_path=str(file_path),
                is_valid_json=False,
                is_valid_structure=False,
                issues=[ValidationIssue('error', 'structural', 0, 'json', f'Invalid JSON: {e}')],
                structural_errors=1, structural_warnings=0, content_errors=0,
                content_warnings=0, legal_pattern_flags=0,
                pages_with_raw_text_no_structures=0,
                sections_with_empty_title=0, sections_with_empty_content=0,
                sections_with_missing_legal_text=0,
                duplicate_page_numbers=[], missing_page_numbers=[],
                invalid_page_types=[]
            )

        pages = data.get('pages', [])
        if not pages and 'document' in data:
            pages = [data]

        seen_page_numbers = set()
        duplicate_pages = []
        all_page_numbers = []

        for page in pages:
            page_num = page.get('page_number')
            if page_num is not None:
                all_page_numbers.append(page_num)
                if page_num in seen_page_numbers:
                    duplicate_pages.append(page_num)
                seen_page_numbers.add(page_num)

        if all_page_numbers:
            expected_range = set(range(min(all_page_numbers), max(all_page_numbers) + 1))
            missing_pages = sorted(expected_range - set(all_page_numbers))
        else:
            missing_pages = []

        invalid_page_types = []
        pages_raw_text_no_structures = 0
        sections_empty_title = 0
        sections_empty_content = 0
        sections_missing_legal_text = 0
        legal_pattern_flags = 0

        for page in pages:
            page_num = page.get('page_number', 0)
            page_type = page.get('page_type', '')

            if page_type and page_type not in self.VALID_PAGE_TYPES:
                invalid_page_types.append(page_type)
                issues.append(ValidationIssue(
                    'warning', 'structural', page_num, 'page_type',
                    f'Invalid page_type: {page_type}',
                    f'Valid types: {sorted(self.VALID_PAGE_TYPES)}'
                ))

            raw_text = page.get('raw_text', '') or ''
            sections = page.get('sections', [])
            rules = page.get('rules', [])
            amendments = page.get('amendments', [])
            definitions = page.get('definitions', [])
            schedules = page.get('schedules', [])
            forms = page.get('forms', [])

            has_structures = bool(sections or rules or amendments or definitions or schedules or forms)

            if raw_text.strip() and not has_structures:
                pages_raw_text_no_structures += 1
                issues.append(ValidationIssue(
                    'warning', 'content', page_num, 'raw_text',
                    'Page has raw_text but no extracted structures',
                    f'raw_text length: {len(raw_text)}'
                ))

            for idx, section in enumerate(sections):
                title = section.get('section_title', '') or ''
                content = section.get('content', '') or ''
                section_num = section.get('section_number', f'idx_{idx}')

                if not title.strip():
                    sections_empty_title += 1
                    issues.append(ValidationIssue(
                        'warning', 'content', page_num, f'sections[{idx}].section_title',
                        'Section has empty title',
                        f'section_number: {section_num}'
                    ))

                if not content.strip():
                    sections_empty_content += 1
                    issues.append(ValidationIssue(
                        'warning', 'content', page_num, f'sections[{idx}].content',
                        'Section has empty content',
                        f'section_number: {section_num}'
                    ))

                if raw_text and content:
                    if not self._legal_text_in_extracted(raw_text, content):
                        sections_missing_legal_text += 1
                        issues.append(ValidationIssue(
                            'warning', 'legal_pattern', page_num, f'sections[{idx}].content',
                            'Legal text in raw_text not found in extracted content',
                            f'section_number: {section_num}, raw_text_sample: {raw_text[:200]}'
                        ))

            page_legal_flags = self._detect_legal_patterns(raw_text, page_num)
            legal_pattern_flags += len(page_legal_flags)
            issues.extend(page_legal_flags)

        structural_errors = sum(1 for i in issues if i.severity == 'error' and i.category == 'structural')
        structural_warnings = sum(1 for i in issues if i.severity == 'warning' and i.category == 'structural')
        content_errors = sum(1 for i in issues if i.severity == 'error' and i.category == 'content')
        content_warnings = sum(1 for i in issues if i.severity == 'warning' and i.category == 'content')

        is_valid_structure = structural_errors == 0

        return ValidationReport(
            file_path=str(file_path),
            is_valid_json=True,
            is_valid_structure=is_valid_structure,
            issues=issues,
            structural_errors=structural_errors,
            structural_warnings=structural_warnings,
            content_errors=content_errors,
            content_warnings=content_warnings,
            legal_pattern_flags=legal_pattern_flags,
            pages_with_raw_text_no_structures=pages_raw_text_no_structures,
            sections_with_empty_title=sections_empty_title,
            sections_with_empty_content=sections_empty_content,
            sections_with_missing_legal_text=sections_missing_legal_text,
            duplicate_page_numbers=duplicate_pages,
            missing_page_numbers=missing_pages,
            invalid_page_types=list(set(invalid_page_types))
        )

    def _legal_text_in_extracted(self, raw_text: str, extracted_content: str) -> bool:
        raw_words = set(re.findall(r'\b\w{4,}\b', raw_text.lower()))
        ext_words = set(re.findall(r'\b\w{4,}\b', extracted_content.lower()))
        if not raw_words:
            return True
        overlap = len(raw_words & ext_words) / len(raw_words)
        return overlap > 0.3

    def _detect_legal_patterns(self, text: str, page_num: int) -> List[ValidationIssue]:
        flags = []
        for pattern, category in self.compiled_patterns:
            matches = pattern.findall(text)
            if matches:
                flags.append(ValidationIssue(
                    'info', 'legal_pattern', page_num, 'raw_text',
                    f'Detected {category}: {matches[:5]}',
                    f'Total matches: {len(matches)}'
                ))
        return flags


def print_validation_summary(report: ValidationReport):
    print(f"\n{'='*60}")
    print(f"VALIDATION REPORT: {Path(report.file_path).name}")
    print(f"{'='*60}")
    print(f"Valid JSON:           {report.is_valid_json}")
    print(f"Valid Structure:      {report.is_valid_structure}")
    print(f"Structural Errors:    {report.structural_errors}")
    print(f"Structural Warnings:  {report.structural_warnings}")
    print(f"Content Errors:       {report.content_errors}")
    print(f"Content Warnings:     {report.content_warnings}")
    print(f"Legal Pattern Flags:  {report.legal_pattern_flags}")
    print(f"Pages raw_text only:  {report.pages_with_raw_text_no_structures}")
    print(f"Empty section titles: {report.sections_with_empty_title}")
    print(f"Empty section content: {report.sections_with_empty_content}")
    print(f"Missing legal text:   {report.sections_with_missing_legal_text}")
    print(f"Duplicate pages:      {report.duplicate_page_numbers}")
    print(f"Missing pages:        {report.missing_page_numbers}")
    print(f"Invalid page types:   {report.invalid_page_types}")

    error_issues = [i for i in report.issues if i.severity == 'error']
    if error_issues:
        print(f"\nERRORS:")
        for issue in error_issues[:10]:
            print(f"  Page {issue.page_number} [{issue.category}]: {issue.message}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_extraction.py <input.json> [output.json]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('validation_report.json')

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    validator = ExtractionValidator()
    report = validator.validate(input_path)

    print_validation_summary(report)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False, default=str)

    print(f"\nReport saved to: {output_path}")

    if not report.is_valid_structure:
        sys.exit(1)


if __name__ == '__main__':
    main()