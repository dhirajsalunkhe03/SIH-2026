#!/usr/bin/env python3
"""
Batch RAG Data Preparation
Process multiple extracted JSON files through RAG pipeline
"""

import json
from pathlib import Path
from typing import List, Dict
import logging
from datetime import datetime
from data_prep import RAGDataPipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BatchRAGPreparer:
    """Process multiple documents through RAG pipeline"""
    
    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pipeline = RAGDataPipeline(output_dir)
        self.results = []
    
    def find_json_files(self, pattern: str = "*.json") -> List[Path]:
        """Find all JSON files matching pattern"""
        files = list(self.input_dir.glob(pattern))
        # Exclude already processed RAG_READY files
        files = [f for f in files if 'RAG_READY' not in f.name]
        return sorted(files)
    
    def process_batch(self, files: List[Path]) -> Dict:
        """Process all files in batch"""
        print("\n" + "="*70)
        print(f"BATCH RAG PREPARATION - {len(files)} documents")
        print("="*70 + "\n")
        
        for i, file_path in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] Processing: {file_path.name}")
            print("-" * 70)
            
            try:
                result = self.pipeline.prepare(
                    str(file_path),
                    str(self.output_dir / f"{file_path.stem}_RAG_READY.json")
                )
                
                self.results.append({
                    'input': file_path.name,
                    'status': 'success',
                    'output': f"{file_path.stem}_RAG_READY.json",
                    'pages': len(result.get('pages', [])),
                    'sections': sum(len(p.get('sections', [])) for p in result.get('pages', [])),
                })
            
            except Exception as e:
                logger.error(f"Error processing {file_path.name}: {str(e)}")
                self.results.append({
                    'input': file_path.name,
                    'status': 'error',
                    'error': str(e)
                })
        
        return self._generate_report()
    
    def _generate_report(self) -> Dict:
        """Generate batch processing report"""
        successful = [r for r in self.results if r['status'] == 'success']
        failed = [r for r in self.results if r['status'] == 'error']
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_documents': len(self.results),
            'successful': len(successful),
            'failed': len(failed),
            'results': self.results,
            'total_pages': sum(r.get('pages', 0) for r in successful),
            'total_sections': sum(r.get('sections', 0) for r in successful),
        }
        
        # Save report
        report_path = self.output_dir / 'batch_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*70)
        print("BATCH PROCESSING COMPLETE")
        print("="*70)
        print(f"✓ Successful: {len(successful)}/{len(self.results)}")
        print(f"✗ Failed: {len(failed)}/{len(self.results)}")
        print(f"\nTotal Stats:")
        print(f"  Documents: {len(successful)}")
        print(f"  Pages: {report['total_pages']}")
        print(f"  Sections: {report['total_sections']}")
        print(f"\nReport saved: {report_path}")
        print("="*70 + "\n")
        
        return report


if __name__ == '__main__':
    import sys
    
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/home/dhiraj/Desktop/SIH/Datasets/BIO')
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('/home/dhiraj/Desktop/SIH/rag_pipeline/output')
    
    preparer = BatchRAGPreparer(input_dir, output_dir)
    json_files = preparer.find_json_files()
    
    if json_files:
        report = preparer.process_batch(json_files)
    else:
        logger.error(f"No JSON files found in {input_dir}")
