"""
Unit tests for the document extraction system.
Run with: python -m pytest test_extraction.py -v
"""

import json
import tempfile
from pathlib import Path
import unittest

from extractor import JSONFormatter, PDFProcessor, OCRHandler
from extractor.config import (
    DocumentType, PageType, OCR_CONFIG, LEGAL_PATTERNS
)

class TestJSONFormatter(unittest.TestCase):
    """Test JSON formatting functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.formatter = JSONFormatter()
    
    def test_create_document(self):
        """Test document creation."""
        self.formatter.create_document("Test Act", "Act", 10)
        
        doc = self.formatter.to_dict()
        self.assertEqual(doc["document"]["document_name"], "Test Act")
        self.assertEqual(doc["document"]["document_type"], "Act")
        self.assertEqual(doc["document"]["total_pages"], 10)
    
    def test_create_page(self):
        """Test page creation."""
        page = self.formatter.create_page(1, "content", "Page Title")
        
        self.assertEqual(page["page_number"], 1)
        self.assertEqual(page["page_type"], "content")
        self.assertEqual(page["title"], "Page Title")
        self.assertIsInstance(page["sections"], list)
    
    def test_create_section(self):
        """Test section creation."""
        section = self.formatter.create_section(
            "1", "Title", "Content", False
        )
        
        self.assertEqual(section["section_number"], "1")
        self.assertEqual(section["section_title"], "Title")
        self.assertEqual(section["content"], "Content")
        self.assertFalse(section["is_continuation"])
    
    def test_create_definition(self):
        """Test definition creation."""
        defn = self.formatter.create_definition(
            "Authority", "means the Government"
        )
        
        self.assertEqual(defn["term"], "Authority")
        self.assertEqual(defn["definition"], "means the Government")
    
    def test_validate_json(self):
        """Test JSON validation."""
        # Empty document should fail
        self.assertFalse(self.formatter.validate_json())
        
        # Document with metadata but no pages should fail
        self.formatter.create_document("Test", "Act", 1)
        self.assertFalse(self.formatter.validate_json())
        
        # Document with pages should pass
        page = self.formatter.create_page(1)
        self.formatter.add_page(page)
        self.assertTrue(self.formatter.validate_json())
    
    def test_json_serialization(self):
        """Test JSON serialization."""
        self.formatter.create_document("Test", "Act", 1)
        page = self.formatter.create_page(1)
        self.formatter.add_page(page)
        
        json_str = self.formatter.to_json()
        parsed = json.loads(json_str)
        
        self.assertEqual(parsed["document"]["document_name"], "Test")
        self.assertEqual(len(parsed["pages"]), 1)
    
    def test_file_io(self):
        """Test file input/output."""
        self.formatter.create_document("Test", "Act", 1)
        page = self.formatter.create_page(1)
        self.formatter.add_page(page)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            # Write to file
            self.assertTrue(self.formatter.to_file(temp_file))
            self.assertTrue(Path(temp_file).exists())
            
            # Read from file
            formatter2 = JSONFormatter()
            self.assertTrue(formatter2.from_file(temp_file))
            self.assertEqual(
                formatter2.to_dict()["document"]["document_name"],
                "Test"
            )
        finally:
            Path(temp_file).unlink()

class TestOCRHandler(unittest.TestCase):
    """Test OCR handling functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = OCRHandler(OCR_CONFIG)
    
    def test_text_confidence(self):
        """Test text confidence scoring."""
        valid_text = "This is a proper English sentence."
        text, confidence = self.handler.validate_text_confidence(valid_text)
        
        self.assertGreater(confidence, 0.5)
        self.assertEqual(text, valid_text)
    
    def test_unclear_marking(self):
        """Test unclear text marking."""
        text = "g@rb@g3 t3xt"
        result = self.handler.mark_unclear_regions(text, 0.5)
        
        # Should be marked as unclear
        self.assertTrue(self.handler.unclear_marker in result or result == text)
    
    def test_preserve_formatting(self):
        """Test formatting preservation."""
        text = "Section 1:  This is   a test\n    Indented line"
        preserved = self.handler.preserve_formatting(text)
        
        # Should maintain some structure
        self.assertIn("Section 1:", preserved)
        self.assertIn("Indented", preserved)

class TestPDFProcessor(unittest.TestCase):
    """Test PDF processing functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = PDFProcessor()
    
    def test_page_type_detection(self):
        """Test page type detection."""
        content = "Table of Contents\n1. Introduction\n2. Main Content"
        page_type = self.processor.detect_page_type(content, 1, 10)
        
        self.assertEqual(page_type, "table_of_contents")
    
    def test_continuation_detection(self):
        """Test continuation detection."""
        current_text = "continued from previous page with incomplete"
        previous_text = "Section 1: This is a section that doesn't end properly"
        
        is_continuation = self.processor.detect_continuation(current_text, previous_text)
        
        self.assertTrue(is_continuation)
    
    def test_extract_sections(self):
        """Test section extraction."""
        text = """
        Section 1: Short title
        This is the content.
        
        Section 2: Definitions
        Rule 1: First rule
        """
        
        structure = self.processor.extract_page_structure(text)
        
        self.assertGreater(len(structure['sections']), 0)
        self.assertGreater(len(structure['rules']), 0)

class TestLegalPatterns(unittest.TestCase):
    """Test legal document pattern matching."""
    
    def test_section_pattern(self):
        """Test section number pattern."""
        import re
        pattern = LEGAL_PATTERNS["section_pattern"]
        
        test_cases = [
            ("Section 1: Title", True),
            ("Section 2.1: Subsection", True),
            ("SECTION 3: All caps", True),
            ("No match here", False),
        ]
        
        for text, should_match in test_cases:
            matches = re.search(pattern, text, re.IGNORECASE)
            if should_match:
                self.assertIsNotNone(matches)
            else:
                self.assertIsNone(matches)
    
    def test_definition_pattern(self):
        """Test definition pattern."""
        import re
        pattern = LEGAL_PATTERNS["definition_pattern"]
        
        test_text = '"Authority" means the Central Government or its agency'
        matches = re.search(pattern, test_text, re.IGNORECASE)
        
        self.assertIsNotNone(matches)

def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)

if __name__ == "__main__":
    print("=" * 60)
    print("Document Extraction System - Unit Tests")
    print("=" * 60)
    print()
    
    run_tests()
    
    print()
    print("=" * 60)
    print("Tests complete!")
    print("=" * 60)
