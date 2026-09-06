#!/usr/bin/env python3
"""
Discover all legal PDFs in the dataset directory and generate a manifest.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class PDFManifestEntry:
    file: str
    filename: str
    folder: str
    document_name: Optional[str] = None
    document_type: Optional[str] = None
    year: Optional[int] = None
    language: Optional[str] = None
    domain: Optional[str] = None
    size_bytes: int = 0
    discovered_at: str = ""


def discover_pdfs(root_dir: Path) -> List[PDFManifestEntry]:
    entries = []
    for pdf_path in root_dir.rglob("*.pdf"):
        if pdf_path.is_file():
            rel_path = pdf_path.relative_to(root_dir)
            folder = str(rel_path.parent) if rel_path.parent != Path(".") else ""
            stat = pdf_path.stat()
            
            entry = PDFManifestEntry(
                file=str(pdf_path),
                filename=pdf_path.name,
                folder=folder,
                size_bytes=stat.st_size,
                discovered_at=datetime.now().isoformat()
            )
            entries.append(entry)
    return entries


def main():
    root_dir = Path("/home/dhiraj/Desktop/SIH/Datasets")
    if not root_dir.exists():
        print(f"Error: Dataset root not found: {root_dir}")
        return 1
    
    entries = discover_pdfs(root_dir)
    
    manifest = {
        "discovered_at": datetime.now().isoformat(),
        "root_directory": str(root_dir),
        "total_pdfs": len(entries),
        "pdfs": [asdict(e) for e in entries]
    }
    
    output_path = Path("/home/dhiraj/Desktop/SIH/rag_pipeline/dataset_manifest.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"Discovered {len(entries)} PDFs")
    for e in entries:
        print(f"  {e.folder}/{e.filename} ({e.size_bytes:,} bytes)")
    
    print(f"\nManifest saved to: {output_path}")
    return 0


if __name__ == '__main__':
    exit(main())