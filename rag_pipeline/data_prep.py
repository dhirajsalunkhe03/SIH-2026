#!/usr/bin/env python3
"""
RAG Data Preparation Pipeline
Converts raw extracted JSON to RAG-ready normalized JSON

Pipeline steps:
1. OCR text cleaning & correction
2. JSON validation & schema compliance
3. Section continuation merging
4. Legal normalization & standardization
5. Output RAG-ready JSON
"""

import json
import re
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CleaningStats:
    """Track cleaning operations"""
    typos_fixed: int = 0
    ocr_artifacts_removed: int = 0
    whitespace_normalized: int = 0
    special_chars_fixed: int = 0


class OCRTextCleaner:
    """
    Clean and correct OCR errors from raw text
    No model-based corrections - only rule-based patterns
    """
    
    def __init__(self):
        self.stats = CleaningStats()
        self.ocr_patterns = self._build_ocr_patterns()
    
    def _build_ocr_patterns(self) -> List[Tuple[re.Pattern, str, str]]:
        """
        Define common OCR misrecognition patterns
        (pattern, replacement_pattern, description)
        """
        return [
            # l/1 confusion
            (re.compile(r'\bl(?=aw|etter|egal|ength|ink)'), '1', 'l→1'),
            (re.compile(r'(^|\s|\()l(?=[A-Z])'), r'\1L', 'initial l→L'),
            
            # O/0 confusion
            (re.compile(r'(\d)O(?=\d)'), r'\g<1>0', 'O→0 in numbers'),
            (re.compile(r'\b0(?=ver|ther|wn)'), 'O', '0→O in words'),
            
            # rn/m confusion
            (re.compile(r'rn(?=\s|[aeiou])'), 'm', 'rn→m'),
            
            # Common OCR artifacts
            (re.compile(r'([a-z])\|([a-z])'), r'\1i\2', '|→i'),
            (re.compile(r'([a-z])1([a-z])'), r'\1l\2', '1→l in words'),
            
            # Multiple spaces
            (re.compile(r'\s{2,}'), ' ', 'multiple spaces→single'),
            
            # Line artifacts
            (re.compile(r'[\u2010-\u2015]{2,}'), '—', 'line artifacts'),
            (re.compile(r'_{2,}'), '—', 'underscores→dash'),
            
            # Garbled characters (preserve intentional special chars)
            (re.compile(r'[^\w\s\-:;\.,\(\)\[\]"\'\—–]'), '', 'remove invalid chars'),
        ]
    
    def clean_text(self, text: str) -> str:
        """Apply all cleaning patterns"""
        if not text or not isinstance(text, str):
            return text
        
        cleaned = text
        
        # Apply OCR pattern corrections
        for pattern, replacement, desc in self.ocr_patterns:
            original = cleaned
            cleaned = pattern.sub(replacement, cleaned)
            if cleaned != original:
                self.stats.ocr_artifacts_removed += 1
        
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        self.stats.whitespace_normalized += 1
        
        # Fix common spacing issues around punctuation
        cleaned = re.sub(r'\s+([.,;:!?\)])', r'\1', cleaned)  # space before punctuation
        cleaned = re.sub(r'([\(\[])\s+', r'\1', cleaned)      # space after opening paren
        
        return cleaned
    
    def clean_document(self, doc: Dict) -> Dict:
        """Recursively clean all text in document"""
        if isinstance(doc, dict):
            return {k: self.clean_document(v) for k, v in doc.items()}
        elif isinstance(doc, list):
            return [self.clean_document(item) for item in doc]
        elif isinstance(doc, str):
            return self.clean_text(doc)
        return doc


