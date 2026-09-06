#!/usr/bin/env python3
"""
Multilingual language detection utilities for query processing.
"""

import re
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class LanguageInfo:
    code: str
    name: str
    script: str
    confidence: float


class LanguageDetector:
    """Lightweight language detection using Unicode script analysis."""
    
    # Unicode script ranges for Indian languages
    SCRIPTS = {
        'en': {'name': 'English', 'ranges': [(0x0000, 0x007F), (0x0080, 0x00FF)], 'patterns': [r'[a-zA-Z]']},
        'hi': {'name': 'Hindi', 'ranges': [(0x0900, 0x097F)], 'patterns': [r'[\u0900-\u097F]']},
        'mr': {'name': 'Marathi', 'ranges': [(0x0900, 0x097F)], 'patterns': [r'[\u0900-\u097F]']},
        'gu': {'name': 'Gujarati', 'ranges': [(0x0A80, 0x0AFF)], 'patterns': [r'[\u0A80-\u0AFF]']},
        'bn': {'name': 'Bengali', 'ranges': [(0x0980, 0x09FF)], 'patterns': [r'[\u0980-\u09FF]']},
        'ta': {'name': 'Tamil', 'ranges': [(0x0B80, 0x0BFF)], 'patterns': [r'[\u0B80-\u0BFF]']},
        'te': {'name': 'Telugu', 'ranges': [(0x0C00, 0x0C7F)], 'patterns': [r'[\u0C00-\u0C7F]']},
        'kn': {'name': 'Kannada', 'ranges': [(0x0C80, 0x0CFF)], 'patterns': [r'[\u0C80-\u0CFF]']},
        'ml': {'name': 'Malayalam', 'ranges': [(0x0D00, 0x0D7F)], 'patterns': [r'[\u0D00-\u0D7F]']},
        'pa': {'name': 'Punjabi', 'ranges': [(0x0A00, 0x0A7F)], 'patterns': [r'[\u0A00-\u0A7F]']},
    }

    def __init__(self):
        # Compile patterns for faster matching
        self.compiled_patterns = {}
        for lang, info in self.SCRIPTS.items():
            self.compiled_patterns[lang] = [re.compile(p) for p in info['patterns']]

    def detect(self, text: str) -> LanguageInfo:
        """Detect language of query text."""
        if not text or not text.strip():
            return LanguageInfo('unknown', 'Unknown', '', 0.0)

        scores = {}
        total_chars = len([c for c in text if not c.isspace()])

        if total_chars == 0:
            return LanguageInfo('unknown', 'Unknown', '', 0.0)

        for lang, patterns in self.compiled_patterns.items():
            count = 0
            for pattern in patterns:
                count += len(pattern.findall(text))
            if count > 0:
                scores[lang] = count / total_chars

        if not scores:
            # Default to English if only ASCII
            if all(ord(c) < 128 for c in text):
                return LanguageInfo('en', 'English', 'Latin', 0.8)
            return LanguageInfo('unknown', 'Unknown', '', 0.0)

        # Get highest scoring language
        best_lang = max(scores, key=scores.get)
        info = self.SCRIPTS[best_lang]
        
        # Calculate confidence
        confidence = min(1.0, scores[best_lang] * 2)
        
        return LanguageInfo(
            code=best_lang,
            name=info['name'],
            script=info.get('script', 'Unknown'),
            confidence=round(confidence, 2)
        )

    def is_indian_language(self, lang_code: str) -> bool:
        return lang_code in ['hi', 'mr', 'gu', 'bn', 'ta', 'te', 'kn', 'ml', 'pa']


# Global instance
_detector = LanguageDetector()


def detect_language(text: str) -> LanguageInfo:
    """Convenience function for language detection."""
    return _detector.detect(text)


def get_language_name(lang_code: str) -> str:
    """Get language name from code."""
    return _detector.SCRIPTS.get(lang_code, {}).get('name', lang_code)


if __name__ == '__main__':
    # Test
    test_queries = [
        "What is a patent?",
        "पेटेंट क्या है?",
        "पेटंट म्हणजे काय?",
        "પેટન્ટ શું છે?",
        "பேட்டண்ட் என்றால் என்ன?",
        "పేటెంట్ అంటే ఏమిటి?",
        "ಪೆಟೆಂಟ್ ಎಂದಿಗ?",
        "പെട്ടന്റ് എന്താണ്?",
        "ਪੇਟੈਂਟ ਕੀ ਹੈ?",
    ]
    
    for q in test_queries:
        info = detect_language(q)
        print(f"'{q}' -> {info.code} ({info.name}) confidence={info.confidence}")