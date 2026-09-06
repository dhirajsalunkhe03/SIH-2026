#!/usr/bin/env python3
"""
Main document extraction script.
Processes PDF documents page by page and converts them to structured JSON.
"""

import logging
import argparse
from pathlib import Path
from typing import Optional
import sys

from extractor import PDFProcessor, OCRHandler, JSONFormatter
from extractor.config import DocumentType, OCR_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DocumentExtractor:
    """Main document extraction orchestrator."""
    
    def __init__(self, pdf_path: str, output_path: Optional[str] = None):
        """
        Initialize document extractor.
        
        Args:
            pdf_path: Path to PDF file
            output_path: Path for output JSON file
        """
        self.pdf_path = pdf_path
        self.output_path = output_path or str(Path(pdf_path).with_suffix('.json'))
        
        # Initialize components
        self.ocr_handler = OCRHandler(OCR_CONFIG)
        self.pdf_processor = PDFProcessor(self.ocr_handler)
        self.json_formatter = JSONFormatter()
        
        # State tracking
        self.previous_page_text = ""
        self.current_section = None
    
    def extract_document(self) -> bool:
        """
        Extract all pages from PDF and convert to JSON.
        
        Returns:
            True if successful, False otherwise
        """
        # Validate PDF file
        if not Path(self.pdf_path).exists():
            logger.error(f"PDF file not found: {self.pdf_path}")
            return False
        
        # Open PDF
        pdf = self.pdf_processor.open_pdf(self.pdf_path)
        if not pdf:
            return False
        
        total_pages = self.pdf_processor.get_total_pages(pdf)
        doc_name = Path(self.pdf_path).stem
        
        # Initialize document
        self.json_formatter.create_document(
            doc_name=doc_name,
            doc_type="Other",  # Can be enhanced to auto-detect
            total_pages=total_pages
        )
        
        logger.info(f"Starting extraction of {total_pages} pages...")
        
        # Process each page
        for page_num in range(total_pages):
            if not self._process_page(pdf, page_num, total_pages):
                logger.warning(f"Failed to process page {page_num + 1}")
                continue
        
        # Validate and save
        if not self.json_formatter.validate_json():
            logger.error("JSON validation failed")
            return False
        
        if not self.json_formatter.to_file(self.output_path):
            logger.error(f"Failed to write output to {self.output_path}")
            return False
        
        logger.info(f"Extraction complete. Output saved to {self.output_path}")
        return True
    
    def _process_page(self, pdf, page_num: int, total_pages: int) -> bool:
        """
        Process a single PDF page.
        
        Args:
            pdf: PdfReader object
            page_num: Page number (0-indexed)
            total_pages: Total pages in document
            
        Returns:
            True if successful
        """
        try:
            # Extract text
            text = self.pdf_processor.get_page_text(pdf, self.pdf_path, page_num)
            if not text:
                logger.warning(f"No text extracted from page {page_num + 1}")
                text = ""
            
            # Detect page type
            page_type = self.pdf_processor.detect_page_type(text, page_num + 1, total_pages)
            
            # Detect continuation
            is_continuation = self.pdf_processor.detect_continuation(
                text, self.previous_page_text, self.current_section
            )
            
            # Create page
            page = self.json_formatter.create_page(
                page_number=page_num + 1,
                page_type=page_type,
                title=None,
                chapter=None
            )
            
            # Extract structure
            structure = self.pdf_processor.extract_page_structure(text)
            
            # Add sections
            for section in structure['sections']:
                section_obj = self.json_formatter.create_section(
                    section_number=section['number'],
                    section_title=section['title'],
                    content=section['content'],
                    is_continuation=is_continuation
                )
                page['sections'].append(section_obj)
            
            # Add rules
            for rule in structure['rules']:
                rule_obj = self.json_formatter.create_rule(
                    rule_number=rule['number'],
                    rule_title=rule['title'],
                    content=rule['content'],
                    is_continuation=is_continuation
                )
                page['rules'].append(rule_obj)
            
            # Add definitions
            for defn in structure['definitions']:
                defn_obj = self.json_formatter.create_definition(
                    term=defn['term'],
                    definition=defn['definition']
                )
                page['definitions'].append(defn_obj)
            
            # Preserve raw text
            page['raw_text'] = text
            
            # Add page to document
            self.json_formatter.add_page(page)
            
            # Update state
            self.previous_page_text = text
            
            logger.info(f"Processed page {page_num + 1}/{total_pages} ({page_type})")
            return True
        
        except Exception as e:
            logger.error(f"Error processing page {page_num + 1}: {e}")
            return False
    
    def get_output_path(self) -> str:
        """Get output file path."""
        return self.output_path

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract structured information from PDF documents and convert to JSON"
    )
    
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to input PDF file"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Path to output JSON file (default: input_filename.json)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run extraction
    extractor = DocumentExtractor(args.input, args.output)
    success = extractor.extract_document()
    
    if success:
        print(f"\n✓ Extraction successful!")
        print(f"Output file: {extractor.get_output_path()}")
        return 0
    else:
        print(f"\n✗ Extraction failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