class JSONValidator:
    """Validate and fix JSON schema compliance"""
    
    # Required fields per object type
    REQUIRED_DOCUMENT = {'document', 'pages'}
    REQUIRED_PAGE = {'page_number', 'page_type', 'raw_text'}
    REQUIRED_SECTION = {'section_number', 'content'}
    
    VALID_PAGE_TYPES = {
        'preamble', 'toc', 'table_of_contents', 'definition', 
        'schedule', 'form', 'content', 'appendix', 'index'
    }
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_document(self, doc: Dict) -> Tuple[bool, List[str]]:
        """Validate document structure"""
        self.errors = []
        self.warnings = []
        
        # Check required fields
        if 'document' not in doc:
            self.errors.append("Missing 'document' key")
            return False, self.errors
        
        if 'pages' not in doc or not isinstance(doc['pages'], list):
            self.errors.append("Missing or invalid 'pages' array")
            return False, self.errors
        
        # Validate each page
        for i, page in enumerate(doc['pages']):
            self._validate_page(page, i)
        
        return len(self.errors) == 0, self.errors + self.warnings
    
    def _validate_page(self, page: Dict, index: int):
        """Validate individual page"""
        page_id = f"Page {index + 1}"
        
        # Check required fields
        for field in self.REQUIRED_PAGE:
            if field not in page:
                self.warnings.append(f"{page_id}: Missing '{field}'")
                page[field] = None if field != 'raw_text' else ""
        
        # Validate page_type
        if page.get('page_type') and page['page_type'] not in self.VALID_PAGE_TYPES:
            self.warnings.append(f"{page_id}: Unknown page_type '{page['page_type']}'")
        
        # Ensure arrays exist
        for field in ['sections', 'rules', 'definitions', 'references', 'tables', 'forms']:
            if field not in page:
                page[field] = []
            elif not isinstance(page[field], list):
                self.warnings.append(f"{page_id}: '{field}' is not an array")
                page[field] = []
        
        # Validate sections
        if page.get('sections'):
            for j, section in enumerate(page['sections']):
                self._validate_section(section, f"{page_id}.Section {j + 1}")
    
    def _validate_section(self, section: Dict, context: str):
        """Validate section object"""
        # Ensure required fields
        if 'section_number' not in section:
            self.warnings.append(f"{context}: Missing section_number")
            section['section_number'] = ""
        
        if 'content' not in section:
            section['content'] = ""
        
        # Ensure boolean flags
        if 'is_continuation' not in section:
            section['is_continuation'] = False
        
        # Add missing optional fields
        for field in ['section_title', 'subsections']:
            if field not in section:
                section[field] = "" if field == 'section_title' else []
    
    def fix_document(self, doc: Dict) -> Dict:
        """Attempt to fix common issues"""
        if 'document' not in doc:
            doc['document'] = {}
        
        if 'pages' not in doc or not isinstance(doc['pages'], list):
            doc['pages'] = []
        
        # Ensure minimum page structure
        for page in doc['pages']:
            for field in ['sections', 'rules', 'definitions', 'references', 'tables', 'forms']:
                if field not in page:
                    page[field] = []
        
        return doc


class SectionContinuationMerger:
    """Merge multi-page sections marked with is_continuation flag"""
    
    def __init__(self):
        self.merges_performed = 0
    
    def merge_sections(self, doc: Dict) -> Dict:
        """Merge continuation sections across pages"""
        pages = doc.get('pages', [])
        
        # Build section map across all pages
        section_map = {}  # section_number -> [page_indices, content_parts]
        
        for page_idx, page in enumerate(pages):
            for section_idx, section in enumerate(page.get('sections', [])):
                sec_num = section.get('section_number', '')
                if not sec_num:
                    continue
                
                if sec_num not in section_map:
                    section_map[sec_num] = {
                        'pages': [],
                        'parts': [],
                        'full_title': section.get('section_title', ''),
                        'is_continuation': section.get('is_continuation', False)
                    }
                
                section_map[sec_num]['pages'].append((page_idx, section_idx))
                section_map[sec_num]['parts'].append(section.get('content', ''))
        
        # Merge content for sections spanning multiple pages
        merged_count = 0
        for sec_num, info in section_map.items():
            if len(info['pages']) > 1:
                # Mark first occurrence as primary
                first_page_idx, first_section_idx = info['pages'][0]
                merged_content = ' '.join(info['parts'])
                
                doc['pages'][first_page_idx]['sections'][first_section_idx]['content'] = merged_content
                doc['pages'][first_page_idx]['sections'][first_section_idx]['is_continuation'] = False
                
                # Remove subsequent occurrences
                for page_idx, section_idx in info['pages'][1:]:
                    doc['pages'][page_idx]['sections'][section_idx]['content'] = ''
                    doc['pages'][page_idx]['sections'][section_idx]['is_continuation'] = True
                
                merged_count += 1
        
        self.merges_performed = merged_count
        logger.info(f"Merged {merged_count} multi-page sections")
        return doc


