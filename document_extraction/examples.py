"""
Example usage of the document extraction system.
"""

from extractor import JSONFormatter, PDFProcessor, OCRHandler
from extractor.config import OCR_CONFIG
import json

def example_basic_extraction():
    """Example: Basic extraction and JSON output."""
    
    # Initialize components
    ocr_handler = OCRHandler(OCR_CONFIG)
    pdf_processor = PDFProcessor(ocr_handler)
    json_formatter = JSONFormatter()
    
    # Create a document
    json_formatter.create_document(
        doc_name="Sample Act 2024",
        doc_type="Act",
        total_pages=10
    )
    
    # Create a page
    page = json_formatter.create_page(page_number=1, page_type="content")
    
    # Add a section
    section = json_formatter.create_section(
        section_number="1",
        section_title="Short title and commencement",
        content="This Act may be called the Sample Act, 2024...",
        is_continuation=False
    )
    page['sections'].append(section)
    
    # Add a definition
    defn = json_formatter.create_definition(
        term="Authority",
        definition="means the Central Government or its authorized agency"
    )
    page['definitions'].append(defn)
    
    # Add raw text
    page['raw_text'] = "Section 1: Short title and commencement\nThis Act may be called..."
    
    # Add page to document
    json_formatter.add_page(page)
    
    # Output
    print("Generated JSON:")
    print(json_formatter.to_json())
    
    # Save to file
    json_formatter.to_file("example_output.json")
    print("\nSaved to example_output.json")

def example_page_processing():
    """Example: Processing individual pages."""
    
    pdf_processor = PDFProcessor()
    
    # Example: Detect page type
    text_content = "Section 1: Title\nRule 1: Content\nDefinition of Authority means..."
    page_type = pdf_processor.detect_page_type(text_content, page_num=1, total_pages=10)
    print(f"Detected page type: {page_type}")
    
    # Example: Extract page structure
    structure = pdf_processor.extract_page_structure(text_content)
    print(f"Extracted sections: {len(structure['sections'])}")
    print(f"Extracted rules: {len(structure['rules'])}")
    print(f"Extracted definitions: {len(structure['definitions'])}")

def example_ocr_handling():
    """Example: OCR error handling."""
    
    ocr_handler = OCRHandler(OCR_CONFIG)
    
    # Example text with potential OCR errors
    text_with_errors = "Section 1: This is a test\n0CR error: 'l' should be '1'"
    
    # Correct errors
    corrected = ocr_handler.correct_ocr_errors(text_with_errors)
    print(f"Original: {text_with_errors}")
    print(f"Corrected: {corrected}")
    
    # Check text confidence
    text, confidence = ocr_handler.validate_text_confidence(text_with_errors)
    print(f"Confidence score: {confidence:.2%}")

if __name__ == "__main__":
    print("=" * 60)
    print("Document Extraction System - Examples")
    print("=" * 60)
    
    print("\n1. Basic Extraction Example:")
    print("-" * 60)
    example_basic_extraction()
    
    print("\n2. Page Processing Example:")
    print("-" * 60)
    example_page_processing()
    
    print("\n3. OCR Handling Example:")
    print("-" * 60)
    example_ocr_handling()
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)
