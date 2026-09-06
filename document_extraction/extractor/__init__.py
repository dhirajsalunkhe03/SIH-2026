"""
Document Extraction Package
A system for extracting structured information from PDF documents.
"""

__version__ = "1.0.0"
__author__ = "Document Extraction Team"

from .json_formatter import JSONFormatter
from .pdf_processor import PDFProcessor
from .ocr_handler import OCRHandler

__all__ = ["JSONFormatter", "PDFProcessor", "OCRHandler"]