class LegalNormalizer:
    """Apply legal document normalization rules"""
    
    def __init__(self):
        self.normalizations_applied = 0
    
    def normalize_document(self, doc: Dict) -> Dict:
        """Apply all normalization rules"""
        # Normalize section numbers
        doc = self._normalize_section_numbers(doc)
        
        # Standardize legal references
        doc = self._standardize_references(doc)
        
        # Clean legal terminology
        doc = self._normalize_terminology(doc)
        
        # Add document metadata
        doc = self._add_metadata(doc)
        
        return doc
    
    def _normalize_section_numbers(self, doc: Dict) -> Dict:
        """Standardize section number format"""
        section_pattern = re.compile(r'^[Ss]ection\s+(\d+[\w\.\-]*)\b')
        
        for page in doc.get('pages', []):
            for section in page.get('sections', []):
                sec_num = section.get('section_number', '').strip()
                
                # Extract numeric section from text if needed
                if not sec_num and section.get('content'):
                    match = section_pattern.search(section['content'])
                    if match:
                        sec_num = match.group(1)
                        section['section_number'] = sec_num
                
                # Normalize format: "Section 5" → "5"
                if sec_num.lower().startswith('section'):
                    sec_num = re.sub(r'^[Ss]ection\s+', '', sec_num)
                    section['section_number'] = sec_num
                
                self.normalizations_applied += 1
        
        return doc
    
    def _standardize_references(self, doc: Dict) -> Dict:
        """Standardize references to Acts, Sections, etc."""
        # Map common abbreviations to full forms
        abbrev_map = {
            r'\bAct[\s,]': 'Act,',
            r'\bSec\.?\s*(\d+)': 'Section \1',
            r'\bSub[\-\s]+sec\.?\s*\((\d+[a-z]?)\)': 'Sub-section (\1)',
            r'\bClause\s*\(([a-z])\)': 'Clause (\1)',
        }
        
        for page in doc.get('pages', []):
            for section in page.get('sections', []):
                content = section.get('content', '')
                for pattern, replacement in abbrev_map.items():
                    content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
                section['content'] = content
        
        return doc
    
    def _normalize_terminology(self, doc: Dict) -> Dict:
        """Normalize legal terminology for consistency"""
        term_map = {
            'biological resources': 'biological resource',
            'biodiversity': 'biodiversity',
            'traditional knowledge': 'traditional knowledge',
        }
        
        for page in doc.get('pages', []):
            for section in page.get('sections', []):
                content = section.get('content', '')
                for old_term, new_term in term_map.items():
                    pattern = re.compile(re.escape(old_term), re.IGNORECASE)
                    content = pattern.sub(new_term, content)
                section['content'] = content
        
        return doc
    
    def _add_metadata(self, doc: Dict) -> Dict:
        """Add processing metadata"""
        if 'metadata' not in doc:
            doc['metadata'] = {}
        
        doc['metadata']['processing_stage'] = 'RAG-ready'
        doc['metadata']['sections_merged'] = True
        doc['metadata']['normalized'] = True
        
        # Add text statistics
        total_chars = sum(
            len(s.get('content', ''))
            for p in doc.get('pages', [])
            for s in p.get('sections', [])
        )
        doc['metadata']['total_characters'] = total_chars
        
        return doc


