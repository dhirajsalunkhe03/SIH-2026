"""
JSON formatting and output module.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import copy

from .config import (
    DOCUMENT_SCHEMA, PAGE_SCHEMA, SECTION_SCHEMA, RULE_SCHEMA,
    DEFINITION_SCHEMA, TABLE_SCHEMA, FORM_SCHEMA
)

logger = logging.getLogger(__name__)

class JSONFormatter:
    """Handles JSON formatting and validation for extracted document data."""
    
    def __init__(self):
        """Initialize JSON formatter."""
        self.document = copy.deepcopy(DOCUMENT_SCHEMA)
    
    def create_document(self, doc_name: str, doc_type: str, total_pages: int) -> None:
        """
        Initialize document metadata.
        
        Args:
            doc_name: Name of the document
            doc_type: Type of document (Act, Rule, etc.)
            total_pages: Total number of pages
        """
        self.document["document"]["document_name"] = doc_name
        self.document["document"]["document_type"] = doc_type
        self.document["document"]["total_pages"] = total_pages
        logger.info(f"Created document: {doc_name} ({doc_type}), {total_pages} pages")
    
    def add_page(self, page_data: Dict[str, Any]) -> None:
        """
        Add a page to the document.
        
        Args:
            page_data: Page data dictionary
        """
        # Validate required fields
        if 'page_number' not in page_data:
            logger.error("Page must have a page_number")
            return
        
        self.document["pages"].append(page_data)
        logger.debug(f"Added page {page_data['page_number']}")
    
    @staticmethod
    def create_page(page_number: int, page_type: str = "content", 
                   title: Optional[str] = None, chapter: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a page template.
        
        Args:
            page_number: Page number
            page_type: Type of page (content, table_of_contents, etc.)
            title: Optional page title
            chapter: Optional chapter name
            
        Returns:
            Page dictionary
        """
        page = copy.deepcopy(PAGE_SCHEMA)
        page["page_number"] = page_number
        page["page_type"] = page_type
        page["title"] = title
        page["chapter"] = chapter
        return page
    
    @staticmethod
    def create_section(section_number: str, section_title: Optional[str] = None,
                      content: Optional[str] = None, is_continuation: bool = False) -> Dict[str, Any]:
        """
        Create a section object.
        
        Args:
            section_number: Section number
            section_title: Section title
            content: Section content
            is_continuation: Whether this is a continuation from previous page
            
        Returns:
            Section dictionary
        """
        section = copy.deepcopy(SECTION_SCHEMA)
        section["section_number"] = section_number
        section["section_title"] = section_title
        section["content"] = content
        section["is_continuation"] = is_continuation
        return section
    
    @staticmethod
    def create_rule(rule_number: str, rule_title: Optional[str] = None,
                   content: Optional[str] = None, is_continuation: bool = False) -> Dict[str, Any]:
        """
        Create a rule object.
        
        Args:
            rule_number: Rule number
            rule_title: Rule title
            content: Rule content
            is_continuation: Whether this is a continuation from previous page
            
        Returns:
            Rule dictionary
        """
        rule = copy.deepcopy(RULE_SCHEMA)
        rule["rule_number"] = rule_number
        rule["rule_title"] = rule_title
        rule["content"] = content
        rule["is_continuation"] = is_continuation
        return rule
    
    @staticmethod
    def create_definition(term: str, definition: str) -> Dict[str, Any]:
        """
        Create a definition object.
        
        Args:
            term: Term being defined
            definition: Definition text
            
        Returns:
            Definition dictionary
        """
        defn = copy.deepcopy(DEFINITION_SCHEMA)
        defn["term"] = term
        defn["definition"] = definition
        return defn
    
    @staticmethod
    def create_table(table_number: Optional[str] = None, table_title: Optional[str] = None,
                    headers: Optional[List[str]] = None, rows: Optional[List[List[str]]] = None) -> Dict[str, Any]:
        """
        Create a table object.
        
        Args:
            table_number: Table number
            table_title: Table title
            headers: Table headers
            rows: Table rows
            
        Returns:
            Table dictionary
        """
        table = copy.deepcopy(TABLE_SCHEMA)
        table["table_number"] = table_number
        table["table_title"] = table_title
        table["headers"] = headers or []
        table["rows"] = rows or []
        return table
    
    @staticmethod
    def create_form(form_number: Optional[str] = None, form_title: Optional[str] = None,
                   fields: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Create a form object.
        
        Args:
            form_number: Form number
            form_title: Form title
            fields: Form fields
            
        Returns:
            Form dictionary
        """
        form = copy.deepcopy(FORM_SCHEMA)
        form["form_number"] = form_number
        form["form_title"] = form_title
        form["fields"] = fields or []
        return form
    
    def validate_json(self) -> bool:
        """
        Validate the current document JSON structure.
        
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check document metadata
            if not self.document["document"]["document_name"]:
                logger.error("Document must have a name")
                return False
            
            if not self.document["pages"]:
                logger.warning("Document has no pages")
                return False
            
            # Validate each page
            for page in self.document["pages"]:
                if "page_number" not in page:
                    logger.error(f"Page missing page_number: {page}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"JSON validation error: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Get document as dictionary.
        
        Returns:
            Document dictionary
        """
        return copy.deepcopy(self.document)
    
    def to_json(self, indent: int = 2) -> str:
        """
        Convert document to JSON string.
        
        Args:
            indent: JSON indentation level
            
        Returns:
            JSON string
        """
        return json.dumps(self.document, indent=indent, ensure_ascii=False)
    
    def to_file(self, filepath: str, indent: int = 2) -> bool:
        """
        Write document to JSON file.
        
        Args:
            filepath: Output file path
            indent: JSON indentation level
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.document, f, indent=indent, ensure_ascii=False)
            logger.info(f"Document written to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error writing to file: {e}")
            return False
    
    def from_json(self, json_string: str) -> bool:
        """
        Load document from JSON string.
        
        Args:
            json_string: JSON string
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.document = json.loads(json_string)
            logger.info("Document loaded from JSON")
            return True
        except Exception as e:
            logger.error(f"Error parsing JSON: {e}")
            return False
    
    def from_file(self, filepath: str) -> bool:
        """
        Load document from JSON file.
        
        Args:
            filepath: Input file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.document = json.load(f)
            logger.info(f"Document loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return False
    
    def add_page_content(self, page_index: int, content_type: str, content_data: Dict[str, Any]) -> bool:
        """
        Add content to an existing page.
        
        Args:
            page_index: Index in pages array
            content_type: Type of content (sections, rules, definitions, etc.)
            content_data: Content data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if content_type in self.document["pages"][page_index]:
                self.document["pages"][page_index][content_type].append(content_data)
                return True
            else:
                logger.error(f"Unknown content type: {content_type}")
                return False
        except IndexError:
            logger.error(f"Page index out of range: {page_index}")
            return False
        except Exception as e:
            logger.error(f"Error adding page content: {e}")
            return False
    
    def get_page_count(self) -> int:
        """
        Get number of pages in document.
        
        Returns:
            Number of pages
        """
        return len(self.document["pages"])
    
    def get_page(self, page_index: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific page.
        
        Args:
            page_index: Index in pages array
            
        Returns:
            Page dictionary or None
        """
        try:
            return self.document["pages"][page_index]
        except IndexError:
            logger.error(f"Page index out of range: {page_index}")
            return None
