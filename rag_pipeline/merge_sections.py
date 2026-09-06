#!/usr/bin/env python3
"""
Merge sections that span multiple pages.
Uses deterministic signals: continuation flags, content continuity, page adjacency.
Does NOT merge table of contents entries with actual sections.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
from copy import deepcopy


@dataclass
class MergeAction:
    section_number: str
    source_pages: List[int]
    action: str
    reason: str


@dataclass
class MergeReport:
    file_path: str
    actions: List[MergeAction]
    sections_before: int
    sections_after: int
    sections_merged: int
    uncertain_merges: int


class SectionMerger:
    def __init__(self):
        self.actions = []

    def merge(self, file_path: Path) -> Tuple[Dict, MergeReport]:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        pages = data.get('pages', [])
        if not pages and 'document' in data:
            pages = [data]

        all_sections = []
        for page in pages:
            page_num = page.get('page_number', 0)
            page_type = page.get('page_type', '')
            for section in page.get('sections', []):
                section['_source_page'] = page_num
                section['_page_type'] = page_type
                all_sections.append(section)

        sections_before = len(all_sections)

        merged_sections = self._merge_sections(all_sections)

        sections_after = len(merged_sections)

        page_sections = defaultdict(list)
        for section in merged_sections:
            page_num = section.get('_source_page', 0)
            page_sections[page_num].append(section)

        for page in pages:
            page_num = page.get('page_number', 0)
            page['sections'] = page_sections.get(page_num, [])
            for s in page['sections']:
                s.pop('_source_page', None)
                s.pop('_page_type', None)
                s.pop('_merge_status', None)

        report = MergeReport(
            file_path=str(file_path),
            actions=self.actions,
            sections_before=sections_before,
            sections_after=sections_after,
            sections_merged=sum(1 for a in self.actions if a.action == 'merged'),
            uncertain_merges=sum(1 for a in self.actions if a.action == 'uncertain')
        )

        return data, report

    def _merge_sections(self, sections: List[Dict]) -> List[Dict]:
        by_section_num = defaultdict(list)
        for section in sections:
            num = self._normalize_section_number(section.get('section_number', ''))
            if num:
                by_section_num[num].append(section)

        merged = []

        for section_num, section_list in by_section_num.items():
            if len(section_list) == 1:
                merged.append(section_list[0])
                self.actions.append(MergeAction(
                    section_number=section_num,
                    source_pages=[section_list[0].get('_source_page', 0)],
                    action='kept_separate',
                    reason='Only one occurrence'
                ))
                continue

            section_list.sort(key=lambda s: s.get('_source_page', 0))
            merged_result = self._merge_section_list(section_num, section_list)
            if isinstance(merged_result, list):
                merged.extend(merged_result)
            else:
                merged.append(merged_result)

        other_sections = [s for s in sections if not self._normalize_section_number(s.get('section_number', ''))]
        merged.extend(other_sections)

        return merged

    def _normalize_section_number(self, num: str) -> str:
        if not num:
            return ''
        return num.strip().rstrip('.').rstrip()

    def _is_toc_entry(self, section: Dict) -> bool:
        content = section.get('content', '') or ''
        title = section.get('section_title', '') or ''
        page_type = section.get('_page_type', '')
        page_num = section.get('_source_page', 0)

        if page_type == 'table_of_contents':
            return True
        if page_type == 'preamble' and page_num <= 3:
            return True
        if len(content.strip()) < 50 and len(title.strip()) > 0:
            return True
        if re.match(r'^\d+\.\s*[A-Z][a-z]+', title) and not content.strip():
            return True
        return False

    def _merge_section_list(self, section_num: str, section_list: List[Dict]) -> List[Dict]:
        non_toc = [s for s in section_list if not self._is_toc_entry(s)]
        toc = [s for s in section_list if self._is_toc_entry(s)]

        if not non_toc:
            for s in toc:
                self.actions.append(MergeAction(
                    section_number=section_num,
                    source_pages=[s.get('_source_page', 0)],
                    action='kept_separate',
                    reason='TOC entry only'
                ))
            return toc

        if len(non_toc) == 1:
            for s in toc:
                self.actions.append(MergeAction(
                    section_number=section_num,
                    source_pages=[s.get('_source_page', 0)],
                    action='kept_separate',
                    reason='TOC entry, actual section exists elsewhere'
                ))
            return [non_toc[0]]

        non_toc.sort(key=lambda s: s.get('_source_page', 0))
        merged_sections = []
        current_group = [non_toc[0]]

        for i in range(1, len(non_toc)):
            prev = current_group[-1]
            curr = non_toc[i]

            if self._should_merge(prev, curr):
                current_group.append(curr)
            else:
                if len(current_group) > 1:
                    merged = self._merge_group(current_group)
                    merged_sections.append(merged)
                else:
                    merged_sections.append(current_group[0])
                current_group = [curr]

        if len(current_group) > 1:
            merged = self._merge_group(current_group)
            merged_sections.append(merged)
        else:
            merged_sections.append(current_group[0])

        return merged_sections

    def _should_merge(self, prev: Dict, curr: Dict) -> bool:
        if curr.get('is_continuation'):
            return True

        prev_page = prev.get('_source_page', 0)
        curr_page = curr.get('_source_page', 0)

        if curr_page - prev_page > 2:
            return False

        prev_content = (prev.get('content', '') or '').strip()
        curr_content = (curr.get('content', '') or '').strip()

        if not prev_content and not curr_content:
            return False

        if prev_content and curr_content:
            if self._is_duplicate_content(prev_content, curr_content):
                return False
            if self._content_continues(prev_content, curr_content):
                return True

        if curr.get('is_continuation'):
            return True

        return curr_page - prev_page == 1

    def _content_continues(self, prev: str, curr: str) -> bool:
        prev_end = prev[-100:] if len(prev) > 100 else prev
        curr_start = curr[:100] if len(curr) > 100 else curr

        prev_words = set(prev_end.lower().split())
        curr_words = set(curr_start.lower().split())

        if not prev_words or not curr_words:
            return False

        overlap = len(prev_words & curr_words) / min(len(prev_words), len(curr_words))
        return overlap > 0.15

    def _is_duplicate_content(self, content1: str, content2: str) -> bool:
        if not content1 or not content2:
            return False
        words1 = set(content1.split())
        words2 = set(content2.split())
        if not words1 or not words2:
            return False
        overlap = len(words1 & words2) / min(len(words1), len(words2))
        return overlap > 0.7

    def _merge_group(self, group: List[Dict]) -> Dict:
        base = deepcopy(group[0])
        source_pages = [base.get('_source_page', 0)]
        base['source_pages'] = source_pages
        merged_content = base.get('content', '') or ''
        base['_merge_status'] = 'merged'

        for section in group[1:]:
            source_pages.append(section.get('_source_page', 0))
            curr_content = section.get('content', '') or ''
            curr_title = section.get('section_title', '') or ''

            if not base.get('section_title') and curr_title:
                base['section_title'] = curr_title

            if curr_content:
                if merged_content and not self._is_duplicate_content(merged_content, curr_content):
                    if merged_content and not merged_content.endswith('\n'):
                        merged_content += '\n'
                    merged_content += curr_content

        base['content'] = merged_content.strip()

        self.actions.append(MergeAction(
            section_number=base.get('section_number', ''),
            source_pages=source_pages,
            action='merged',
            reason=f'Merged {len(group)} parts across pages {source_pages}'
        ))

        return base


def print_merge_summary(report: MergeReport):
    print(f"\n{'='*60}")
    print(f"MERGE REPORT: {Path(report.file_path).name}")
    print(f"{'='*60}")
    print(f"Sections before merge:  {report.sections_before}")
    print(f"Sections after merge:   {report.sections_after}")
    print(f"Sections merged:        {report.sections_merged}")
    print(f"Uncertain merges:       {report.uncertain_merges}")
    print(f"Total actions:          {len(report.actions)}")

    for action in report.actions[:20]:
        print(f"  Section {action.section_number}: {action.action} (pages {action.source_pages}) - {action.reason}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python merge_sections.py <input.json> [output.json]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(input_path.stem + '_MERGED.json')

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    merger = SectionMerger()
    merged_data, report = merger.merge(input_path)

    print_merge_summary(report)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)

    with open(output_path.with_suffix('.merge_report.json'), 'w', encoding='utf-8') as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False, default=str)

    print(f"\nMerged JSON saved to: {output_path}")
    print(f"Merge report saved to: {output_path.with_suffix('.merge_report.json')}")


if __name__ == '__main__':
    main()