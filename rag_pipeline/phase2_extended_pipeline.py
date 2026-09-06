#!/usr/bin/env python3
"""
Extended Phase 2 Pipeline - Processes all legal documents including new Acts and Rules.
Supports multilingual (English + Marathi) documents.
"""

import json
import subprocess
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class PipelineStats:
    file_name: str
    document_name: str
    document_type: str
    domain: str
    language: str
    pages: int
    sections_before: int
    sections_after_repair: int
    sections_after_merge: int
    rules_before: int
    rules_after_merge: int
    schedules: int
    forms: int
    empty_provisions_before: int
    empty_provisions_after: int
    rag_chunks: int
    extraction_quality: str  # GOOD / WARNING / ERROR
    repair_actions: int
    merge_actions: int
    warnings: List[str]
    status: str
    error: Optional[str] = None


class ExtendedPhase2Pipeline:
    SCRIPTS_DIR = Path(__file__).parent
    OUTPUT_DIR = SCRIPTS_DIR / 'output'
    VALIDATED_DIR = OUTPUT_DIR / 'validated'
    CANONICAL_DIR = OUTPUT_DIR / 'canonical'
    RAG_CHUNKS_DIR = OUTPUT_DIR / 'rag_chunks'
    EMBEDDINGS_DIR = OUTPUT_DIR / 'embeddings'
    
    EXTRACTED_DIR = SCRIPTS_DIR  # Where _EXTRACTED.json files are

    def __init__(self):
        for d in [self.VALIDATED_DIR, self.CANONICAL_DIR, self.RAG_CHUNKS_DIR, self.EMBEDDINGS_DIR]:
            d.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def run_script(self, script_name: str, args: List[str]) -> subprocess.CompletedProcess:
        cmd = [sys.executable, str(self.SCRIPTS_DIR / script_name)] + args
        self.logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            self.logger.error(f"Script failed: {result.stderr}")
        return result

    def count_provisions(self, file_path: Path) -> Dict[str, int]:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            pages = data.get('pages', [])
            if not pages and 'document' in data:
                pages = [data]
            
            doc_meta = data.get('document', {})
            doc_type = doc_meta.get('document_type', 'Other')
            is_act = doc_type in ('Act', 'Amendment Act')
            is_rules = doc_type == 'Rules'
            
            total_sections = 0
            total_rules = 0
            total_schedules = 0
            total_forms = 0
            empty_sections = 0
            empty_rules = 0
            
            for page in pages:
                if is_act:
                    for section in page.get('sections', []):
                        total_sections += 1
                        if not section.get('content', '').strip():
                            empty_sections += 1
                elif is_rules:
                    for rule in page.get('rules', []):
                        total_rules += 1
                        if not rule.get('content', '').strip():
                            empty_rules += 1
                else:
                    # Unknown type - count both
                    for section in page.get('sections', []):
                        total_sections += 1
                        if not section.get('content', '').strip():
                            empty_sections += 1
                    for rule in page.get('rules', []):
                        total_rules += 1
                        if not rule.get('content', '').strip():
                            empty_rules += 1
                total_schedules += len(page.get('schedules', []))
                total_forms += len(page.get('forms', []))
            
            return {
                'sections': total_sections,
                'rules': total_rules,
                'schedules': total_schedules,
                'forms': total_forms,
                'empty_sections': empty_sections,
                'empty_rules': empty_rules,
                'empty_provisions': empty_sections + empty_rules
            }
        except Exception:
            return {'sections': 0, 'rules': 0, 'schedules': 0, 'forms': 0, 'empty_provisions': 0}

    def get_document_info(self, file_path: Path) -> Dict:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            doc = data.get('document', {})
            pages = data.get('pages', [])
            return {
                'document_name': doc.get('document_name', ''),
                'document_type': doc.get('document_type', ''),
                'domain': doc.get('domain', ''),
                'language': doc.get('language', ''),
                'total_pages': len(pages)
            }
        except Exception:
            return {}

    def assess_extraction_quality(self, counts: Dict, page_count: int, doc_type: str) -> str:
        is_act = doc_type in ('Act', 'Amendment Act')
        is_rules = doc_type == 'Rules'
        
        if is_act:
            total_provisions = counts['sections']
            empty_provisions = counts['empty_sections']
        elif is_rules:
            total_provisions = counts['rules']
            empty_provisions = counts['empty_rules']
        else:
            total_provisions = counts['sections'] + counts['rules']
            empty_provisions = counts['empty_provisions']
        
        if page_count == 0:
            return 'ERROR'
        if total_provisions == 0:
            return 'ERROR'
        if empty_provisions / max(total_provisions, 1) > 0.5:
            return 'WARNING'
        if total_provisions < page_count * 0.3:
            return 'WARNING'
        return 'GOOD'

    def process_document(self, extracted_file: Path) -> PipelineStats:
        file_name = extracted_file.name
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Processing: {file_name}")
        self.logger.info(f"{'='*60}")

        doc_info = self.get_document_info(extracted_file)
        doc_name = doc_info.get('document_name', file_name)
        doc_type = doc_info.get('document_type', 'Other')
        domain = doc_info.get('domain', 'General Legal')
        language = doc_info.get('language', 'unknown')
        page_count = doc_info.get('total_pages', 0)

        counts_before = self.count_provisions(extracted_file)
        
        stats = PipelineStats(
            file_name=file_name,
            document_name=doc_name,
            document_type=doc_type,
            domain=domain,
            language=language,
            pages=page_count,
            sections_before=counts_before['sections'],
            sections_after_repair=0,
            sections_after_merge=0,
            rules_before=counts_before['rules'],
            rules_after_merge=0,
            schedules=counts_before['schedules'],
            forms=counts_before['forms'],
            empty_provisions_before=counts_before['empty_provisions'],
            empty_provisions_after=0,
            rag_chunks=0,
            extraction_quality='UNKNOWN',
            repair_actions=0,
            merge_actions=0,
            warnings=[],
            status='started'
        )

        try:
            # Step 1: Validate
            validated_file = self.VALIDATED_DIR / f"{extracted_file.stem}_VALIDATED.json"
            result = self.run_script('validate_extraction.py', [str(extracted_file), str(validated_file)])
            if result.returncode != 0:
                stats.warnings.append(f"Validation failed: {result.stderr[:200]}")

            # Step 2: Repair
            repaired_file = self.VALIDATED_DIR / f"{extracted_file.stem}_REPAIRED.json"
            result = self.run_script('repair_extraction.py', [str(extracted_file), str(repaired_file)])
            if result.returncode == 0:
                counts_repaired = self.count_provisions(repaired_file)
                stats.sections_after_repair = counts_repaired['sections']
                stats.rules_after_merge = counts_repaired['rules']
                
                repair_report_file = repaired_file.with_suffix('.repair_report.json')
                if repair_report_file.exists():
                    with open(repair_report_file) as f:
                        repair_data = json.load(f)
                    stats.repair_actions = len(repair_data.get('actions', []))
            else:
                stats.status = 'repair_failed'
                stats.error = f'Repair failed: {result.stderr[:200]}'
                return stats

            # Step 3: Merge
            merged_file = self.VALIDATED_DIR / f"{extracted_file.stem}_MERGED.json"
            result = self.run_script('merge_sections.py', [str(repaired_file), str(merged_file)])
            if result.returncode == 0:
                counts_merged = self.count_provisions(merged_file)
                stats.sections_after_merge = counts_merged['sections']
                stats.rules_after_merge = counts_merged['rules']
                stats.schedules = counts_merged['schedules']
                stats.forms = counts_merged['forms']
                stats.empty_provisions_after = counts_merged['empty_provisions']
                
                merge_report_file = merged_file.with_suffix('.merge_report.json')
                if merge_report_file.exists():
                    with open(merge_report_file) as f:
                        merge_data = json.load(f)
                    stats.merge_actions = merge_data.get('sections_merged', 0)
            else:
                stats.status = 'merge_failed'
                stats.error = f'Merge failed: {result.stderr[:200]}'
                return stats

            # Step 4: Normalize
            normalized_file = self.CANONICAL_DIR / f"{extracted_file.stem}_NORMALIZED.json"
            result = self.run_script('legal_normalizer.py', [str(merged_file), str(normalized_file)])
            if result.returncode != 0:
                stats.status = 'normalize_failed'
                stats.error = f'Normalize failed: {result.stderr[:200]}'
                return stats

            # Step 5: Canonicalize
            canonical_file = self.CANONICAL_DIR / f"{extracted_file.stem}_CANONICAL.json"
            result = self.run_script('canonicalize.py', [str(normalized_file), str(canonical_file)])
            if result.returncode != 0:
                stats.status = 'canonicalize_failed'
                stats.error = f'Canonicalize failed: {result.stderr[:200]}'
                return stats

            # Step 6: Create RAG Chunks
            rag_file = self.RAG_CHUNKS_DIR / f"{extracted_file.stem}_RAG_CHUNKS.json"
            result = self.run_script('create_rag_chunks.py', [str(canonical_file), str(rag_file)])
            if result.returncode == 0:
                with open(rag_file) as f:
                    rag_data = json.load(f)
                stats.rag_chunks = rag_data.get('metadata', {}).get('total_chunks', 0)
            else:
                stats.status = 'rag_failed'
                stats.error = f'RAG chunks failed: {result.stderr[:200]}'
                return stats

            # Assess quality using merged file (has proper sections/rules structure)
            merged_file = self.VALIDATED_DIR / f"{extracted_file.stem}_MERGED.json"
            final_counts = self.count_provisions(merged_file)
            stats.extraction_quality = self.assess_extraction_quality(final_counts, page_count, doc_type)
            
            if stats.extraction_quality == 'WARNING':
                stats.warnings.append('High empty provision ratio or low provision density')
            elif stats.extraction_quality == 'ERROR':
                stats.warnings.append('Critical extraction issues detected')

            stats.status = 'completed'

        except Exception as e:
            stats.status = 'error'
            stats.error = str(e)
            self.logger.exception(f"Error processing {file_name}")

        return stats

    def run(self, extracted_files: List[Path] = None) -> List[PipelineStats]:
        if extracted_files is None:
            # Find all _EXTRACTED.json files
            extracted_files = list(self.EXTRACTED_DIR.glob('*_EXTRACTED.json'))
            # Exclude already processed ones
            extracted_files = [f for f in extracted_files 
                             if not any(x in f.name for x in ['_REPAIRED', '_MERGED', '_NORMALIZED', '_CANONICAL', '_RAG_CHUNKS', '_VALIDATED'])]

        self.logger.info(f"Found {len(extracted_files)} extracted documents to process")

        all_stats = []
        for extracted_file in extracted_files:
            stats = self.process_document(extracted_file)
            all_stats.append(stats)

        self._print_summary(all_stats)
        self._save_report(all_stats)

        return all_stats

    def _print_summary(self, all_stats: List[PipelineStats]):
        print(f"\n{'='*70}")
        print(f"EXTENDED LEGAL CORPUS COMPLETE")
        print(f"{'='*70}")

        completed = [s for s in all_stats if s.status == 'completed']
        failed = [s for s in all_stats if s.status != 'completed']

        print(f"\nPDFs discovered:           {len(all_stats)}")
        print(f"Documents processed:       {len(completed)}")
        print(f"Failed documents:          {len(failed)}")

        if completed:
            total_pages = sum(s.pages for s in completed)
            total_sections = sum(s.sections_after_merge for s in completed)
            total_rules = sum(s.rules_after_merge for s in completed)
            total_schedules = sum(s.schedules for s in completed)
            total_forms = sum(s.forms for s in completed)
            total_chunks = sum(s.rag_chunks for s in completed)
            total_empty_before = sum(s.empty_provisions_before for s in completed)
            total_empty_after = sum(s.empty_provisions_after for s in completed)
            total_repairs = sum(s.repair_actions for s in completed)
            total_merges = sum(s.merge_actions for s in completed)
            
            en_docs = sum(1 for s in completed if s.language == 'en')
            mr_docs = sum(1 for s in completed if s.language == 'mr')
            mixed_docs = sum(1 for s in completed if s.language == 'mixed')
            
            acts = sum(1 for s in completed if s.document_type == 'Act')
            rules_docs = sum(1 for s in completed if s.document_type == 'Rules')
            amendment_acts = sum(1 for s in completed if s.document_type == 'Amendment Act')

            print(f"Total pages:               {total_pages}")
            print(f"Acts:                      {acts}")
            print(f"Rules:                     {rules_docs}")
            print(f"Amendment Acts:            {amendment_acts}")
            print(f"English documents:         {en_docs}")
            print(f"Marathi documents:         {mr_docs}")
            print(f"Mixed documents:           {mixed_docs}")
            print(f"Total sections:            {total_sections}")
            print(f"Total rules:               {total_rules}")
            print(f"Total schedules:           {total_schedules}")
            print(f"Total forms:               {total_forms}")
            print(f"Total RAG chunks:          {total_chunks}")
            print(f"Empty provisions before:   {total_empty_before}")
            print(f"Empty provisions after:    {total_empty_after}")
            print(f"Repair operations:         {total_repairs}")
            print(f"Section/rule merges:       {total_merges}")

            quality_counts = {}
            for s in completed:
                quality_counts[s.extraction_quality] = quality_counts.get(s.extraction_quality, 0) + 1
            print(f"\nExtraction quality:")
            for q, c in quality_counts.items():
                print(f"  {q}: {c}")

        if failed:
            print(f"\nFailed documents:")
            for s in failed:
                print(f"  {s.file_name}: {s.error}")

    def _save_report(self, all_stats: List[PipelineStats]):
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_documents': len(all_stats),
                'completed': len([s for s in all_stats if s.status == 'completed']),
                'failed': len([s for s in all_stats if s.status != 'completed']),
            },
            'documents': [asdict(s) for s in all_stats]
        }
        
        report_file = self.OUTPUT_DIR / 'EXTENDED_DATASET_REPORT.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"\nExtended dataset report saved to: {report_file}")


def main():
    if len(sys.argv) > 1:
        extracted_dir = Path(sys.argv[1])
        extracted_files = list(extracted_dir.glob('*_EXTRACTED.json'))
    else:
        extracted_files = None

    pipeline = ExtendedPhase2Pipeline()
    pipeline.run(extracted_files)


if __name__ == '__main__':
    main()