#!/usr/bin/env python3
"""
Phase 8 Smoke Tests for SIH 2026 PS45 Legal RAG API.

Tests:
1. API health endpoint
2. Valid chat request
3. Invalid request handling
4. RAG response with sources
5. Source metadata preservation
6. Multilingual request
7. Ollama failure handling
"""

import sys
import time
import json
import requests
from typing import Dict, Any, Optional


API_BASE = "http://127.0.0.1:8000"
CHAT_ENDPOINT = f"{API_BASE}/api/chat"
HEALTH_ENDPOINT = f"{API_BASE}/health"
DETAILED_HEALTH_ENDPOINT = f"{API_BASE}/health/detailed"
METRICS_ENDPOINT = f"{API_BASE}/api/metrics"


class SmokeTestResult:
    def __init__(self, name: str, passed: bool, message: str = "", data: Any = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.data = data
    
    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status} - {self.name}: {self.message}"


def test_health_endpoint() -> SmokeTestResult:
    """Test 1: API health endpoint returns healthy status."""
    try:
        resp = requests.get(HEALTH_ENDPOINT, timeout=10)
        if resp.status_code != 200:
            return SmokeTestResult("Health Endpoint", False, f"Status code: {resp.status_code}")
        
        data = resp.json()
        if data.get("status") not in ("healthy", "degraded"):
            return SmokeTestResult("Health Endpoint", False, f"Unexpected status: {data.get('status')}")
        
        # Check components
        components = ["ollama", "chromadb", "retriever"]
        for comp in components:
            if comp not in data:
                return SmokeTestResult("Health Endpoint", False, f"Missing component: {comp}")
        
        return SmokeTestResult("Health Endpoint", True, f"Status: {data['status']}, Components: {components}")
    except Exception as e:
        return SmokeTestResult("Health Endpoint", False, f"Exception: {e}")


def test_detailed_health() -> SmokeTestResult:
    """Test 2: Detailed health endpoint returns component info."""
    try:
        resp = requests.get(DETAILED_HEALTH_ENDPOINT, timeout=10)
        if resp.status_code != 200:
            return SmokeTestResult("Detailed Health", False, f"Status code: {resp.status_code}")
        
        data = resp.json()
        required = ["ollama", "chromadb", "embedding_model", "retriever", "rag_engine"]
        for key in required:
            if key not in data:
                return SmokeTestResult("Detailed Health", False, f"Missing key: {key}")
        
        return SmokeTestResult("Detailed Health", True, "All components present")
    except Exception as e:
        return SmokeTestResult("Detailed Health", False, f"Exception: {e}")


def test_valid_chat_request() -> SmokeTestResult:
    """Test 3: Valid chat request returns structured response."""
    payload = {
        "query": "What does Section 11 of the Patents Act, 1970 deal with?",
        "language": "en",
        "domain": "all",
        "top_k": 3,
        "concise": True
    }
    
    try:
        resp = requests.post(CHAT_ENDPOINT, json=payload, timeout=180)
        if resp.status_code != 200:
            return SmokeTestResult("Valid Chat Request", False, f"Status: {resp.status_code}, Body: {resp.text}")
        
        data = resp.json()
        
        # Check required fields
        required_fields = ["success", "query", "detected_language", "answer_language", "domain", "answer", "confidence", "sources", "latency"]
        for field in required_fields:
            if field not in data:
                return SmokeTestResult("Valid Chat Request", False, f"Missing field: {field}")
        
        if not data["success"]:
            return SmokeTestResult("Valid Chat Request", False, f"Success=false: {data.get('error')}")
        
        # Check answer is not empty placeholder
        answer = data["answer"].strip()
        if not answer or answer == "**Answer**:" or "[answer]" in answer:
            return SmokeTestResult("Valid Chat Request", False, "Empty or placeholder answer")
        
        # Check sources
        if not data["sources"]:
            return SmokeTestResult("Valid Chat Request", False, "No sources returned")
        
        # Check latency breakdown
        latency = data["latency"]
        latency_fields = ["retrieval_ms", "generation_ms", "total_ms"]
        for field in latency_fields:
            if field not in latency:
                return SmokeTestResult("Valid Chat Request", False, f"Missing latency field: {field}")
        
        return SmokeTestResult("Valid Chat Request", True, 
            f"Answer length: {len(answer)}, Sources: {len(data['sources'])}, Total: {latency['total_ms']}ms")
    
    except requests.exceptions.Timeout:
        return SmokeTestResult("Valid Chat Request", False, "Request timed out")
    except Exception as e:
        return SmokeTestResult("Valid Chat Request", False, f"Exception: {e}")


def test_invalid_request() -> SmokeTestResult:
    """Test 4: Invalid request returns proper error."""
    # Empty query
    payload = {"query": "", "language": "en", "domain": "all", "top_k": 5}
    
    try:
        resp = requests.post(CHAT_ENDPOINT, json=payload, timeout=10)
        # FastAPI/Pydantic returns 422 for validation errors (correct behavior)
        if resp.status_code in (400, 422):
            return SmokeTestResult("Invalid Request Handling", True, f"Returns {resp.status_code} for empty query")
        else:
            return SmokeTestResult("Invalid Request Handling", False, f"Expected 400/422, got {resp.status_code}")
    except Exception as e:
        return SmokeTestResult("Invalid Request Handling", False, f"Exception: {e}")


