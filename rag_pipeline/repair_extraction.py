#!/usr/bin/env python3
"""
Repair broken legal extraction using deterministic Python rules.
Recovers section titles and content from raw_text.
Handles continuation pages and amendment acts.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from copy import deepcopy


@dataclass
class RepairAction:
    page_number: int
    action_type: str
    field: str
    before: str
    after: str
    reason: str


@dataclass
class RepairReport:
    file_path: str
    actions: List[RepairAction]
    sections_recovered: int
    titles_recovered: int
    content_recovered: int
    continuations_marked: int
    amendments_detected: int


class ExtractionRepairer:
    SECTION_PATTERN = re.compile(
        r'(?:^|\n)\s*(\d+)\.\s*([^\n]{5,200})',
        re.MULTILINE
    )

    AMENDMENT_SECTION_PATTERN = re.compile(
        r'(?:^|\n)\s*(\d+)\.\s+(?:Amendment|Substitution|Insertion|Omission|Repeal)\s+of\s+section\s+(\d+)',
        re.MULTILINE | re.IGNORECASE
    )

    SUBSTITUTION_PATTERN = re.compile(
        r'(?:^|\n)\s*For\s+section\s+(\d+)\s+of\s+the\s+principal\s+Act,?\s+the\s+following\s+section\s+shall\s+be\s+substituted',
        re.MULTILINE | re.IGNORECASE
    )

    AMENDMENT_HEADING_PATTERN = re.compile(
        r'(?:^|\n)\s*(\d+)\.\s+(?:In\s+section\s+\d+|For\s+section\s+\d+|After\s+section\s+\d+)',
        re.MULTILINE | re.IGNORECASE
    )

    RAW_SECTION_PATTERN = re.compile(
        r'(?:^|\n)\s*(\d+)\.\s+(?:\([^)]+\)\s*)?([A-Z][^\n]{10,})',
        re.MULTILINE
    )

    CONTINUATION_PATTERNS = [
        re.compile(r'(?:^|\n)\s*section\s+\d+\s+continues', re.IGNORECASE),
        re.compile(r'(?:^|\n)\s*contd\.', re.IGNORECASE),
        re.compile(r'(?:^|\n)\s*\(cont', re.IGNORECASE),
    ]

    def __init__(self):
        self.actions = []

    def repair(self, file_path: Path) -> Tuple[Dict, RepairReport]:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        original_data = deepcopy(data)
        pages = data.get('pages', [])
        if not pages and 'document' in data:
            pages = [data]

        is_amendment_act = self._detect_amendment_act(data)

        for i, page in enumerate(pages):
            raw_text = page.get('raw_text', '') or ''
            sections = page.get('sections', [])

            if not sections and raw_text:
                new_sections = self._extract_sections_from_raw_text(raw_text, page.get('page_number', i+1), is_amendment_act)
                if new_sections:
                    page['sections'] = new_sections
                    self._record_action(page.get('page_number', i+1), 'add_sections', 'sections',
                                      '[]', str(new_sections), 'Extracted sections from raw_text')

            for j, section in enumerate(sections):
                self._repair_section(section, raw_text, page.get('page_number', i+1), j, is_amendment_act)

            self._mark_continuations(page, pages, i)

            if is_amendment_act:
                amendments = self._extract_amendments(raw_text, page.get('page_number', i+1))
                if amendments:
                    page['amendments'] = amendments
                    self._record_action(page.get('page_number', i+1), 'add_amendments', 'amendments',
                                      '[]', str(amendments), 'Extracted amendments from raw_text')

        report = RepairReport(
            file_path=str(file_path),
            actions=self.actions,
            sections_recovered=sum(1 for a in self.actions if a.action_type == 'add_sections'),
            titles_recovered=sum(1 for a in self.actions if a.action_type == 'recover_title'),
            content_recovered=sum(1 for a in self.actions if a.action_type == 'recover_content'),
            continuations_marked=sum(1 for a in self.actions if a.action_type == 'mark_continuation'),
            amendments_detected=sum(1 for a in self.actions if a.action_type == 'add_amendments')
        )

        return data, report

    def _detect_amendment_act(self, data: Dict) -> bool:
        doc_name = data.get('document', {}).get('document_name', '').lower()
        return 'amendment' in doc_name

    def _extract_sections_from_raw_text(self, raw_text: str, page_num: int, is_amendment: bool) -> List[Dict]:
        sections = []

        if is_amendment:
            sections = self._extract_amendment_sections(raw_text, page_num)
        else:
            sections = self._extract_regular_sections(raw_text, page_num)

        return sections

    def _extract_regular_sections(self, raw_text: str, page_num: int) -> List[Dict]:
        sections = []

        raw_matches = list(self.RAW_SECTION_PATTERN.finditer(raw_text))
        for idx, match in enumerate(raw_matches):
            section_num = match.group(1)
            title_text = match.group(2).strip()

            start = match.end()
            end = raw_matches[idx + 1].start() if idx + 1 < len(raw_matches) else len(raw_text)
            content = raw_text[start:end].strip()

            title = self._clean_title(title_text)

            if content or title:
                sections.append({
                    'section_number': section_num,
                    'section_title': title,
                    'content': content,
                    'is_continuation': False,
                    'subsections': [],
                    'source_page': page_num
                })

        if not sections:
            matches = list(self.SECTION_PATTERN.finditer(raw_text))
            for idx, match in enumerate(matches):
                section_num = match.group(1)
                title_text = match.group(2).strip()

                start = match.end()
                end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw_text)
                content = raw_text[start:end].strip()

                title = self._clean_title(title_text)

                if content or title:
                    sections.append({
                        'section_number': section_num,
                        'section_title': title,
                        'content': content,
                        'is_continuation': False,
                        'subsections': [],
                        'source_page': page_num
                    })

        return sections

    def _extract_amendment_sections(self, raw_text: str, page_num: int) -> List[Dict]:
        sections = []

        sub_matches = list(self.SUBSTITUTION_PATTERN.finditer(raw_text))
        for match in sub_matches:
            target_section = match.group(1)
            start = match.start()
            next_match = self.SUBSTITUTION_PATTERN.search(raw_text, start + 1)
            end = next_match.start() if next_match else len(raw_text)
            amendment_text = raw_text[start:end].strip()

            sections.append({
                'section_number': target_section,
                'section_title': f'Substitution of section {target_section}',
                'content': amendment_text,
                'is_continuation': False,
                'subsections': [],
                'source_page': page_num,
                'is_amendment': True,
                'amendment_action': 'substitution'
            })

        amend_heading_matches = list(self.AMENDMENT_HEADING_PATTERN.finditer(raw_text))
        for match in amend_heading_matches:
            amend_num = match.group(1)
            start = match.start()
            next_match = self.AMENDMENT_HEADING_PATTERN.search(raw_text, start + 1)
            end = next_match.start() if next_match else len(raw_text)
            amendment_text = raw_text[start:end].strip()

            action = self._determine_amendment_action(amendment_text)
            target = self._extract_target_section(amendment_text)

            sections.append({
                'section_number': amend_num,
                'section_title': f'{action.capitalize()} of section {target}',
                'content': amendment_text,
                'is_continuation': False,
                'subsections': [],
                'source_page': page_num,
                'is_amendment': True,
                'amendment_action': action,
                'target_section': target
            })

        return sections

    def _determine_amendment_action(self, text: str) -> str:
        text_lower = text.lower()
        if 'substitution' in text_lower or 'substituted' in text_lower:
            return 'substitution'
        elif 'insertion' in text_lower or 'inserted' in text_lower:
            return 'insertion'
        elif 'omission' in text_lower or 'omitted' in text_lower:
            return 'omission'
        elif 'repeal' in text_lower:
            return 'repeal'
        elif 'amendment' in text_lower:
            return 'amendment'
        return 'amendment'

    def _extract_target_section(self, text: str) -> str:
        match = re.search(r'section\s+(\d+)', text, re.IGNORECASE)
        if match:
            return match.group(1)
        return 'unknown'

    def _clean_title(self, title: str) -> str:
        title = re.sub(r'\s+', ' ', title)
        title = re.sub(r'[.]+$', '', title)
        return title.strip()

    def _repair_section(self, section: Dict, raw_text: str, page_num: int, section_idx: int, is_amendment: bool):
        section_num = section.get('section_number', '')
        title = section.get('section_title', '') or ''
        content = section.get('content', '') or ''

        if not title.strip() and section_num:
            recovered_title = self._recover_title_from_raw(raw_text, section_num)
            if recovered_title:
                section['section_title'] = recovered_title
                self._record_action(page_num, 'recover_title', f'sections[{section_idx}].section_title',
                                  '""', f'"{recovered_title}"', f'Recovered title for section {section_num}')

        if not content.strip() and section_num:
            recovered_content = self._recover_content_from_raw(raw_text, section_num, is_amendment)
            if recovered_content:
                section['content'] = recovered_content
                self._record_action(page_num, 'recover_content', f'sections[{section_idx}].content',
                                  '""', f'"{recovered_content[:100]}..."', f'Recovered content for section {section_num}')

    def _recover_title_from_raw(self, raw_text: str, section_num: str) -> Optional[str]:
        patterns = [
            rf'(?:^|\n)\s*{re.escape(section_num)}\.\s*([^\n]{5,200})',
            rf'(?:^|\n)\s*{re.escape(section_num)}\s+([^\n]{5,200})',
            rf'section\s+{re.escape(section_num)}\s+([^\n]{5,200})',
        ]

        for pattern in patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE | re.MULTILINE)
            if match:
                return self._clean_title(match.group(1))
        return None

    def _recover_content_from_raw(self, raw_text: str, section_num: str, is_amendment: bool) -> Optional[str]:
        if is_amendment:
            patterns = [
                rf'(?:^|\n)\s*(?:Amendment|Substitution|Insertion|Omission|Repeal)\s+of\s+section\s+{re.escape(section_num)}.*?(?=\n\s*\d+\.\s+(?:Amendment|Substitution|Insertion|Omission|Repeal)\s+of\s+section|\Z)',
                rf'For\s+section\s+{re.escape(section_num)}\s+of\s+the\s+principal\s+Act.*?(?=For\s+section\s+\d+|\Z)',
                rf'(?:^|\n)\s*{re.escape(section_num)}\.\s+(?:In\s+section\s+\d+|For\s+section\s+\d+|After\s+section\s+\d+).*?(?=\n\s*\d+\.\s+|\Z)',
            ]
        else:
            patterns = [
                rf'(?:^|\n)\s*{re.escape(section_num)}\.\s*[^\n]*\n(.*?)(?=\n\s*\d+\.\s+[A-Z]|\n\s*CHAPTER|\n\s*$|\Z)',
                rf'(?:^|\n)\s*{re.escape(section_num)}\.\s*([^\n].*?)(?=\n\s*\d+\.\s+|\Z)',
            ]

        for pattern in patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                content = match.group(1) if match.lastindex else match.group(0)
                content = content.strip()
                if len(content) > 20:
                    return content[:5000]

        return None

    def _mark_continuations(self, page: Dict, all_pages: List[Dict], page_idx: int):
        sections = page.get('sections', [])
        page_num = page.get('page_number', page_idx + 1)

        if page_idx > 0:
            prev_page = all_pages[page_idx - 1]
            prev_sections = prev_page.get('sections', [])
            prev_raw = prev_page.get('raw_text', '') or ''

            for section in sections:
                if section.get('is_continuation'):
                    continue

                section_num = section.get('section_number', '')
                if not section_num:
                    continue

                for prev_section in prev_sections:
                    if prev_section.get('section_number') == section_num:
                        if not section.get('content') and prev_section.get('content'):
                            section['is_continuation'] = True
                            section['content'] = prev_section.get('content', '')
                            self._record_action(page_num, 'mark_continuation', f'section {section_num}',
                                              'false', 'true', f'Section {section_num} continues from page {prev_page.get("page_number")}')
                        break

    def _extract_amendments(self, raw_text: str, page_num: int) -> List[Dict]:
        amendments = []

        sub_matches = list(self.SUBSTITUTION_PATTERN.finditer(raw_text))
        for match in sub_matches:
            target = match.group(1)
            start = match.start()
            next_m = self.SUBSTITUTION_PATTERN.search(raw_text, start + 1)
            end = next_m.start() if next_m else len(raw_text)
            text = raw_text[start:end].strip()

            amendments.append({
                'amendment_number': f'sub_{target}',
                'target_section': target,
                'amendment_action': 'substitution',
                'amendment_text': text,
                'source_page': page_num
            })

        amend_matches = list(self.AMENDMENT_SECTION_PATTERN.finditer(raw_text))
        for match in amend_matches:
            amend_num = match.group(1)
            target = match.group(2)
            start = match.start()
            next_m = self.AMENDMENT_SECTION_PATTERN.search(raw_text, start + 1)
            end = next_m.start() if next_m else len(raw_text)
            text = raw_text[start:end].strip()
            action = self._determine_amendment_action(text)

            amendments.append({
                'amendment_number': amend_num,
                'target_section': target,
                'amendment_action': action,
                'amendment_text': text,
                'source_page': page_num
            })

        return amendments

    def _record_action(self, page_num: int, action_type: str, field: str, before: str, after: str, reason: str):
        self.actions.append(RepairAction(
            page_number=page_num,
            action_type=action_type,
            field=field,
            before=before[:200] if before else '',
            after=after[:200] if after else '',
            reason=reason
        ))


def print_repair_summary(report: RepairReport):
    print(f"\n{'='*60}")
    print(f"REPAIR REPORT: {Path(report.file_path).name}")
    print(f"{'='*60}")
    print(f"Sections recovered:     {report.sections_recovered}")
    print(f"Titles recovered:       {report.titles_recovered}")
    print(f"Content recovered:      {report.content_recovered}")
    print(f"Continuations marked:   {report.continuations_marked}")
    print(f"Amendments detected:    {report.amendments_detected}")
    print(f"Total actions:          {len(report.actions)}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python repair_extraction.py <input.json> [output.json]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(input_path.stem + '_REPAIRED.json')

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    repairer = ExtractionRepairer()
    repaired_data, report = repairer.repair(input_path)

    print_repair_summary(report)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(repaired_data, f, indent=2, ensure_ascii=False)

    with open(output_path.with_suffix('.repair_report.json'), 'w', encoding='utf-8') as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False, default=str)

    print(f"\nRepaired JSON saved to: {output_path}")
    print(f"Repair report saved to: {output_path.with_suffix('.repair_report.json')}")


if __name__ == '__main__':
    main()