class RAGDataPipeline:
    """Main orchestrator for RAG data preparation"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.cleaner = OCRTextCleaner()
        self.validator = JSONValidator()
        self.merger = SectionContinuationMerger()
        self.normalizer = LegalNormalizer()
        self.output_dir = output_dir or Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare(self, input_json_path: str, output_json_path: Optional[str] = None) -> Dict:
        """
        Execute full RAG data preparation pipeline
        
        Args:
            input_json_path: Path to raw extracted JSON
            output_json_path: Optional custom output path
        
        Returns:
            Prepared document dict
        """
        logger.info(f"Starting RAG preparation pipeline: {input_json_path}")
        
        # Load raw JSON
        with open(input_json_path, 'r', encoding='utf-8') as f:
            doc = json.load(f)
        
        # Step 1: Clean OCR text
        logger.info("Step 1/5: Cleaning OCR text...")
        doc = self.cleaner.clean_document(doc)
        logger.info(f"  → Fixed {self.cleaner.stats.ocr_artifacts_removed} OCR artifacts")
        
        # Step 2: Validate JSON schema
        logger.info("Step 2/5: Validating JSON schema...")
        is_valid, messages = self.validator.validate_document(doc)
        if not is_valid:
            logger.warning(f"  → Fixing {len(messages)} schema issues...")
            doc = self.validator.fix_document(doc)
        else:
            logger.info("  → Document schema valid ✓")
        
        # Step 3: Merge continuation sections
        logger.info("Step 3/5: Merging continuation sections...")
        doc = self.merger.merge_sections(doc)
        logger.info(f"  → Merged {self.merger.merges_performed} multi-page sections")
        
        # Step 4: Normalize legal content
        logger.info("Step 4/5: Normalizing legal terminology...")
        doc = self.normalizer.normalize_document(doc)
        logger.info(f"  → Applied {self.normalizer.normalizations_applied} normalizations")
        
        # Step 5: Save RAG-ready JSON
        logger.info("Step 5/5: Saving RAG-ready JSON...")
        if output_json_path is None:
            input_path = Path(input_json_path)
            output_json_path = str(
                self.output_dir / f"{input_path.stem}_RAG_READY.json"
            )
        
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ RAG-ready JSON saved: {output_json_path}")
        
        # Print summary
        self._print_summary(doc, output_json_path)
        
        return doc
    
    def _print_summary(self, doc: Dict, output_path: str):
        """Print processing summary"""
        pages = doc.get('pages', [])
        total_sections = sum(len(p.get('sections', [])) for p in pages)
        total_chars = sum(
            len(s.get('content', ''))
            for p in pages
            for s in p.get('sections', [])
        )
        
        print("\n" + "="*70)
        print("RAG DATA PREPARATION SUMMARY")
        print("="*70)
        print(f"Input Document: {doc.get('document', {}).get('document_name', 'Unknown')}")
        print(f"Output File: {output_path}")
        print(f"\nStatistics:")
        print(f"  Pages processed: {len(pages)}")
        print(f"  Total sections: {total_sections}")
        print(f"  Total characters: {total_chars:,}")
        print(f"\nProcessing Steps:")
        print(f"  OCR artifacts fixed: {self.cleaner.stats.ocr_artifacts_removed}")
        print(f"  Sections merged: {self.merger.merges_performed}")
        print(f"  Normalizations applied: {self.normalizer.normalizations_applied}")
        print(f"  Schema warnings: {len(self.validator.warnings)}")
        print("\nStatus: ✓ RAG-READY")
        print("="*70 + "\n")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 data_prep.py <input_json> [output_json]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    pipeline = RAGDataPipeline()
    pipeline.prepare(input_file, output_file)