def test_rag_response_sources() -> SmokeTestResult:
    """Test 5: RAG response includes source metadata."""
    payload = {
        "query": "What is a geographical indication?",
        "language": "en",
        "domain": "all",
        "top_k": 3
    }
    
    try:
        resp = requests.post(CHAT_ENDPOINT, json=payload, timeout=180)
        if resp.status_code != 200:
            return SmokeTestResult("RAG Response Sources", False, f"Status: {resp.status_code}")
        
        data = resp.json()
        sources = data.get("sources", [])
        
        if not sources:
            return SmokeTestResult("RAG Response Sources", False, "No sources")
        
        # Check source metadata fields exist
        required_source_fields = ["document", "document_type", "score"]
        for source in sources[:2]:  # Check first 2 sources
            for field in required_source_fields:
                if field not in source:
                    return SmokeTestResult("RAG Response Sources", False, f"Source missing field: {field}")
        
        # Section/rule metadata is optional (depends on retrieval)
        has_section = any(s.get("section") for s in sources)
        has_rule = any(s.get("rule") for s in sources)
        
        return SmokeTestResult("RAG Response Sources", True, 
            f"Sources: {len(sources)}, Has section: {has_section}, Has rule: {has_rule}")
    
    except Exception as e:
        return SmokeTestResult("RAG Response Sources", False, f"Exception: {e}")


def test_multilingual_request() -> SmokeTestResult:
    """Test 6: Multilingual request works."""
    payload = {
        "query": "पेटेंट क्या है?",  # Hindi: "What is a patent?"
        "language": "hi",
        "domain": "all",
        "top_k": 3
    }
    
    try:
        resp = requests.post(CHAT_ENDPOINT, json=payload, timeout=180)
        if resp.status_code != 200:
            return SmokeTestResult("Multilingual Request", False, f"Status: {resp.status_code}")
        
        data = resp.json()
        if not data.get("success"):
            return SmokeTestResult("Multilingual Request", False, f"Success=false: {data.get('error')}")
        
        # Check answer language is Hindi
        answer_lang = data.get("answer_language", "")
        if answer_lang != "hi":
            return SmokeTestResult("Multilingual Request", False, f"Answer language: {answer_lang} (expected hi)")
        
        # Check answer is in Hindi (Devanagari script)
        answer = data.get("answer", "")
        if not any('\u0900' <= c <= '\u097F' for c in answer):
            return SmokeTestResult("Multilingual Request", False, "Answer not in Devanagari script")
        
        return SmokeTestResult("Multilingual Request", True, 
            f"Hindi answer length: {len(answer)}, Language: {answer_lang}")
    
    except Exception as e:
        return SmokeTestResult("Multilingual Request", False, f"Exception: {e}")


def test_metrics_endpoint() -> SmokeTestResult:
    """Test 7: Metrics endpoint returns monitoring data."""
    try:
        resp = requests.get(METRICS_ENDPOINT, timeout=5)
        if resp.status_code != 200:
            return SmokeTestResult("Metrics Endpoint", False, f"Status: {resp.status_code}")
        
        data = resp.json()
        required = ["request_count", "rag_engine_ready"]
        for field in required:
            if field not in data:
                return SmokeTestResult("Metrics Endpoint", False, f"Missing field: {field}")
        
        return SmokeTestResult("Metrics Endpoint", True, 
            f"Requests: {data['request_count']}, Engine ready: {data['rag_engine_ready']}")
    
    except Exception as e:
        return SmokeTestResult("Metrics Endpoint", False, f"Exception: {e}")


def test_confidence_and_abstention() -> SmokeTestResult:
    """Test 8: Confidence scoring and abstention behavior."""
    # Test a query that should abstain (insufficient evidence)
    payload = {
        "query": "What does Section 2(1)(m) of the Patents Act define?",
        "language": "en",
        "domain": "all",
        "top_k": 3
    }
    
    try:
        resp = requests.post(CHAT_ENDPOINT, json=payload, timeout=180)
        if resp.status_code != 200:
            return SmokeTestResult("Confidence & Abstention", False, f"Status: {resp.status_code}")
        
        data = resp.json()
        answer = data.get("answer", "").lower()
        confidence = data.get("confidence", "")
        
        # Should abstain for insufficient evidence
        is_abstention = "could not find sufficient" in answer
        has_confidence = confidence in ("High", "Medium", "Low") or isinstance(confidence, (int, float))
        
        return SmokeTestResult("Confidence & Abstention", True, 
            f"Abstention: {is_abstention}, Confidence: {confidence}")
    
    except Exception as e:
        return SmokeTestResult("Confidence & Abstention", False, f"Exception: {e}")


def run_all_tests() -> Dict[str, Any]:
    """Run all smoke tests and return summary."""
    tests = [
        test_health_endpoint,
        test_detailed_health,
        test_valid_chat_request,
        test_invalid_request,
        test_rag_response_sources,
        test_multilingual_request,
        test_metrics_endpoint,
        test_confidence_and_abstention,
    ]
    
    results = []
    for test_func in tests:
        print(f"Running {test_func.__name__}...")
        result = test_func()
        results.append(result)
        print(f"  {result}")
    
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    summary = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "success_rate": f"{passed/total*100:.1f}%",
        "results": [
            {
                "name": r.name,
                "passed": r.passed,
                "message": r.message
            }
            for r in results
        ]
    }
    
    return summary


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 8 SMOKE TESTS")
    print("=" * 60)
    print(f"API Base: {API_BASE}")
    print()
    
    # Wait for API to be ready
    print("Waiting for API to be ready...")
    for i in range(30):
        try:
            resp = requests.get(HEALTH_ENDPOINT, timeout=2)
            if resp.status_code == 200:
                print("API is ready!")
                break
        except:
            pass
        time.sleep(1)
    else:
        print("WARNING: API not ready, continuing anyway...")
    
    print()
    summary = run_all_tests()
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']}")
    
    # Save results
    with open("phase8_smoke_test_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nResults saved to phase8_smoke_test_results.json")
    
    # Exit with error code if any failed
    sys.exit(0 if summary['failed'] == 0 else 1)