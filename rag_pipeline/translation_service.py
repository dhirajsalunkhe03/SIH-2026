#!/usr/bin/env python3
"""
Translation Service for Multilingual Legal RAG.
Uses Meta NLLB-200 (distilled 600M) for English<->Indic translation.

Model: facebook/nllb-200-distilled-600M (open, no auth required)
Supports 200+ languages including all 10 target Indian languages.
"""

import logging
import time
from typing import Dict, Optional, List
from dataclasses import dataclass
from functools import lru_cache

import torch

try:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


logger = logging.getLogger("translation_service")


@dataclass
class TranslationResult:
    """Result of a translation operation."""
    success: bool
    text: str
    error: Optional[str] = None
    latency_ms: int = 0
    source_lang: str = ""
    target_lang: str = ""


@dataclass
class LanguageConfig:
    """Configuration for a supported language."""
    code: str              # Internal code (e.g., 'hi')
    name: str              # Display name (e.g., 'Hindi')
    native_name: str       # Native script name (e.g., 'हिंदी')
    nllb_code: str         # NLLB-200 language code (e.g., 'hin_Deva')
    script: str            # Script name (e.g., 'Devanagari')
    enabled: bool = True


# Language configuration mapping
# Maps internal codes to NLLB-200 codes and metadata
# Verified against NLLB-200 tokenizer language codes
SUPPORTED_LANGUAGES: Dict[str, LanguageConfig] = {
    'en': LanguageConfig(
        code='en',
        name='English',
        native_name='English',
        nllb_code='eng_Latn',
        script='Latin'
    ),
    'hi': LanguageConfig(
        code='hi',
        name='Hindi',
        native_name='हिंदी',
        nllb_code='hin_Deva',
        script='Devanagari'
    ),
    'mr': LanguageConfig(
        code='mr',
        name='Marathi',
        native_name='मराठी',
        nllb_code='mar_Deva',
        script='Devanagari'
    ),
    'gu': LanguageConfig(
        code='gu',
        name='Gujarati',
        native_name='ગુજરાતી',
        nllb_code='guj_Gujr',
        script='Gujarati'
    ),
    'bn': LanguageConfig(
        code='bn',
        name='Bengali',
        native_name='বাংলা',
        nllb_code='ben_Beng',
        script='Bengali'
    ),
    'ta': LanguageConfig(
        code='ta',
        name='Tamil',
        native_name='தமிழ்',
        nllb_code='tam_Taml',
        script='Tamil'
    ),
    'te': LanguageConfig(
        code='te',
        name='Telugu',
        native_name='తెలుగు',
        nllb_code='tel_Telu',
        script='Telugu'
    ),
    'kn': LanguageConfig(
        code='kn',
        name='Kannada',
        native_name='ಕನ್ನಡ',
        nllb_code='kan_Knda',
        script='Kannada'
    ),
    'ml': LanguageConfig(
        code='ml',
        name='Malayalam',
        native_name='മലയാളം',
        nllb_code='mal_Mlym',
        script='Malayalam'
    ),
    'pa': LanguageConfig(
        code='pa',
        name='Punjabi',
        native_name='ਪੰਜਾਬੀ',
        nllb_code='pan_Guru',
        script='Gurmukhi'
    ),
}

# Known translation quality issues for specific languages
# These languages have lower NLLB-200 translation quality for short legal queries
TRANSLATION_QUALITY_WARNING = {'kn', 'ml'}

# Pre-translation normalization for languages with known quality issues
# Maps common legal terms in native script to English equivalents
# This runs BEFORE NLLB-200 translation to improve accuracy
PRE_TRANSLATION_MAP: Dict[str, Dict[str, str]] = {
    'kn': {
        'ಪೆಟೆಂಟ್': 'patent',
        'ಪೆಟೆಂಟ್‌ಗಳು': 'patents',
        'ಪೆಟೆಂಟ್ ಕಾನೂನು': 'patent law',
        'ಪೆಟೆಂಟ್ ಅಧಿನಿಯಮ': 'patent act',
        'ಕಲಮ': 'section',
        'ಧಾರಾ': 'section',
        'ಕायदೆ': 'act',
        'ಅಧಿನಿಯಮ': 'act',
        'ನ್ಯಾಯಾಂಗ': 'legal',
        'ಗೌಪ್ಯ': 'confidential',
        'ಔಷಧಿ': 'drug',
        'ಔಷಧಿಗಳು': 'drugs',
        'ವೈದ್ಯಕೀಯ': 'medical',
        'ರೋಗ': 'disease',
        'ಚಿಕಿತ್ಸೆ': 'treatment',
        'ಎಂದಿಗ': 'what is',
        'என்று': 'what is',
        'ಅর্থ': 'meaning',
        'ಅರ್ಥವಾಗುತ್ತದೆ': 'means',
        'ಯಾವುದೇ': 'any',
        'ಹೇಗೆ': 'how',
        'ಏನು': 'what',
        'ಯಾಕೆ': 'why',
        'ಯಾವಾಗ': 'when',
        'ಎಲ್ಲಿ': 'where',
        'ಯಾರು': 'who',
    },
    'ml': {
        'പെട്ടന്റ്': 'patent',
        'പെട്ടന്റുകള്': 'patents',
        'പെട്ടന്റ് നിയമം': 'patent law',
        'പെട്ടന്റ് നിയമം': 'patent act',
        'വകുപ്പ്': 'section',
        'ധാര': 'section',
        'നിയമം': 'act',
        'കാനൂന്': 'law',
        'നിയമപരമായ': 'legal',
        'രഹസ്യമായ': 'confidential',
        'മരുന്ന്': 'drug',
        'മരുന്നുകള്': 'drugs',
        'വൈദ്യ': 'medical',
        'രോഗം': 'disease',
        'ചികിത്സ': 'treatment',
        'എന്താണ്': 'what is',
        'എന്താണ്': 'what is',
        'അര്‍ത്ഥം': 'meaning',
        'അര്‍ത്ഥമാക്കുന്നു': 'means',
        'എന്ത്': 'what',
        'എങ്ങിനെ': 'how',
        'എന്തുകൊണ്ട്': 'why',
        'അപ്പോള്': 'when',
        'എവിടെ': 'where',
        'ആര്': 'who',
    },
}


