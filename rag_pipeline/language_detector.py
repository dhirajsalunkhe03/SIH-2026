#!/usr/bin/env python3
"""
Language detection for legal documents (English, Marathi, Mixed).
Uses Unicode script detection.
"""

import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class LanguageResult:
    language: str  # 'en', 'mr', 'mixed', 'unknown'
    language_confidence: Optional[float]
    devanagari_ratio: float
    latin_ratio: float
    total_chars: int
    details: Dict[str, any]


class LanguageDetector:
    # Devanagari Unicode range: U+0900 to U+097F
    DEVANAGARI_RANGE = (0x0900, 0x097F)
    # Basic Latin range: U+0000 to U+007F
    LATIN_RANGE = (0x0000, 0x007F)
    # Latin Extended ranges for accented characters
    LATIN_EXTENDED_RANGES = [
        (0x0080, 0x00FF),  # Latin-1 Supplement
        (0x0100, 0x017F),  # Latin Extended-A
        (0x0180, 0x024F),  # Latin Extended-B
    ]
    
    def __init__(self):
        pass
    
    def detect(self, text: str) -> LanguageResult:
        if not text or not text.strip():
            return LanguageResult(
                language='unknown',
                language_confidence=None,
                devanagari_ratio=0.0,
                latin_ratio=0.0,
                total_chars=0,
                details={'reason': 'empty_text'}
            )
        
        total_chars = len(text)
        devanagari_count = 0
        latin_count = 0
        other_count = 0
        
        for ch in text:
            code = ord(ch)
            if self.DEVANAGARI_RANGE[0] <= code <= self.DEVANAGARI_RANGE[1]:
                devanagari_count += 1
            elif (self.LATIN_RANGE[0] <= code <= self.LATIN_RANGE[1]) or \
                 any(r[0] <= code <= r[1] for r in self.LATIN_EXTENDED_RANGES):
                latin_count += 1
            else:
                other_count += 1
        
        # Exclude whitespace and punctuation from ratio calculation
        meaningful_chars = devanagari_count + latin_count + other_count
        if meaningful_chars == 0:
            return LanguageResult(
                language='unknown',
                language_confidence=None,
                devanagari_ratio=0.0,
                latin_ratio=0.0,
                total_chars=total_chars,
                details={'reason': 'no_meaningful_chars'}
            )
        
        devanagari_ratio = devanagari_count / meaningful_chars
        latin_ratio = latin_count / meaningful_chars
        
        # Determine language
        if devanagari_ratio >= 0.5 and latin_ratio <= 0.3:
            language = 'mr'
            confidence = min(0.99, devanagari_ratio + 0.1)
        elif latin_ratio >= 0.5 and devanagari_ratio <= 0.3:
            language = 'en'
            confidence = min(0.99, latin_ratio + 0.1)
        elif devanagari_ratio >= 0.15 and latin_ratio >= 0.15:
            language = 'mixed'
            confidence = min(0.9, 1.0 - abs(devanagari_ratio - latin_ratio))
        else:
            language = 'unknown'
            confidence = None
        
        details = {
            'devanagari_count': devanagari_count,
            'latin_count': latin_count,
            'other_count': other_count,
            'meaningful_chars': meaningful_chars,
            'sample_devanagari': self._get_sample_chars(text, 'devanagari')[:50],
            'sample_latin': self._get_sample_chars(text, 'latin')[:50],
        }
        
        return LanguageResult(
            language=language,
            language_confidence=round(confidence, 3) if confidence else None,
            devanagari_ratio=round(devanagari_ratio, 3),
            latin_ratio=round(latin_ratio, 3),
            total_chars=total_chars,
            details=details
        )
    
    def _get_sample_chars(self, text: str, script: str) -> str:
        samples = []
        for ch in text:
            code = ord(ch)
            if script == 'devanagari' and self.DEVANAGARI_RANGE[0] <= code <= self.DEVANAGARI_RANGE[1]:
                samples.append(ch)
            elif script == 'latin' and (self.LATIN_RANGE[0] <= code <= self.LATIN_RANGE[1] or 
                  any(r[0] <= code <= r[1] for r in self.LATIN_EXTENDED_RANGES)):
                if ch.isalnum():
                    samples.append(ch)
            if len(samples) >= 100:
                break
        return ''.join(samples)


def detect_file_language(pdf_path: Path, max_pages: int = 5) -> LanguageResult:
    """Detect language from PDF text extraction (first few pages)."""
    try:
        import pdfplumber
        text_samples = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= max_pages:
                    break
                text = page.extract_text() or ""
                text_samples.append(text)
        combined = "\n".join(text_samples)
        detector = LanguageDetector()
        return detector.detect(combined)
    except Exception as e:
        return LanguageResult(
            language='unknown',
            language_confidence=None,
            devanagari_ratio=0.0,
            latin_ratio=0.0,
            total_chars=0,
            details={'error': str(e)}
        )


def main():
    if len(sys.argv) < 2:
        print("Usage: python language_detector.py <pdf_path> [max_pages]")
        print("       python language_detector.py --text '<text>'")
        return 1
    
    detector = LanguageDetector()
    
    if sys.argv[1] == '--text':
        text = sys.argv[2] if len(sys.argv) > 2 else ""
        result = detector.detect(text)
        print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
        return 0
    
    pdf_path = Path(sys.argv[1])
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        return 1
    
    result = detect_file_language(pdf_path, max_pages)
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    main()