from typing import Dict, List, Any, Optional, Tuple
#!/usr/bin/env python3
"""
Create RAG chunks from canonical legal JSON.
Each section becomes one RAG document with embedding_text for future embedding.
"""

import json
import re
import sys
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ChunkReport:
    file_path: str
    total_chunks: int
    chunks_by_type: Dict[str, int]
    chunks_with_hierarchy: int
    avg_chunk_length: float
    max_chunk_length: int


class RAGChunkCreator:
    MAX_CHUNK_LENGTH = 8000
    MIN_CHUNK_LENGTH = 100

    def __init__(self):
        pass

    def create_chunks(self, file_path: Path) -> Tuple[List[Dict], ChunkReport]:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        doc_meta = data.get('document', {})
        pages = data.get('pages', [])

        doc_name = doc_meta.get('document_name', 'Unknown Document')
        doc_type = doc_meta.get('document_type', 'Other')
        doc_year = doc_meta.get('year')
        jurisdiction = doc_meta.get('jurisdiction', 'India')
        source = doc_meta.get('source', 'India Code')
        primary_domain = doc_meta.get('primary_domain', 'General Legal')
        secondary_domains = doc_meta.get('secondary_domains', [])
        language = doc_meta.get('language', 'unknown')

        chunks = []
        chunk_id_counter = 0

        for page in pages:
            page_num = page.get('page_number', 0)
            for section in page.get('sections', []):
                section_chunks = self._create_section_chunks(
                    section, doc_name, doc_type, doc_year,
                    jurisdiction, source, primary_domain, secondary_domains,
                    language, chunk_id_counter
                )
                chunks.extend(section_chunks)
                chunk_id_counter += len(section_chunks)

            for amend in page.get('amendments', []):
                amend_chunks = self._create_amendment_chunks(
                    amend, doc_name, doc_type, doc_year,
                    jurisdiction, source, primary_domain, secondary_domains,
                    language, chunk_id_counter
                )
                chunks.extend(amend_chunks)
                chunk_id_counter += len(amend_chunks)

        chunks_by_type = {}
        for chunk in chunks:
            ctype = chunk.get('chunk_type', 'section')
            chunks_by_type[ctype] = chunks_by_type.get(ctype, 0) + 1

        chunks_with_hierarchy = sum(1 for c in chunks if c.get('metadata', {}).get('has_hierarchy', False))
        lengths = [len(c.get('text', '')) for c in chunks]
        avg_length = sum(lengths) / len(lengths) if lengths else 0
        max_length = max(lengths) if lengths else 0

        report = ChunkReport(
            file_path=str(file_path),
            total_chunks=len(chunks),
            chunks_by_type=chunks_by_type,
            chunks_with_hierarchy=chunks_with_hierarchy,
            avg_chunk_length=round(avg_length, 2),
            max_chunk_length=max_length
        )

        return chunks, report

    def _create_section_chunks(self, section: Dict, doc_name: str, doc_type: str,
                               doc_year: Optional[int], jurisdiction: str, source: str,
                               primary_domain: str, secondary_domains: List[str],
                               language: str, start_id: int) -> List[Dict]:
        chunks = []
        section_num = section.get('section_number', '')
        section_title = section.get('section_title', '') or ''
        content = section.get('content', '') or ''
        subsections = section.get('subsections', [])
        provisos = section.get('provisos', [])
        explanations = section.get('explanations', [])
        cross_refs = section.get('cross_references', [])
        keywords = section.get('keywords', [])
        legal_entities = section.get('legal_entities', [])
        dates = section.get('dates', [])
        authorities = section.get('authorities', [])
        source_pages = section.get('source_pages', [section.get('_source_page', 0)])
        is_continuation = section.get('is_continuation', False)
        is_amendment = section.get('is_amendment', False)
        amendment_action = section.get('amendment_action')
        target_section = section.get('target_section')
        merge_status = section.get('merge_status')

        if not content.strip() and not subsections and not provisos and not explanations:
            return chunks

        full_text = self._build_full_text(content, subsections, provisos, explanations)

        if len(full_text) <= self.MAX_CHUNK_LENGTH:
            chunk = self._build_chunk(
                chunk_id=f"{self._slugify(doc_name)}_sec_{section_num}_{start_id}",
                doc_name=doc_name,
                doc_type=doc_type,
                doc_year=doc_year,
                section_number=section_num,
                section_title=section_title,
                text=full_text,
                source_pages=source_pages,
                domain=primary_domain,
                keywords=keywords,
                cross_refs=cross_refs,
                jurisdiction=jurisdiction,
                source=source,
                chunk_type='section' if not is_amendment else 'amendment',
                has_hierarchy=bool(subsections or provisos or explanations),
                secondary_domains=secondary_domains,
                legal_entities=legal_entities,
                dates=dates,
                authorities=authorities,
                is_continuation=is_continuation,
                is_amendment=is_amendment,
                amendment_action=amendment_action,
                target_section=target_section,
                merge_status=merge_status,
                language=language
            )
            chunks.append(chunk)
        else:
            sub_chunks = self._split_long_section(
                full_text, section_num, section_title, source_pages,
                doc_name, doc_type, doc_year, jurisdiction, source,
                primary_domain, secondary_domains, keywords, cross_refs,
                legal_entities, dates, authorities, start_id, language
            )
            chunks.extend(sub_chunks)

        return chunks

    def _create_amendment_chunks(self, amend: Dict, doc_name: str, doc_type: str,
                                 doc_year: Optional[int], jurisdiction: str, source: str,
                                 primary_domain: str, secondary_domains: List[str],
                                 language: str, start_id: int) -> List[Dict]:
        chunks = []
        amend_num = amend.get('amendment_number', '')
        target = amend.get('target_section', '')
        action = amend.get('amendment_action', 'amendment')
        text = amend.get('amendment_text', '') or amend.get('content', '') or ''
        source_page = amend.get('source_page', 0)

        if not text.strip():
            return chunks

        chunk = self._build_chunk(
            chunk_id=f"{self._slugify(doc_name)}_amend_{amend_num}_{start_id}",
            doc_name=doc_name,
            doc_type=doc_type,
            doc_year=doc_year,
            section_number=target,
            section_title=f"{action.capitalize()} of section {target}",
            text=text,
            source_pages=[source_page],
            domain=primary_domain,
            keywords=[],
            cross_refs=[],
            jurisdiction=jurisdiction,
            source=source,
            chunk_type='amendment',
            has_hierarchy=False,
            secondary_domains=secondary_domains,
            legal_entities=[],
            dates=[],
            authorities=[],
            is_continuation=False,
            is_amendment=True,
            amendment_action=action,
            target_section=target,
            merge_status=None,
            language=language
        )
        chunks.append(chunk)
        return chunks

    def _build_full_text(self, content: str, subsections: List, provisos: List, explanations: List) -> str:
        parts = []
        if content.strip():
            parts.append(content.strip())

        for sub in subsections:
            sub_text = sub.get('text', '')
            if sub_text.strip():
                parts.append(sub_text.strip())
            for clause in sub.get('clauses', []):
                clause_text = clause.get('text', '')
                if clause_text.strip():
                    parts.append(clause_text.strip())
                for sub_clause in clause.get('sub_clauses', []):
                    sc_text = sub_clause.get('text', '')
                    if sc_text.strip():
                        parts.append(sc_text.strip())

        for proviso in provisos:
            prov_text = proviso.get('text', '')
            if prov_text.strip():
                parts.append(prov_text.strip())

        for expl in explanations:
            expl_text = expl.get('text', '')
            if expl_text.strip():
                parts.append(expl_text.strip())

        return '\n\n'.join(parts)

    def _split_long_section(self, full_text: str, section_num: str, section_title: str,
                            source_pages: List, doc_name: str, doc_type: str,
                            doc_year: Optional[int], jurisdiction: str, source: str,
                            primary_domain: str, secondary_domains: List[str],
                            keywords: List, cross_refs: List,
                            legal_entities: List, dates: List, authorities: List,
                            start_id: int, language: str) -> List[Dict]:
        chunks = []
        paragraphs = [p.strip() for p in full_text.split('\n\n') if p.strip()]

        current_chunk = ''
        chunk_idx = 0

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= self.MAX_CHUNK_LENGTH:
                if current_chunk:
                    current_chunk += '\n\n' + para
                else:
                    current_chunk = para
            else:
                if current_chunk and len(current_chunk) >= self.MIN_CHUNK_LENGTH:
                    chunk = self._build_chunk(
                        chunk_id=f"{self._slugify(doc_name)}_sec_{section_num}_{start_id + chunk_idx}",
                        doc_name=doc_name,
                        doc_type=doc_type,
                        doc_year=doc_year,
                        section_number=section_num,
                        section_title=f"{section_title} (part {chunk_idx + 1})" if section_title else f"Section {section_num} (part {chunk_idx + 1})",
                        text=current_chunk,
                        source_pages=source_pages,
                        domain=primary_domain,
                        keywords=keywords,
                        cross_refs=cross_refs,
                        jurisdiction=jurisdiction,
                        source=source,
                        chunk_type='section',
                        has_hierarchy=True,
                        secondary_domains=secondary_domains,
                        legal_entities=legal_entities,
                        dates=dates,
                        authorities=authorities,
                        is_continuation=True,
                        is_amendment=False,
                        amendment_action=None,
                        target_section=None,
                        merge_status='split',
                        language=language
                    )
                    chunks.append(chunk)
                    chunk_idx += 1
                current_chunk = para

        if current_chunk and len(current_chunk) >= self.MIN_CHUNK_LENGTH:
            chunk = self._build_chunk(
                chunk_id=f"{self._slugify(doc_name)}_sec_{section_num}_{start_id + chunk_idx}",
                doc_name=doc_name,
                doc_type=doc_type,
                doc_year=doc_year,
                section_number=section_num,
                section_title=f"{section_title} (part {chunk_idx + 1})" if section_title else f"Section {section_num} (part {chunk_idx + 1})",
                text=current_chunk,
                source_pages=source_pages,
                domain=primary_domain,
                keywords=keywords,
                cross_refs=cross_refs,
                jurisdiction=jurisdiction,
                source=source,
                chunk_type='section',
                has_hierarchy=True,
                secondary_domains=secondary_domains,
                legal_entities=legal_entities,
                dates=dates,
                authorities=authorities,
                is_continuation=True,
                is_amendment=False,
                amendment_action=None,
                target_section=None,
                merge_status='split',
                language=language
            )
            chunks.append(chunk)

        return chunks

    def _build_chunk(self, chunk_id: str, doc_name: str, doc_type: str, doc_year: Optional[int],
                     section_number: str, section_title: str, text: str, source_pages: List,
                     domain: str, keywords: List, cross_refs: List, jurisdiction: str,
                     source: str, chunk_type: str, has_hierarchy: bool,
                     secondary_domains: List[str], legal_entities: List,
                     dates: List, authorities: List, is_continuation: bool,
                     is_amendment: bool, amendment_action: Optional[str],
                     target_section: Optional[str], merge_status: Optional[str],
                     language: str) -> Dict:

        embedding_text = self._build_embedding_text(
            doc_name, domain, section_number, section_title, text, keywords
        )

        return {
            'chunk_id': chunk_id,
            'document': doc_name,
            'document_type': doc_type,
            'document_year': doc_year,
            'section_number': section_number,
            'section_title': section_title,
            'text': text,
            'embedding_text': embedding_text,
            'source_pages': source_pages,
            'domain': domain,
            'keywords': keywords,
            'cross_references': cross_refs,
            'language': language,
            'metadata': {
                'jurisdiction': jurisdiction,
                'source': source,
                'has_hierarchy': has_hierarchy,
                'secondary_domains': secondary_domains,
                'legal_entities': legal_entities,
                'dates': dates,
                'authorities': authorities,
                'is_continuation': is_continuation,
                'is_amendment': is_amendment,
                'amendment_action': amendment_action,
                'target_section': target_section,
                'merge_status': merge_status
            }
        }

    def _build_embedding_text(self, doc_name: str, domain: str, section_num: str,
                              section_title: str, text: str, keywords: List) -> str:
        parts = [
            f"Document: {doc_name}",
            f"Domain: {domain}",
            f"Section {section_num}: {section_title}" if section_title else f"Section {section_num}",
            "",
            text,
            "",
            f"Keywords: {', '.join(keywords)}" if keywords else ""
        ]
        return '\n'.join(parts)

    def _slugify(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '_', text)
        text = text.strip('_')
        return text[:50]


