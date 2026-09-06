"""
Configuration and schema definitions for document extraction.
"""

from typing import Optional, List, Dict, Any
from enum import Enum

# Document Types
class DocumentType(str, Enum):
    ACT = "Act"
    RULE = "Rule"
    NOTIFICATION = "Notification"
    COURT_JUDGMENT = "Court Judgment"
    PATENT = "Patent"
    OTHER = "Other"

# Page Types
class PageType(str, Enum):
    CONTENT = "content"
    TABLE_OF_CONTENTS = "table_of_contents"
    PREAMBLE = "preamble"
    DEFINITION = "definition"
    SCHEDULE = "schedule"
    FORM = "form"
    OTHER = "other"

# Document Schema Template
DOCUMENT_SCHEMA = {
    "document": {
        "document_name": None,
        "document_type": "Act/Rule/Notification/Other",
        "source": "India Code",
        "total_pages": None
    },
    "pages": []
}

# Page Schema Template
PAGE_SCHEMA = {
    "page_number": None,
    "page_type": "content",
    "title": None,
    "chapter": None,
    "sections": [],
    "rules": [],
    "definitions": [],
    "references": [],
    "tables": [],
    "forms": [],
    "raw_text": None
}

# Section Schema Template
SECTION_SCHEMA = {
    "section_number": None,
    "section_title": None,
    "content": None,
    "is_continuation": False
}

# Rule Schema Template
RULE_SCHEMA = {
    "rule_number": None,
    "rule_title": None,
    "content": None,
    "is_continuation": False
}

# Definition Schema Template
DEFINITION_SCHEMA = {
    "term": None,
    "definition": None
}

# Table Schema Template
TABLE_SCHEMA = {
    "table_number": None,
    "table_title": None,
    "headers": [],
    "rows": [],
    "raw_html": None
}

# Form Schema Template
FORM_SCHEMA = {
    "form_number": None,
    "form_title": None,
    "fields": [],
    "raw_html": None
}

# Extraction Rules
EXTRACTION_RULES = {
    "preserve_legal_terminology": True,
    "preserve_section_numbers": True,
    "preserve_dates": True,
    "preserve_references": True,
    "preserve_definitions": True,
    "remove_headers_footers": True,
    "remove_page_numbers": True,
    "correct_ocr_errors": True,
    "mark_unclear_text": True,
    "never_invent_text": True,
}

# OCR Configuration
OCR_CONFIG = {
    "engine": "pytesseract",
    "language": "eng",
    "psm": 3,  # Assume a single column of text
    "oem": 3,  # Use both legacy and LSTM OCR engine modes
    "config": "--psm 3",
}

# Common patterns for legal documents
LEGAL_PATTERNS = {
    "section_pattern": r"^Section\s+(\d+[\w\-\.]*):?\s*(.*?)$",
    "rule_pattern": r"^Rule\s+(\d+[\w\-\.]*):?\s*(.*?)$",
    "definition_pattern": r"^['\"]?([A-Za-z\s]+)['\"]?\s*(?:means?|shall\s+mean|defined\s+as)\s+(.*?)$",
    "schedule_pattern": r"^(?:Schedule|SCHEDULE)\s+([A-Z\d]*).*?$",
    "form_pattern": r"^(?:Form|FORM)\s+(\d+[\w\-\.]*):?\s*(.*?)$",
}

# Source documentation
SOURCE_DOCUMENTATION = {
    "type": "Indian Legal Documents",
    "source_url": "https://indiacode.nic.in/",
    "last_updated": "2024",
}
