from typing import Dict, List, Any, Optional, Tuple
#!/usr/bin/env python3
"""
Normalize legal hierarchy into structured format:
Document -> Part -> Chapter -> Section/Rule -> subsection -> clause -> sub-clause -> proviso -> explanation
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from copy import deepcopy


@dataclass
class NormalizeReport:
    file_path: str
    sections_processed: int
    sections_with_hierarchy: int
    sections_preserved_as_content: int
    cross_references_extracted: int
    keywords_extracted: int


class LegalNormalizer:
    SUBSECTION_PATTERN = re.compile(r'\((\d+)\)')
    CLAUSE_PATTERN = re.compile(r'\(([a-z])\)')
    SUB_CLAUSE_PATTERN = re.compile(r'\((i{1,3}|iv|v|vi{0,3})\)', re.IGNORECASE)
    PROVISO_PATTERN = re.compile(r'(Provided that|Provided further that)', re.IGNORECASE)
    EXPLANATION_PATTERN = re.compile(r'(Explanation[.—:])', re.IGNORECASE)
    CROSS_REF_PATTERN = re.compile(
        r'\b(?:section|sub[-\s]?section|clause|sub[-\s]?clause|schedule|form|article|rule)\s+[\d\(\)ivx]+',
        re.IGNORECASE
    )

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

    def normalize(self, file_path: Path) -> Tuple[Dict, NormalizeReport]:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        pages = data.get('pages', [])
        if not pages and 'document' in data:
            pages = [data]

        sections_processed = 0
        sections_with_hierarchy = 0
        sections_preserved = 0
        cross_refs_total = 0
        keywords_total = 0

        for page in pages:
            for section in page.get('sections', []):
                sections_processed += 1
                normalized = self._normalize_section(section)
                section.update(normalized)
                if normalized.get('subsections') or normalized.get('provisos') or normalized.get('explanations'):
                    sections_with_hierarchy += 1
                else:
                    sections_preserved += 1
                cross_refs_total += len(normalized.get('cross_references', []))
                keywords_total += len(normalized.get('keywords', []))

            for section in page.get('amendments', []):
                sections_processed += 1
                normalized = self._normalize_section(section, is_amendment=True)
                section.update(normalized)

        report = NormalizeReport(
            file_path=str(file_path),
            sections_processed=sections_processed,
            sections_with_hierarchy=sections_with_hierarchy,
            sections_preserved_as_content=sections_preserved,
            cross_references_extracted=cross_refs_total,
            keywords_extracted=keywords_total
        )

        return data, report

    def _normalize_section(self, section: Dict, is_amendment: bool = False) -> Dict:
        content = section.get('content', '') or ''
        result = {
            'subsections': [],
            'provisos': [],
            'explanations': [],
            'cross_references': [],
            'keywords': [],
            'legal_entities': [],
            'dates': [],
            'authorities': []
        }

        if not content.strip():
            return result

        hierarchy = self._parse_hierarchy(content)
        if hierarchy['subsections'] or hierarchy['provisos'] or hierarchy['explanations']:
            result.update(hierarchy)
        else:
            result['content'] = content

        result['cross_references'] = self._extract_cross_references(content)
        result['keywords'] = self._extract_keywords(content)
        result['legal_entities'] = self._extract_legal_entities(content)
        result['dates'] = self._extract_dates(content)
        result['authorities'] = self._extract_authorities(content)

        return result

    def _parse_hierarchy(self, text: str) -> Dict:
        result = {
            'subsections': [],
            'provisos': [],
            'explanations': []
        }

        lines = text.split('\n')
        current_subsection = None
        current_clause = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            subsec_match = self.SUBSECTION_PATTERN.match(line)
            if subsec_match:
                if current_subsection:
                    result['subsections'].append(current_subsection)
                current_subsection = {
                    'number': f'({subsec_match.group(1)})',
                    'text': line,
                    'clauses': []
                }
                current_clause = None
                continue

            clause_match = self.CLAUSE_PATTERN.match(line)
            if clause_match and current_subsection:
                if current_clause:
                    current_subsection['clauses'].append(current_clause)
                current_clause = {
                    'number': f'({clause_match.group(1)})',
                    'text': line,
                    'sub_clauses': []
                }
                continue

            sub_clause_match = self.SUB_CLAUSE_PATTERN.match(line)
            if sub_clause_match and current_clause:
                current_clause['sub_clauses'].append({
                    'number': f'({sub_clause_match.group(1)})',
                    'text': line
                })
                continue

            proviso_match = self.PROVISO_PATTERN.search(line)
            if proviso_match:
                result['provisos'].append({
                    'text': line,
                    'type': proviso_match.group(1).lower().replace(' ', '_')
                })
                continue

            explanation_match = self.EXPLANATION_PATTERN.search(line)
            if explanation_match:
                result['explanations'].append({
                    'text': line
                })
                continue

            if current_subsection and not current_clause:
                current_subsection['text'] += ' ' + line
            elif current_clause:
                current_clause['text'] += ' ' + line

        if current_subsection:
            result['subsections'].append(current_subsection)
        if current_clause:
            current_subsection['clauses'].append(current_clause)

        return result

    def _extract_cross_references(self, text: str) -> List[Dict]:
        refs = []
        for match in self.CROSS_REF_PATTERN.finditer(text):
            ref_text = match.group(0)
            ref_type = self._classify_reference(ref_text)
            target = self._extract_target(ref_text)
            refs.append({
                'reference_text': ref_text,
                'reference_type': ref_type,
                'target': target
            })
        return refs

    def _classify_reference(self, ref: str) -> str:
        ref_lower = ref.lower()
        if 'section' in ref_lower and 'sub' not in ref_lower:
            return 'section'
        elif 'sub-section' in ref_lower or 'subsection' in ref_lower:
            return 'subsection'
        elif 'clause' in ref_lower and 'sub' not in ref_lower:
            return 'clause'
        elif 'sub-clause' in ref_lower or 'subclause' in ref_lower:
            return 'sub_clause'
        elif 'schedule' in ref_lower:
            return 'schedule'
        elif 'form' in ref_lower:
            return 'form'
        elif 'rule' in ref_lower:
            return 'rule'
        elif 'article' in ref_lower:
            return 'article'
        return 'other'

    def _extract_target(self, ref: str) -> str:
        nums = re.findall(r'[\d\(\)ivx]+', ref, re.IGNORECASE)
        if nums:
            return nums[0].strip('()')
        return ''

    def _extract_keywords(self, text: str) -> List[str]:
        keywords = []
        text_lower = text.lower()
        for domain, kws in self.DOMAIN_KEYWORDS.items():
            for kw in kws:
                if kw in text_lower and kw not in keywords:
                    keywords.append(kw)
        return keywords[:20]

    def _extract_legal_entities(self, text: str) -> List[str]:
        entities = []
        patterns = [
            r'\b(?:National Biodiversity Authority|State Biodiversity Board|Biodiversity Management Committee|Central Government|State Government)\b',
            r'\b(?:Controller|Patent Office|High Court|Supreme Court|National Green Tribunal)\b',
            r'\b(?:Ministry of \w+|Department of \w+)\b',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append(match.group(0))
        return list(set(entities))

    def _extract_dates(self, text: str) -> List[str]:
        dates = []
        patterns = [
            r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
            r'\b\d{4}\b',
            r'\b(?:w\.e\.f\.|with effect from)\s+[\d\-]+\b',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                dates.append(match.group(0))
        return list(set(dates))

    def _extract_authorities(self, text: str) -> List[str]:
        authorities = []
        patterns = [
            r'\b(?:Central Government|State Government|National Biodiversity Authority|State Biodiversity Board|Biodiversity Management Committee|Controller|Patent Office|High Court|Supreme Court|National Green Tribunal|Registrar)\b',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                authorities.append(match.group(0))
        return list(set(authorities))


def print_normalize_summary(report: NormalizeReport):
    print(f"\n{'='*60}")
    print(f"NORMALIZE REPORT: {Path(report.file_path).name}")
    print(f"{'='*60}")
    print(f"Sections processed:       {report.sections_processed}")
    print(f"Sections with hierarchy:  {report.sections_with_hierarchy}")
    print(f"Sections preserved:       {report.sections_preserved_as_content}")
    print(f"Cross-references found:   {report.cross_references_extracted}")
    print(f"Keywords extracted:       {report.keywords_extracted}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python legal_normalizer.py <input.json> [output.json]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(input_path.stem + '_NORMALIZED.json')

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    normalizer = LegalNormalizer()
    normalized_data, report = normalizer.normalize(input_path)

    print_normalize_summary(report)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(normalized_data, f, indent=2, ensure_ascii=False)

    with open(output_path.with_suffix('.normalize_report.json'), 'w', encoding='utf-8') as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False, default=str)

    print(f"\nNormalized JSON saved to: {output_path}")
    print(f"Normalize report saved to: {output_path.with_suffix('.normalize_report.json')}")


if __name__ == '__main__':
    main()