#!/usr/bin/env python3
"""
Phase 2 Pipeline - Orchestrates the complete legal document processing pipeline.
Runs: inspect -> validate -> repair -> merge -> normalize -> canonicalize -> rag_chunks
"""

import json
import sys
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class PipelineStats:
    file_name: str
    pages_before: int
    pages_after: int
    sections_before_repair: int
    sections_after_repair: int
    sections_after_merge: int
    empty_sections_before: int
    empty_sections_after: int
    suspicious_pages_before: int
    suspicious_pages_after: int
    amendments_detected: int
    definitions_detected: int
    rag_chunks_created: int
    validation_errors: int
    repair_actions: int
    merge_actions: int
    status: str
    error: Optional[str] = None


class Phase2Pipeline:
    SCRIPTS_DIR = Path(__file__).parent
    OUTPUT_DIR = SCRIPTS_DIR / 'output'
    VALIDATED_DIR = OUTPUT_DIR / 'validated'
    CANONICAL_DIR = OUTPUT_DIR / 'canonical'
    RAG_CHUNKS_DIR = OUTPUT_DIR / 'rag_chunks'

    def __init__(self):
        self.VALIDATED_DIR.mkdir(parents=True, exist_ok=True)
        self.CANONICAL_DIR.mkdir(parents=True, exist_ok=True)
        self.RAG_CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def run_script(self, script_name: str, args: List[str]) -> subprocess.CompletedProcess:
        cmd = [sys.executable, str(self.SCRIPTS_DIR / script_name)] + args
        self.logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            self.logger.error(f"Script failed: {result.stderr}")
        return result

    def count_sections(self, file_path: Path) -> int:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            pages = data.get('pages', [])
            if not pages and 'document' in data:
                pages = [data]
            return sum(len(p.get('sections', [])) for p in pages)
        except Exception:
            return 0

    def count_pages(self, file_path: Path) -> int:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            pages = data.get('pages', [])
            if not pages and 'document' in data:
                pages = [data]
            return len(pages)
        except Exception:
            return 0

    def count_empty_sections(self, file_path: Path) -> int:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            pages = data.get('pages', [])
            if not pages and 'document' in data:
                pages = [data]
            count = 0
            for page in pages:
                for section in page.get('sections', []):
                    if not section.get('content', '').strip():
                        count += 1
            return count
        except Exception:
            return 0

    def process_file(self, input_file: Path) -> PipelineStats:
        file_name = input_file.name
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Processing: {file_name}")
        self.logger.info(f"{'='*60}")

        stats = PipelineStats(
            file_name=file_name,
            pages_before=0, pages_after=0,
            sections_before_repair=0, sections_after_repair=0,
            sections_after_merge=0,
            empty_sections_before=0, empty_sections_after=0,
            suspicious_pages_before=0, suspicious_pages_after=0,
            amendments_detected=0, definitions_detected=0,
            rag_chunks_created=0,
            validation_errors=0, repair_actions=0, merge_actions=0,
            status='started'
        )

        try:
            stats.pages_before = self.count_pages(input_file)
            stats.sections_before_repair = self.count_sections(input_file)
            stats.empty_sections_before = self.count_empty_sections(input_file)

            validated_file = self.VALIDATED_DIR / f"{input_file.stem}_VALIDATED.json"
            result = self.run_script('validate_extraction.py', [str(input_file), str(validated_file)])
            if result.returncode != 0:
                stats.validation_errors = 1

            repaired_file = self.VALIDATED_DIR / f"{input_file.stem}_REPAIRED.json"
            result = self.run_script('repair_extraction.py', [str(input_file), str(repaired_file)])
            if result.returncode == 0:
                stats.sections_after_repair = self.count_sections(repaired_file)
                stats.empty_sections_after = self.count_empty_sections(repaired_file)
                repair_report_file = repaired_file.with_suffix('.repair_report.json')
                if repair_report_file.exists():
                    with open(repair_report_file) as f:
                        repair_data = json.load(f)
                    stats.repair_actions = len(repair_data.get('actions', []))
                    stats.amendments_detected = repair_data.get('amendments_detected', 0)
            else:
                stats.status = 'repair_failed'
                stats.error = 'Repair script failed'
                return stats

            merged_file = self.VALIDATED_DIR / f"{input_file.stem}_MERGED.json"
            result = self.run_script('merge_sections.py', [str(repaired_file), str(merged_file)])
            if result.returncode == 0:
                stats.sections_after_merge = self.count_sections(merged_file)
                merge_report_file = merged_file.with_suffix('.merge_report.json')
                if merge_report_file.exists():
                    with open(merge_report_file) as f:
                        merge_data = json.load(f)
                    stats.merge_actions = merge_data.get('sections_merged', 0)
            else:
                stats.status = 'merge_failed'
                stats.error = 'Merge script failed'
                return stats

            normalized_file = self.CANONICAL_DIR / f"{input_file.stem}_NORMALIZED.json"
            result = self.run_script('legal_normalizer.py', [str(merged_file), str(normalized_file)])
            if result.returncode != 0:
                stats.status = 'normalize_failed'
                stats.error = 'Normalize script failed'
                return stats

            canonical_file = self.CANONICAL_DIR / f"{input_file.stem}_CANONICAL.json"
            result = self.run_script('canonicalize.py', [str(normalized_file), str(canonical_file)])
            if result.returncode != 0:
                stats.status = 'canonicalize_failed'
                stats.error = 'Canonicalize script failed'
                return stats

            rag_file = self.RAG_CHUNKS_DIR / f"{input_file.stem}_RAG_CHUNKS.json"
            result = self.run_script('create_rag_chunks.py', [str(canonical_file), str(rag_file)])
            if result.returncode == 0:
                with open(rag_file) as f:
                    rag_data = json.load(f)
                stats.rag_chunks_created = rag_data.get('metadata', {}).get('total_chunks', 0)
            else:
                stats.status = 'rag_failed'
                stats.error = 'RAG chunks script failed'
                return stats

            stats.pages_after = self.count_pages(canonical_file)
            stats.status = 'completed'

        except Exception as e:
            stats.status = 'error'
            stats.error = str(e)
            self.logger.exception(f"Error processing {file_name}")

        return stats

    def run(self, input_dir: Optional[Path] = None) -> List[PipelineStats]:
        if input_dir is None:
            input_dir = self.OUTPUT_DIR

        json_files = list(input_dir.glob('*_RAG_READY.json'))
        if not json_files:
            json_files = list(input_dir.glob('*.json'))

        self.logger.info(f"Found {len(json_files)} JSON files to process")

        all_stats = []
        for json_file in json_files:
            if 'VALIDATED' in json_file.name or 'REPAIRED' in json_file.name or 'MERGED' in json_file.name or 'NORMALIZED' in json_file.name or 'CANONICAL' in json_file.name or 'RAG_CHUNKS' in json_file.name:
                continue
            stats = self.process_file(json_file)
            all_stats.append(stats)

        self._print_summary(all_stats)
        self._save_summary(all_stats)

        return all_stats

    def _print_summary(self, all_stats: List[PipelineStats]):
        print(f"\n{'='*60}")
        print(f"PHASE 2 COMPLETE")
        print(f"{'='*60}")

        completed = [s for s in all_stats if s.status == 'completed']
        failed = [s for s in all_stats if s.status != 'completed']

        print(f"\nDocuments processed:     {len(completed)}")
        print(f"Failed documents:        {len(failed)}")

        if completed:
            total_pages = sum(s.pages_after for s in completed)
            total_sections_before = sum(s.sections_before_repair for s in completed)
            total_sections_after = sum(s.sections_after_merge for s in completed)
            total_empty_before = sum(s.empty_sections_before for s in completed)
            total_empty_after = sum(s.empty_sections_after for s in completed)
            total_amendments = sum(s.amendments_detected for s in completed)
            total_definitions = sum(s.definitions_detected for s in completed)
            total_chunks = sum(s.rag_chunks_created for s in completed)

            print(f"Pages processed:         {total_pages}")
            print(f"Sections before repair:  {total_sections_before}")
            print(f"Sections after repair:   {sum(s.sections_after_repair for s in completed)}")
            print(f"Sections after merge:    {total_sections_after}")
            print(f"Empty sections before:   {total_empty_before}")
            print(f"Empty sections after:    {total_empty_after}")
            print(f"Amendments detected:     {total_amendments}")
            print(f"Definitions detected:    {total_definitions}")
            print(f"RAG chunks created:      {total_chunks}")

        if failed:
            print(f"\nFailed documents:")
            for s in failed:
                print(f"  {s.file_name}: {s.error}")

    def _save_summary(self, all_stats: List[PipelineStats]):
        summary_file = self.OUTPUT_DIR / 'phase2_summary.json'
        with open(summary_file, 'w') as f:
            json.dump([asdict(s) for s in all_stats], f, indent=2, default=str)
        self.logger.info(f"Pipeline summary saved to: {summary_file}")


def main():
    if len(sys.argv) > 1:
        input_dir = Path(sys.argv[1])
    else:
        input_dir = None

    pipeline = Phase2Pipeline()
    pipeline.run(input_dir)


if __name__ == '__main__':
    main()