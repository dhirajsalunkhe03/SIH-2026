"""
PDF processing module for extracting text and images from PDF files.
"""

import logging
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import PyPDF2
from pdf2image import convert_from_path
from PIL import Image
import tempfile

from .ocr_handler import OCRHandler
from .config import PAGE_SCHEMA, PageType

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Handles PDF file processing and page extraction."""
    
    def __init__(self, ocr_handler: OCRHandler = None):
        """
        Initialize PDF processor.
        
        Args:
            ocr_handler: OCRHandler instance for text recognition
        """
        self.ocr_handler = ocr_handler or OCRHandler()
    
    def open_pdf(self, pdf_path: str) -> Optional[PyPDF2.PdfReader]:
        """
        Open and read a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            PdfReader object or None if error
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf = PyPDF2.PdfReader(file)
                logger.info(f"Opened PDF: {pdf_path} ({len(pdf.pages)} pages)")
                return pdf
        except FileNotFoundError:
            logger.error(f"PDF file not found: {pdf_path}")
            return None
        except Exception as e:
            logger.error(f"Error opening PDF: {e}")
            return None
    
    def get_total_pages(self, pdf: PyPDF2.PdfReader) -> int:
        """
        Get total number of pages in PDF.
        
        Args:
            pdf: PdfReader object
            
        Returns:
            Number of pages
        """
        return len(pdf.pages)
    
    def extract_text_from_page(self, pdf: PyPDF2.PdfReader, page_num: int) -> str:
        """
        Extract text from a specific PDF page.
        
        Args:
            pdf: PdfReader object
            page_num: Page number (0-indexed)
            
        Returns:
            Extracted text
        """
        try:
            page = pdf.pages[page_num]
            text = page.extract_text()
            return text if text else ""
        except Exception as e:
            logger.error(f"Error extracting text from page {page_num}: {e}")
            return ""
    
    def convert_page_to_image(self, pdf_path: str, page_num: int) -> Optional[Image.Image]:
        """
        Convert a PDF page to an image.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            
        Returns:
            PIL Image object or None if error
        """
        try:
            images = convert_from_path(pdf_path, first_page=page_num + 1, last_page=page_num + 1)
            return images[0] if images else None
        except Exception as e:
            logger.error(f"Error converting page {page_num} to image: {e}")
            return None
    
    def extract_text_via_ocr(self, pdf_path: str, page_num: int) -> str:
        """
        Extract text from a PDF page using OCR.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            
        Returns:
            Extracted text via OCR
        """
        image = self.convert_page_to_image(pdf_path, page_num)
        if image is None:
            return ""
        
        try:
            text = self.ocr_handler.extract_text_from_image(image)
            # Preserve formatting
            text = self.ocr_handler.preserve_formatting(text)
            return text
        except Exception as e:
            logger.error(f"OCR extraction failed for page {page_num}: {e}")
            return ""
    
    def get_page_text(self, pdf: PyPDF2.PdfReader, pdf_path: str, page_num: int, use_ocr_fallback: bool = True) -> str:
        """
        Extract text from a page, using OCR as fallback if needed.
        
        Args:
            pdf: PdfReader object
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            use_ocr_fallback: Use OCR if direct extraction fails
            
        Returns:
            Extracted text
        """
        # First try direct text extraction
        text = self.extract_text_from_page(pdf, page_num)
        
        # If empty or too short, try OCR
        if (not text or len(text.strip()) < 50) and use_ocr_fallback:
            logger.info(f"Using OCR fallback for page {page_num}")
            text = self.extract_text_via_ocr(pdf_path, page_num)
        
        return text
    
    def detect_page_type(self, text: str, page_num: int, total_pages: int) -> str:
        """
        Detect the type of page based on content.
        
        Args:
            text: Page text
            page_num: Page number (1-indexed)
            total_pages: Total pages in document
            
        Returns:
            Page type string
        """
        text_lower = text.lower()
        
        # Check for table of contents
        if page_num <= 3 and ('table of contents' in text_lower or 'contents' in text_lower):
            return 'table_of_contents'
        
        # Check for preamble/introduction
        if page_num == 1 and ('preamble' in text_lower or 'introduction' in text_lower):
            return 'preamble'
        
        # Check for definitions
        if 'definitions' in text_lower and text.count('means') > 2:
            return 'definition'
        
        # Check for schedules
        if 'schedule' in text_lower:
            return 'schedule'
        
        # Check for forms
        if 'form' in text_lower and ('field' in text_lower or 'signature' in text_lower):
            return 'form'
        
        # Default to content
        return 'content'
    
    def detect_continuation(self, current_text: str, previous_page_text: str, current_section: Optional[str] = None) -> bool:
        """
        Detect if current page is a continuation from previous page.
        
        Args:
            current_text: Current page text
            previous_page_text: Previous page text
            current_section: Current section number being processed
            
        Returns:
            True if this page is a continuation
        """
        if not previous_page_text or not current_text:
            return False
        
        # Check if current page starts mid-sentence
        current_start = current_text[:100].strip()
        
        # If current page doesn't start with a new section/rule header
        if not any(indicator in current_start for indicator in ['Section', 'Rule', 'Article']):
            # Check if previous page ends mid-paragraph
            previous_end = previous_page_text[-200:].strip()
            if not previous_end.endswith(('.', ')', ':', '"', '\n')):
                return True
        
        return False
    
    def extract_page_structure(self, text: str) -> Dict[str, Any]:
        """
        Extract structural elements from page text.
        
        Args:
            text: Page text
            
        Returns:
            Dictionary containing extracted sections, rules, etc.
        """
        import re
        
        structure = {
            'sections': [],
            'rules': [],
            'definitions': [],
            'paragraphs': []
        }
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Extract sections
            section_match = re.match(r'^Section\s+(\d+[\w\-\.]*):?\s*(.*?)$', line, re.IGNORECASE)
            if section_match:
                structure['sections'].append({
                    'number': section_match.group(1),
                    'title': section_match.group(2),
                    'content': ''
                })
            
            # Extract rules
            rule_match = re.match(r'^Rule\s+(\d+[\w\-\.]*):?\s*(.*?)$', line, re.IGNORECASE)
            if rule_match:
                structure['rules'].append({
                    'number': rule_match.group(1),
                    'title': rule_match.group(2),
                    'content': ''
                })
            
            # Extract definitions
            def_match = re.match(r'^["\']?([A-Za-z\s]+)["\']?\s+(?:means?|shall\s+mean|is\s+defined\s+as)\s+(.*?)$', line, re.IGNORECASE)
            if def_match:
                structure['definitions'].append({
                    'term': def_match.group(1),
                    'definition': def_match.group(2)
                })
        
        return structure