class TranslationService:
    """Main translation service using NLLB-200 model."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.device = self._get_device()
        self.model = None
        self.tokenizer = None
        self._models_loaded = False
        self._use_cpu = False
        
        # Model name (distilled 600M version for efficiency on 6GB GPU)
        self.model_name = self.config.get(
            'model_name',
            'facebook/nllb-200-distilled-600M'
        )
        
        # Use float16 on CUDA for memory efficiency
        self.torch_dtype = torch.float16 if self.device == 'cuda' else torch.float32
        
        # CPU fallback config
        self.cpu_fallback = self.config.get('cpu_fallback', True)
    
    def _get_device(self) -> str:
        """Determine the best available device."""
        if torch.cuda.is_available():
            return 'cuda'
        return 'cpu'
    
    def _load_model_on_device(self, device: str, dtype):
        """Load model on specific device."""
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            self.model_name,
            dtype=dtype,
            low_cpu_mem_usage=True
        ).to(device)
        self.model.eval()
    
    def load_models(self):
        """Load translation model lazily (singleton pattern) with CPU fallback on OOM."""
        if self._models_loaded:
            return
        
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "transformers not installed. Run: pip install transformers accelerate"
            )
        
        target_device = self.device
        target_dtype = self.torch_dtype
        
        logger.info(f"Loading NLLB-200 translation model on {target_device}...")
        
        try:
            self._load_model_on_device(target_device, target_dtype)
            
        except RuntimeError as e:
            if "out of memory" in str(e).lower() and self.cpu_fallback and target_device == 'cuda':
                logger.warning(f"CUDA OOM loading translation model, falling back to CPU: {e}")
                # Clear CUDA cache
                torch.cuda.empty_cache()
                target_device = 'cpu'
                target_dtype = torch.float32
                try:
                    self._load_model_on_device(target_device, target_dtype)
                    self._use_cpu = True
                except Exception as e2:
                    logger.error(f"Failed to load NLLB-200 on CPU fallback: {e2}")
                    raise
            else:
                logger.error(f"Failed to load NLLB-200 model: {e}")
                raise
        
        self.device = target_device
        self.torch_dtype = target_dtype
        self._models_loaded = True
        logger.info(f"NLLB-200 model loaded successfully on {self.device}" + (" (CPU fallback)" if self._use_cpu else ""))
    
    def _translate(
        self,
        text: str,
        src_lang: str,
        tgt_lang: str
    ) -> str:
        """Translate a single text using NLLB-200."""
        if not self._models_loaded:
            self.load_models()
        
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Translation model not loaded")
        
        # Tokenize with source language
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
            src_lang=src_lang
        ).to(self.device)
        
        # Generate translation
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                forced_bos_token_id=self.tokenizer.convert_tokens_to_ids(tgt_lang),
                max_length=512,
                num_beams=5,
                early_stopping=True
            )
        
        # Decode
        result = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
        return result
    
    def translate_to_english(self, text: str, source_language: str) -> TranslationResult:
        """Translate text from source language to English."""
        start = time.time()
        
        if source_language == 'en':
            return TranslationResult(
                success=True,
                text=text,
                latency_ms=int((time.time() - start) * 1000),
                source_lang='en',
                target_lang='en'
            )
        
        lang_config = SUPPORTED_LANGUAGES.get(source_language)
        if not lang_config:
            return TranslationResult(
                success=False,
                text="",
                error=f"Unsupported source language: {source_language}",
                latency_ms=int((time.time() - start) * 1000),
                source_lang=source_language,
                target_lang='en'
            )
        
        try:
            # Apply pre-translation normalization for known quality issues
            normalized_text = pre_translate_query(text, source_language)
            
            translated = self._translate(normalized_text, lang_config.nllb_code, 'eng_Latn')
            
            return TranslationResult(
                success=True,
                text=translated,
                latency_ms=int((time.time() - start) * 1000),
                source_lang=source_language,
                target_lang='en'
            )
        except Exception as e:
            logger.error(f"Translation to English failed: {e}")
            return TranslationResult(
                success=False,
                text="",
                error=f"Translation error: {str(e)}",
                latency_ms=int((time.time() - start) * 1000),
                source_lang=source_language,
                target_lang='en'
            )
    
    def translate_from_english(self, text: str, target_language: str) -> TranslationResult:
        """Translate text from English to target language."""
        start = time.time()
        
        if target_language == 'en':
            return TranslationResult(
                success=True,
                text=text,
                latency_ms=int((time.time() - start) * 1000),
                source_lang='en',
                target_lang='en'
            )
        
        lang_config = SUPPORTED_LANGUAGES.get(target_language)
        if not lang_config:
            return TranslationResult(
                success=False,
                text="",
                error=f"Unsupported target language: {target_language}",
                latency_ms=int((time.time() - start) * 1000),
                source_lang='en',
                target_lang=target_language
            )
        
        try:
            translated = self._translate(text, 'eng_Latn', lang_config.nllb_code)
            
            return TranslationResult(
                success=True,
                text=translated,
                latency_ms=int((time.time() - start) * 1000),
                source_lang='en',
                target_lang=target_language
            )
        except Exception as e:
            logger.error(f"Translation from English failed: {e}")
            return TranslationResult(
                success=False,
                text="",
                error=f"Translation error: {str(e)}",
                latency_ms=int((time.time() - start) * 1000),
                source_lang='en',
                target_lang=target_language
            )


# Global service instance (singleton)
_translation_service: Optional[TranslationService] = None


def get_translation_service(config: Optional[Dict] = None) -> TranslationService:
    """Get or create global translation service instance."""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService(config)
    return _translation_service


def translate_to_english(text: str, source_language: str) -> TranslationResult:
    """Convenience function to translate to English."""
    service = get_translation_service()
    return service.translate_to_english(text, source_language)


def translate_from_english(text: str, target_language: str) -> TranslationResult:
    """Convenience function to translate from English."""
    service = get_translation_service()
    return service.translate_from_english(text, target_language)


def get_language_config(lang_code: str) -> Optional[LanguageConfig]:
    """Get language configuration by internal code."""
    return SUPPORTED_LANGUAGES.get(lang_code)


def get_supported_languages() -> Dict[str, LanguageConfig]:
    """Get all supported languages."""
    return {k: v for k, v in SUPPORTED_LANGUAGES.items() if v.enabled}


def get_nllb_code(lang_code: str) -> Optional[str]:
    """Get NLLB-200 code for internal language code."""
    config = SUPPORTED_LANGUAGES.get(lang_code)
    return config.nllb_code if config else None


def pre_translate_query(text: str, source_language: str) -> str:
    """
    Apply pre-translation normalization for languages with known NLLB-200 quality issues.
    This replaces common legal terms in native script with English equivalents
    before sending to the NLLB-200 model.
    """
    if source_language not in PRE_TRANSLATION_MAP:
        return text
    
    translation_map = PRE_TRANSLATION_MAP[source_language]
    result = text
    
    # Sort by length descending to match longer phrases first
    for native_term, english_term in sorted(translation_map.items(), key=lambda x: -len(x[0])):
        if native_term in result:
            result = result.replace(native_term, english_term)
    
    return result


if __name__ == '__main__':
    # Quick test
    import sys
    
    if not TRANSFORMERS_AVAILABLE:
        print("transformers not available. Install with: pip install transformers accelerate")
        sys.exit(1)
    
    service = get_translation_service()
    
    # Test English -> Hindi
    print("Testing English -> Hindi...")
    result = service.translate_from_english("What is a patent?", "hi")
    print(f"  Success: {result.success}")
    print(f"  Text: {result.text}")
    print(f"  Latency: {result.latency_ms}ms")
    if result.error:
        print(f"  Error: {result.error}")
    
    # Test Hindi -> English
    print("\nTesting Hindi -> English...")
    result = service.translate_to_english("पेटेंट क्या है?", "hi")
    print(f"  Success: {result.success}")
    print(f"  Text: {result.text}")
    print(f"  Latency: {result.latency_ms}ms")
    if result.error:
        print(f"  Error: {result.error}")
    
    # Test English -> Marathi
    print("\nTesting English -> Marathi...")
    result = service.translate_from_english("What is a patent?", "mr")
    print(f"  Success: {result.success}")
    print(f"  Text: {result.text}")
    print(f"  Latency: {result.latency_ms}ms")
    if result.error:
        print(f"  Error: {result.error}")
    
    # Test Marathi -> English
    print("\nTesting Marathi -> English...")
    result = service.translate_to_english("पेटंट म्हणजे काय?", "mr")
    print(f"  Success: {result.success}")
    print(f"  Text: {result.text}")
    print(f"  Latency: {result.latency_ms}ms")
    if result.error:
        print(f"  Error: {result.error}")