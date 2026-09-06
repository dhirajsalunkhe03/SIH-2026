"""
OCR handling and text recognition module.
"""

import re
from typing import Optional, Tuple
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class OCRHandler:
    """Handles OCR processing and text correction for extracted text."""
    
    def __init__(self, config: dict = None):
        """
        Initialize OCR handler.
        
        Args:
            config: OCR configuration dictionary
        """
        self.config = config or {}
        self.unclear_marker = "[UNCLEAR]"
        
        # Try to import pytesseract
        try:
            import pytesseract
            self.pytesseract = pytesseract
            self.ocr_available = True
        except ImportError:
            logger.warning("pytesseract not available. OCR will be limited.")
            self.pytesseract = None
            self.ocr_available = False
    
    def extract_text_from_image(self, image: Image.Image) -> str:
        """
        Extract text from an image using OCR.
        
        Args:
            image: PIL Image object
            
        Returns:
            Extracted text string
        """
        if not self.ocr_available:
            logger.warning("OCR not available. Returning empty string.")
            return ""
        
        try:
            config = self.config.get("config", "--psm 3")
            text = self.pytesseract.image_to_string(image, config=config)
            return text
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""
    
    def correct_ocr_errors(self, text: str) -> str:
        """
        Apply common OCR error corrections.
        
        Args:
            text: Text potentially containing OCR errors
            
        Returns:
            Corrected text
        """
        if not text:
            return text
        
        # Common OCR misrecognitions
        corrections = {
            r'\bl\b': 'l',  # lowercase L often misread
            r'\bO\b': '0',  # O often confused with 0
            r'\bI\b': '1' if re.search(r'\d', text) else 'I',  # Context-dependent
            r'rn': 'm',  # rm often misread as rn
            r'ii': 'u',  # ii sometimes misread as u
            r'1s': 'is',  # 1s sometimes misread as is
        }
        
        corrected = text
        for pattern, replacement in corrections.items():
            corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
        
        return corrected
    
    def validate_text_confidence(self, text: str, min_confidence: float = 0.7) -> Tuple[str, float]:
        """
        Validate text quality and return confidence score.
        
        Args:
            text: Extracted text
            min_confidence: Minimum acceptable confidence score
            
        Returns:
            Tuple of (text, confidence_score)
        """
        if not text or len(text.strip()) == 0:
            return text, 0.0
        
        # Simple heuristic confidence calculation
        # This is a placeholder - actual implementation would use OCR confidence data
        
        # Check for minimum length
        if len(text) < 10:
            confidence = 0.5
        else:
            # Check for valid characters (letters, numbers, punctuation)
            valid_chars = sum(1 for c in text if c.isalnum() or c in ' .,;:-\'"()[]{}')
            confidence = min(1.0, valid_chars / len(text))
        
        return text, confidence
    
    def mark_unclear_regions(self, text: str, unclear_threshold: float = 0.5) -> str:
        """
        Mark regions with low confidence as [UNCLEAR].
        
        Args:
            text: Extracted text
            unclear_threshold: Confidence threshold below which text is marked unclear
            
        Returns:
            Text with unclear regions marked
        """
        marked_text, confidence = self.validate_text_confidence(text)
        
        if confidence < unclear_threshold:
            return self.unclear_marker
        
        return marked_text
    
    def extract_legal_terms(self, text: str) -> list:
        """
        Extract potential legal terms and definitions from text.
        
        Args:
            text: Input text
            
        Returns:
            List of extracted legal terms
        """
        # Pattern for definitions (common in legal documents)
        definition_pattern = r'["\']?([A-Za-z\s]+)["\']?\s+(?:means?|shall\s+mean|is\s+defined\s+as|refers?\s+to)\s+'
        
        matches = re.findall(definition_pattern, text, re.IGNORECASE)
        return [match.strip() for match in matches if match.strip()]
    
    def preserve_formatting(self, text: str) -> str:
        """
        Preserve important formatting in text.
        
        Args:
            text: Input text
            
        Returns:
            Text with preserved formatting
        """
        # Preserve line breaks and indentation for legal documents
        # This maintains the structure that's often important in legal texts
        
        # Don't collapse excessive whitespace - it may indicate structure
        lines = text.split('\n')
        preserved = []
        
        for line in lines:
            # Preserve indentation but normalize internal spaces
            indent = len(line) - len(line.lstrip())
            content = ' '.join(line.split())
            if content:
                preserved.append(' ' * indent + content)
            else:
                preserved.append('')
        
        return '\n'.join(preserved)
    
    def is_unclear(self, text: str) -> bool:
        """
        Check if text should be marked as unclear.
        
        Args:
            text: Input text
            
        Returns:
            True if text confidence is below threshold
        """
        _, confidence = self.validate_text_confidence(text)
        return confidence < 0.7