def print_chunk_summary(report: ChunkReport):
    print(f"\n{'='*60}")
    print(f"RAG CHUNK REPORT: {Path(report.file_path).name}")
    print(f"{'='*60}")
    print(f"Total chunks:           {report.total_chunks}")
    print(f"Chunks by type:         {report.chunks_by_type}")
    print(f"Chunks with hierarchy:  {report.chunks_with_hierarchy}")
    print(f"Avg chunk length:       {report.avg_chunk_length:.0f} chars")
    print(f"Max chunk length:       {report.max_chunk_length} chars")


def main():
    if len(sys.argv) < 2:
        print("Usage: python create_rag_chunks.py <input.json> [output.json]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(input_path.stem + '_RAG_CHUNKS.json')

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    creator = RAGChunkCreator()
    chunks, report = creator.create_chunks(input_path)

    print_chunk_summary(report)

    output_data = {
        'chunks': chunks,
        'metadata': {
            'total_chunks': report.total_chunks,
            'chunks_by_type': report.chunks_by_type,
            'avg_chunk_length': report.avg_chunk_length,
            'max_chunk_length': report.max_chunk_length
        }
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    with open(output_path.with_suffix('.rag_chunk_report.json'), 'w', encoding='utf-8') as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False, default=str)

    print(f"\nRAG chunks saved to: {output_path}")
    print(f"Chunk report saved to: {output_path.with_suffix('.rag_chunk_report.json')}")


if __name__ == '__main__':
    from typing import Tuple, List
    main()