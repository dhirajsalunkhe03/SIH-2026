#!/usr/bin/env python3
"""
Ollama utilities for Qwen3:4b interaction using HTTP API.
Handles model availability, prompting, and response cleaning.
"""

import json
import os
import re
import subprocess
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    ollama = None


@dataclass
class OllamaResponse:
    success: bool
    text: str
    error: Optional[str] = None
    model: str = "qwen3:4b"
    latency_ms: int = 0


class OllamaClient:
    """Client for interacting with local Ollama instance via HTTP API."""
    
    def __init__(self, model: str = "qwen3:4b", host: str = "http://localhost:11434",
                 temperature: float = 0.1, top_p: float = 0.9, max_tokens: int = 512, timeout: int = 120):
        self.model = model
        self.host = host
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._available = None
        
        if not OLLAMA_AVAILABLE:
            raise ImportError("ollama Python package not installed. Run: pip install ollama")
        
        # Configure ollama client
        self.client = ollama.Client(host=host)
    
    def check_availability(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            models = self.client.list()
            model_names = [m.model for m in models.models]
            return self.model in model_names
        except Exception:
            return False
    
    def ensure_model(self) -> bool:
        """Ensure the model is available, pull if needed."""
        if self.check_availability():
            return True
        try:
            print(f"Pulling model {self.model}...")
            self.client.pull(self.model)
            return True
        except Exception as e:
            print(f"Failed to pull model: {e}")
            return False
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None
    ) -> OllamaResponse:
        """Generate response from Qwen3 model via HTTP API."""
        start = time.time()
        
        # Use instance defaults if not provided
        temp = temperature if temperature is not None else self.temperature
        top_p_val = top_p if top_p is not None else self.top_p
        max_tok = max_tokens if max_tokens is not None else self.max_tokens
        timeout_val = timeout if timeout is not None else self.timeout
        
        if not self.ensure_model():
            return OllamaResponse(
                success=False,
                text="",
                error=f"Model {self.model} not available",
                latency_ms=int((time.time() - start) * 1000)
            )
        
        # Build messages for chat API
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": temp,
                    "top_p": top_p_val,
                    "num_predict": max_tok,
                    "think": False
                }
            )
            
            latency_ms = int((time.time() - start) * 1000)
            
            msg = response.get('message', {})
            content = msg.get('content', '')
            thinking = msg.get('thinking', '')
            
            # Robust response parsing
            # With think=false, Qwen3 may still put reasoning in thinking field and leave content empty
            # Priority: content field > extracted answer from thinking field
            full_text = content.strip() if content else ""
            
            # If content is empty, try to extract the formatted answer from thinking field
            if not full_text and thinking:
                thinking_clean = thinking.strip()
                # Extract the formatted answer pattern: **Answer**: ... **Sources**: ... **Confidence**: ...
                import re
                # Look for the answer pattern in thinking
                answer_match = re.search(r'\*\*Answer\*\*:.*?(?:\*\*Sources\*\*:.*?)?(?:\*\*Confidence\*\*:.*?)?(?:\n|$)', thinking_clean, re.DOTALL)
                if answer_match:
                    full_text = answer_match.group(0).strip()
                else:
                    # Fallback: check if thinking contains legal terms and looks like an answer
                    thinking_lower = thinking_clean.lower()
                    has_legal_terms = any(term in thinking_lower for term in [
                        'section', 'rule', 'act', 'patent', 'trademark', 'copyright', 
                        'design', 'geographical', 'biodiversity', 'traditional knowledge', 
                        'benefit sharing', 'invention', 'granted under'
                    ])
                    if has_legal_terms and len(thinking_clean) > 50:
                        # But don't use raw thinking - it contains reasoning
                        full_text = ""
            
            # Clean the response (remove any residual thinking tokens, formatting)
            clean_text = self._clean_response(full_text)
            
            # Validate: if still empty after cleaning, it's a failed generation
            if not clean_text:
                return OllamaResponse(
                    success=False,
                    text="",
                    error="Model returned empty response after cleaning",
                    latency_ms=latency_ms
                )
            
            return OllamaResponse(
                success=True,
                text=clean_text,
                latency_ms=latency_ms
            )
            
        except Exception as e:
            return OllamaResponse(
                success=False,
                text="",
                error=f"Generation error: {str(e)}",
                latency_ms=int((time.time() - start) * 1000)
            )
    
    def _clean_response(self, text: str) -> str:
        """Clean Qwen3 response - remove thinking tokens and formatting artifacts."""
        if not text:
            return ""
        
        # Remove Qwen3 chat format tokens
        text = text.replace("<|system|>", "").replace("<|user|>", "").replace("<|assistant|>", "")
        
        # Remove Qwen3 thinking tags (with think=false these should not appear, but handle defensively)
        text = re.sub(r'<\|think\|>.*?<\|endofthink\|>', '', text, flags=re.DOTALL)
        text = re.sub(r'<\|reasoning\|>.*?<\|endofreasoning\|>', '', text, flags=re.DOTALL)
        
        # Remove generic thinking markers
        text = re.sub(r'Thinking\.\.\..*?done thinking\.', '', text, flags=re.DOTALL)
        text = re.sub(r'Thinking\.\.\..*?done thinking', '', text, flags=re.DOTALL)
        
        # Remove reasoning preamble patterns (common in Qwen3 outputs)
        reasoning_patterns = [
            r'^First, I need to[^.]*\.\s*',
            r'^Let me (analyze|look at|examine|check)[^.]*\.\s*',
            r'^Based on the context,\s*',
            r'^Looking at the context,\s*',
            r'^From the context,\s*',
            r'^According to the context,\s*',
            r'^The context (shows|indicates|states)\s+',
            r'^I (need to|will|should)\s+',
            r'^Let me (see|find|determine)\s+',
            r'^We are given.*?(?=\.|$)',
            r'^The context has.*?(?=\.|$)',
            r'^We are given.*?(?=\.|$)',
            r'^Let\'s look at.*?(?=\.|$)',
            r'^Let me review.*?(?=\.|$)',
            r'^The (question|context) is.*?(?=\.|$)',
            # Additional patterns for meta-commentary
            r'^SOURCE \d+[:.]\s*',
            r'^Answer[:.]?\s*',
            r'^Sources[:.]?\s*',
            r'^Confidence[:.]?\s*',
            r'^The question is.*?(?=\.|$)',
            r'^Let me check.*?(?=\.|$)',
        ]
        for pattern in reasoning_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        # Remove any remaining <|...|> tags
        text = re.sub(r'<\|[^|]+\|>', '', text)
        
        # Remove ANSI escape sequences
        text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        text = re.sub(r'\x1b\[\?[0-9]*[hl]', '', text)
        text = re.sub(r'\x1b\[[0-9]*[A-Z]', '', text)
        text = re.sub(r'\[\?25[hl]', '', text)
        text = re.sub(r'\[\?2026[hl]', '', text)
        text = re.sub(r'\[\d+G', '', text)
        text = re.sub(r'\[K', '', text)
        text = re.sub(r'\[\d+[A-Z]', '', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove leading artifacts
        text = text.lstrip('. ,')
        
        return text


def clean_response(text: str) -> str:
    """
    Standalone function to clean Qwen3 response.
    Safe to use independently of OllamaClient.
    """
    if not text:
        return ""
    
    try:
        # Remove Qwen3 chat format tokens
        text = text.replace("<|system|>", "").replace("<|user|>", "").replace("<|assistant|>", "")
        
        # Remove Qwen3 thinking tags
        text = re.sub(r'<\|think\|>.*?<\|endofthink\|>', '', text, flags=re.DOTALL)
        text = re.sub(r'<\|reasoning\|>.*?<\|endofreasoning\|>', '', text, flags=re.DOTALL)
        
        # Remove generic thinking markers
        text = re.sub(r'Thinking\.\.\..*?done thinking\.', '', text, flags=re.DOTALL)
        text = re.sub(r'Thinking\.\.\..*?done thinking', '', text, flags=re.DOTALL)
        
        # Remove reasoning preamble patterns (common in Qwen3 outputs)
        reasoning_patterns = [
            r'^First, I need to[^.]*\.\s*',
            r'^Let me (analyze|look at|examine|check)[^.]*\.\s*',
            r'^Based on the context,\s*',
            r'^Looking at the context,\s*',
            r'^From the context,\s*',
            r'^According to the context,\s*',
            r'^The context (shows|indicates|states)\s+',
            r'^I (need to|will|should)\s+',
            r'^Let me (see|find|determine)\s+',
            r'^We are given.*?(?=\.|$)',
            r'^The context has.*?(?=\.|$)',
            r'^We are given.*?(?=\.|$)',
            r'^Let\'s look at.*?(?=\.|$)',
            r'^Let me review.*?(?=\.|$)',
            r'^The (question|context) is.*?(?=\.|$)',
            # Additional patterns for meta-commentary
            r'^SOURCE \d+[:.]\s*',
            r'^Answer[:.]?\s*',
            r'^Sources[:.]?\s*',
            r'^Confidence[:.]?\s*',
            r'^The question is.*?(?=\.|$)',
            r'^Let me check.*?(?=\.|$)',
        ]
        for pattern in reasoning_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        # Remove any remaining <|...|> tags
        text = re.sub(r'<\|[^|]+\|>', '', text)
        
        # Remove ANSI escape sequences
        text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        text = re.sub(r'\x1b\[\?[0-9]*[hl]', '', text)
        text = re.sub(r'\x1b\[[0-9]*[A-Z]', '', text)
        text = re.sub(r'\[\?25[hl]', '', text)
        text = re.sub(r'\[\?2026[hl]', '', text)
        text = re.sub(r'\[\d+G', '', text)
        text = re.sub(r'\[K', '', text)
        text = re.sub(r'\[\d+[A-Z]', '', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove leading artifacts
        text = text.lstrip('. ,')
        
        return text
    
    except Exception as e:
        # Safe fallback - return stripped text
        if text:
            return text.strip()
        return ""


def test_clean_response():
    """Test the clean_response function with example inputs."""
    test_cases = [
        ("Patent is an invention protected by law.", "Patent is an invention protected by law."),
        ("  Patent is an invention protected by law.  ", "Patent is an invention protected by law."),
        ("पेटेंट क्या है?", "पेटेंट क्या है?"),
        ("पेटंट म्हणजे काय?", "पेटंट म्हणजे काय?"),
        ("No reasoning tags here. Section 3 applies.", "No reasoning tags here. Section 3 applies."),
        ("<|system|>system prompt<|user|>query<|assistant|>answer", "system promptqueryanswer"),
        ("Thinking... some reasoning ...done thinking. Final answer.", "Final answer."),
        ("", ""),
    ]
    
    print("Testing clean_response function:")
    all_passed = True
    for i, (inp, expected) in enumerate(test_cases, 1):
        result = clean_response(inp) if inp is not None else clean_response("")
        passed = result == expected
        if not passed:
            all_passed = False
        status = "✓" if passed else "✗"
        print(f"  Test {i}: {status}")
        if not passed:
            print(f"    Input:    {repr(inp)}")
            print(f"    Expected: {repr(expected)}")
            print(f"    Got:      {repr(result)}")
    
    print(f"\nAll tests passed: {all_passed}")
    return all_passed


def test_ollama() -> Dict[str, Any]:
    """Test Ollama availability and model response."""
    client = OllamaClient()
    
    result = {
        "ollama_available": False,
        "model_available": False,
        "model_name": "qwen3:4b",
        "test_response": None,
        "latency_ms": 0,
        "error": None
    }
    
    try:
        if not client.check_availability():
            result["error"] = "Ollama not running or not accessible"
            return result
        
        result["ollama_available"] = True
        
        if not client.check_availability():
            result["error"] = "qwen3:4b model not found in Ollama"
            return result
        
        result["model_available"] = True
        
        # Test generation
        response = client.generate("Hello, respond briefly.")
        result["latency_ms"] = response.latency_ms
        result["test_response"] = response.text[:200] if response.success else None
        
        if not response.success:
            result["error"] = response.error
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


if __name__ == '__main__':
    import sys
    try:
        test_clean_response()
        print("\nRunning Ollama test...")
        result = test_ollama()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)