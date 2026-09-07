#!/usr/bin/env python3
"""
Multilingual language detection utilities for query processing.
Uses a combination of Unicode script analysis and word-level heuristics.
"""

import re
from typing import Dict, Optional, Set
from dataclasses import dataclass


@dataclass
class LanguageInfo:
    code: str
    name: str
    script: str
    confidence: float


class LanguageDetector:
    """Language detection using Unicode script analysis with word-level heuristics."""
    
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
    
    # Language-specific common words for disambiguation (especially Hindi vs Marathi)
    LANGUAGE_WORDS = {
        'hi': {
            'क्या', 'है', 'का', 'के', 'की', 'में', 'से', 'को', 'पर', 'और', 'या', 'नहीं', 'हैं', 'था', 'थी', 'थे',
            'होगा', 'होगी', 'होंगे', 'करता', 'करती', 'करते', 'किया', 'किया', 'दिया', 'लिया', 'गया', 'आई',
            'आया', 'जाता', 'जाती', 'जाते', 'चाहता', 'चाहती', 'चाहते', 'मिलता', 'मिलती', 'मिलते',
            'पता', 'बताओ', 'बताइए', 'जानना', 'समझ', 'समझना', 'पढ़ना', 'लिखना', 'बोलना', 'सुनना'
        },
        'mr': {
            'काय', 'आहे', 'चा', 'चे', 'ची', 'मध्ये', 'पासून', 'ला', 'वर', 'आणि', 'किंवा', 'नाही', 'आहात', 'होते', 'होती', 'होते',
            'होईल', 'होईल', 'होईल', 'करतो', 'करते', 'करतात', 'केले', 'केली', 'केले', 'दिले', 'घेतले', 'गेलं', 'आलं',
            'जातो', 'जाते', 'जातात', 'पाहिजे', 'पाहिजे', 'पाहिजेत', 'मिळतो', 'मिळते', 'मिळतात',
            'माहिती', 'सांगा', 'सांग', 'समज', 'समजाव', 'वाच', 'लिह', 'बोल', 'ऐक'
        },
        'gu': {
            'શું', 'છે', 'નો', 'ની', 'નાં', 'માં', 'થી', 'ને', 'પર', 'અને', 'અથવા', 'નથી', 'છો', 'હતું', 'હતી', 'હતા',
            'શે', 'શે', 'શે', 'કરે', 'કરે', 'કરે', 'કર્યું', 'કર્યું', 'દીધું', 'લીધું', 'ગયું', 'આવ્યું',
            'જાય', 'જાય', 'જાય', 'ચાહે', 'ચાહે', 'ચાહે', 'મળે', 'મળે', 'મળે'
        },
        'bn': {
            'কি', 'হয়', 'এর', 'এর', 'যে', 'তে', 'থেকে', 'কে', 'পর', 'এবং', 'অথবা', 'না', 'ছেন', 'ছিল', 'ছিল', 'ছিল',
            'হবে', 'হবে', 'হবে', 'করে', 'করে', 'করে', 'করল', 'করল', 'দিল', 'নিল', 'গেল', 'আসло',
            'যাবে', 'যাবে', 'যাবে', 'চায়', 'চায়', 'চায়', 'পায়', 'পায়', 'পায়'
        },
        'ta': {
            'என்ன', 'ஆகும்', 'இன்', 'இன்', 'உள்ள', 'இல்', 'இருந்து', 'உக்கு', 'மேல்', 'மற்றும்', 'அல்லது', 'இல்லை', 'உள்ளன', 'இருந்தது', 'இருந்தது', 'இருந்தது',
            'ஆகும்', 'ஆகும்', 'ஆகும்', 'செய்யும்', 'செய்யும்', 'செய்யும்', 'செய்தார்', 'செய்தார்', 'கொடுத்தார்', 'எடுத்தார்', 'போனார்', 'வந்தார்',
            'போவார்', 'போவார்', 'போவார்', 'வேண்டும்', 'வேண்டும்', 'வேண்டும்', 'கிடைக்கும்', 'கிடைக்கும்', 'கிடைக்கும்'
        },
        'te': {
            'ఏమి', 'అవుతుంది', 'ਦਾ', 'ది', 'లో', 'నుండి', 'కంటే', 'మరియు', 'లేదా', 'కాదు', 'వెచ్చిన', 'చెప్పు', 'అర్థం', 'అర్థమయ్యాలి',
            'అవుతుంది', 'చేస్తాడు', 'చేస్తాడు', 'చెప్ప.taobao', 'ఇస్తాడు', 'తీసుకున్నాడు', 'పోయాడు', 'వచ్చినాడు',
            'పొందుతుంది', 'కోరుకుంటాడు', 'మిలుతుంది'
        },
        'kn': {
            'ಏನು', 'ಆಗುತ್ತದೆ', 'ದ', 'ದಿ', '�ાં', 'ಿಂದ', 'ಗೆ', 'ಮತ್ತು', 'ಅಥವ', 'ಇಲ್ಲ', 'ಇದೆ', 'ಇತ್ತು', 'ಇತ್ತು', 'ಇತ್ತು',
            'ಆಗುತ್ತದೆ', 'ಮಾಡುವನು', 'ಮಾಡುವನು', 'ಕೊಟ್ಟನು', 'ತೆಗೆದನು', 'ಹೋದನು', 'ಬಂದನು',
            'ಹೋಗುವನು', 'ಕಡದನು', 'ಮಿಲುವನು'
        },
        'ml': {
            'എന്ത്', 'ആകും', 'ഉടെ', 'ഇൽ', 'നിന്ന്', 'ക്ക്', 'മേൽ', 'ഔर', 'അല്ലെങ്കിൽ', 'ഇല്ല', 'ഉണ്ട്', 'ഉണ്ടായിരുന്നു', 'ഉണ്ടായിരുന്നു', 'ഉണ്ടായിരുന്നു',
            'ആകും', 'ചെയ്യും', 'ചെയ്യും', 'കൊടുത്തു', 'എടുത്തു', 'പോയി', 'വന്നു',
            'പോകും', 'കിട്ടും', 'വേണം'
        },
        'pa': {
            'ਕੀ', 'ਹੈ', 'ਦਾ', 'ਦੀ', 'ਦੇ', 'ਵਿੱਚ', 'ਤੋਂ', 'ਨੂੰ', 'ਤੇ', 'ਅਤੇ', 'ਜਾਂ', 'ਨਹੀਂ', 'ਹਨ', 'ਸੀ', 'ਸੀ', 'ਸੀ',
            'ਹੋਵੇਗਾ', 'ਕਰਦਾ', 'ਕਰਦੀ', 'ਕਰਦੇ', 'ਕੀਤਾ', 'ਕੀਤੀ', 'ਕੀਤੇ', 'ਦਿੱਤਾ', 'ਲਿਆ', 'ਗਿਆ', 'ਆਇਆ',
            'ਜਾਣਾ', 'ਜਾਣੀ', 'ਜਾਣੇ', 'ਚਾਹੁੰਦਾ', 'ਚਾਹੁੰਦੀ', 'ਚਾਹੁੰਦੇ', 'ਮਿਲਦਾ', 'ਮਿਲਦੀ', 'ਮਿਲਦੇ'
        },
    }
    
    # Hindi-specific words (not in Marathi)
    HI_SPECIFIC = {'क्या', 'है', 'का', 'के', 'की', 'में', 'से', 'को', 'पर', 'और', 'या', 'नहीं', 'हैं', 'था', 'थी', 'थे',
                   'होगा', 'होगी', 'होंगे', 'करता', 'करती', 'करते', 'किया', 'दिया', 'लिया', 'गया', 'आई', 'आया',
                   'पता', 'बताओ', 'बताइए', 'जानना', 'समझ', 'समझना', 'पढ़ना', 'लिखना', 'बोलना', 'सुनना'}
    
    # Marathi-specific words (not in Hindi)
    MR_SPECIFIC = {'काय', 'आहे', 'चा', 'चे', 'ची', 'मध्ये', 'पासून', 'ला', 'वर', 'आणि', 'किंवा', 'नाही', 'आहात', 'होते', 'होती',
                   'होईल', 'करतो', 'करते', 'करतात', 'केले', 'केली', 'दिले', 'घेतले', 'गेलं', 'आलं',
                   'जातो', 'जाते', 'जातात', 'पाहिजे', 'मिळतो', 'मिळते', 'मिळतात',
                   'माहिती', 'सांगा', 'सांग', 'समज', 'समजाव', 'वाच', 'लिह', 'बोल', 'ऐक'}

    def __init__(self):
        # Compile patterns for faster matching
        self.compiled_patterns = {}
        for lang, info in self.SCRIPTS.items():
            self.compiled_patterns[lang] = [re.compile(p) for p in info['patterns']]
        
        # Pre-compile word sets for faster lookup
        self.lang_word_sets = {lang: set(words) for lang, words in self.LANGUAGE_WORDS.items()}
        self.hi_specific = self.HI_SPECIFIC
        self.mr_specific = self.MR_SPECIFIC

    def detect(self, text: str) -> LanguageInfo:
        """Detect language of query text with improved Hindi/Marathi disambiguation."""
        if not text or not text.strip():
            return LanguageInfo('unknown', 'Unknown', '', 0.0)

        scores = {}
        total_chars = len([c for c in text if not c.isspace()])

        if total_chars == 0:
            return LanguageInfo('unknown', 'Unknown', '', 0.0)

        # Script-based scoring
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

        # Word-level disambiguation for Devanagari scripts (Hindi vs Marathi)
        devanagari_langs = ['hi', 'mr']
        devanagari_scores = {lang: scores.get(lang, 0) for lang in devanagari_langs if lang in scores}
        
        if len(devanagari_scores) > 1:
            # Both Hindi and Marathi detected - use word-level disambiguation
            text_words = set(text.split())
            hi_word_score = len(text_words & self.hi_specific) / max(len(self.hi_specific), 1)
            mr_word_score = len(text_words & self.mr_specific) / max(len(self.mr_specific), 1)
            
            # Boost the language with more specific words
            if hi_word_score > mr_word_score:
                scores['hi'] = scores.get('hi', 0) + 0.3
            elif mr_word_score > hi_word_score:
                scores['mr'] = scores.get('mr', 0) + 0.3
            # If equal, keep script-based scores (will default to first)

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


def get_supported_language_codes() -> list:
    """Get list of supported language codes."""
    return list(_detector.SCRIPTS.keys())


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