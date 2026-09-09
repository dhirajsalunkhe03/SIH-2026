#!/usr/bin/env python3
"""
End-to-end test script for SIH 2026 PS45 Legal RAG API.
Tests the complete pipeline with representative queries.
"""

import requests
import json
import time
from typing import Dict, Any

API_BASE = "http://127.0.0.1:8000"
CHAT_ENDPOINT = f"{API_BASE}/api/chat"

# Test queries from the requirements
TEST_QUERIES = [
    # 1. English - Legal
    {
        "query": "What is the purpose of the Biological Diversity Act?",
        "language": "en",
        "domain": "all",
        "expected_agent": "abs",
        "category": "English - Legal"
    },
    # 2. Hindi
    {
        "query": "जैव विविधता अधिनियम का उद्देश्य क्या है?",
        "language": "hi",
        "domain": "all",
        "expected_agent": "abs",
        "category": "Hindi"
    },
    # 3. Marathi
    {
        "query": "जैवविविधता कायद्याचा उद्देश काय आहे?",
        "language": "mr",
        "domain": "all",
        "expected_agent": "abs",
        "category": "Marathi"
    },
    # 4. Tamil
    {
        "query": "உயிரியல் பன்முகத்தன்மை சட்டத்தின் நோக்கம் என்ன?",
        "language": "ta",
        "domain": "all",
        "expected_agent": "abs",
        "category": "Tamil"
    },
    # 5. Kannada
    {
        "query": "ಜೈವಿಕ ವೈವಿಧ್ಯತಾ ಕಾಯಿದೆಯ ಉದ್ದೇಶವೇನು?",
        "language": "kn",
        "domain": "all",
        "expected_agent": "abs",
        "category": "Kannada"
    },
    # 6. Malayalam
    {
        "query": "ജൈവവൈവിധ്യ നിയമത്തിന്റെ ഉദ്ദേശ്യം എന്താണ്?",
        "language": "ml",
        "domain": "all",
        "expected_agent": "abs",
        "category": "Malayalam"
    },
    # 7. IP
    {
        "query": "Can traditional knowledge about a medicinal plant be patented?",
        "language": "en",
        "domain": "all",
        "expected_agent": "ip",
        "category": "IP"
    },
    # 8. ABS
    {
        "query": "What is access and benefit sharing?",
        "language": "en",
        "domain": "all",
        "expected_agent": "abs",
        "category": "ABS"
    },
    # 9. TK
    {
        "query": "What is traditional knowledge?",
        "language": "en",
        "domain": "all",
        "expected_agent": "tk",
        "category": "TK"
    },
    # 10. Insufficient evidence - outside corpus
    {
        "query": "What is the legal framework for teleportation technology patents?",
        "language": "en",
        "domain": "all",
        "expected_agent": "ip",
        "category": "Insufficient Evidence"
    },
    # Additional agent routing tests
    {
        "query": "What does Section 11 of the Patents Act deal with?",
        "language": "en",
        "domain": "all",
        "expected_agent": "legal",
        "category": "Legal - Patent Section"
    },
    {
        "query": "What is a geographical indication?",
        "language": "en",
        "domain": "all",
        "expected_agent": "ip",
        "category": "IP - GI"
    },
    {
        "query": "What are the functions of State Biodiversity Boards?",
        "language": "en",
        "domain": "all",
        "expected_agent": "abs",
        "category": "ABS - SBB"
    },
    {
        "query": "What is the relationship between traditional knowledge and biodiversity?",
        "language": "en",
        "domain": "all",
        "expected_agent": "tk",
        "category": "TK - Biodiversity"
    },
]

def run_query(test: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single query and return results with analysis."""
    payload = {
        "query": test["query"],
        "language": test["language"],
        "domain": test["domain"],
        "top_k": 5,
        "concise": True
    }
    
    start = time.time()
    try:
        response = requests.post(CHAT_ENDPOINT, json=payload, timeout=180)
        elapsed = time.time() - start
        
        result = {
            "test": test,
            "http_status": response.status_code,
            "elapsed_seconds": elapsed,
            "success": False,
            "response": None,
            "error": None
        }
        
        if response.status_code == 200:
            data = response.json()
            result["success"] = data.get("success", False)
            result["response"] = data
        else:
            result["error"] = response.text
            
        return result
        
    except requests.exceptions.Timeout:
        return {
            "test": test,
            "http_status": 0,
            "elapsed_seconds": time.time() - start,
            "success": False,
            "response": None,
            "error": "Timeout"
        }
    except Exception as e:
        return {
            "test": test,
            "http_status": 0,
            "elapsed_seconds": time.time() - start,
            "success": False,
            "response": None,
            "error": str(e)
        }

def analyze_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a test result for pass/fail criteria."""
    test = result["test"]
    resp = result["response"]
    
    analysis = {
        "category": test["category"],
        "query": test["query"][:80],
        "language": test["language"],
        "http_status": result["http_status"],
        "passed": False,
        "details": {}
    }
    
    if not result["success"] or not resp:
        analysis["details"]["error"] = result.get("error", "Request failed")
        analysis["passed"] = False
        return analysis
    
    # Extract key fields
    detected_lang = resp.get("detected_language", {}).get("code", "unknown")
    answer_lang = resp.get("answer_language", "unknown")
    agent_domain = resp.get("domain", "unknown")
    agents_used = resp.get("routing_domain", "unknown")
    routing_reason = resp.get("routing_reason", "")
    answer = resp.get("answer", "")
    confidence = resp.get("confidence", "0.0")
    sources = resp.get("sources", [])
    latency = resp.get("latency", {})
    
    # Analysis
    has_answer = bool(answer and answer.strip() and "could not find" not in answer.lower())
    has_sources = len(sources) > 0
    has_metadata = any(s.get("section") or s.get("rule") for s in sources)
    
    # Check if agent routing matches expected
    expected = test["expected_agent"]
    actual_agents = [a.strip() for a in str(agents_used).split(",")] if agents_used else []
    routing_correct = expected in actual_agents or expected in routing_reason.lower()
    
    # Check answer language matches request (or is English for insufficient evidence)
    lang_match = (answer_lang == test["language"]) or (answer_lang == "en" and not has_answer)
    
    analysis["details"] = {
        "detected_language": detected_lang,
        "answer_language": answer_lang,
        "agent_domain": agent_domain,
        "agents_used": actual_agents,
        "routing_reason": routing_reason,
        "routing_correct": routing_correct,
        "answer_non_empty": has_answer,
        "sources_available": has_sources,
        "has_section_metadata": has_metadata,
        "confidence": confidence,
        "latency_ms": latency.get("total_ms", 0),
        "lang_match": lang_match,
        "answer_preview": answer[:200] if answer else ""
    }
    
    # Pass criteria: HTTP 200, success=true, has sources, routing correct, language match
    analysis["passed"] = (
        result["http_status"] == 200 and
        result["success"] and
        has_sources and
        routing_correct and
        lang_match
    )
    
    return analysis

def main():
    print("=" * 80)
    print("SIH 2026 PS45 - End-to-End Validation")
    print("=" * 80)
    
    all_results = []
    analyses = []
    
    for i, test in enumerate(TEST_QUERIES, 1):
        print(f"\n[{i}/{len(TEST_QUERIES)}] {test['category']}: {test['query'][:60]}...")
        result = run_query(test)
        analysis = analyze_result(result)
        all_results.append(result)
        analyses.append(analysis)
        
        status = "PASS" if analysis["passed"] else "FAIL"
        print(f"  Status: {status}")
        print(f"  HTTP: {analysis['http_status']} | Lang: {analysis['details'].get('detected_language')} -> {analysis['details'].get('answer_language')}")
        print(f"  Agents: {analysis['details'].get('agents_used')} | Routing: {'OK' if analysis['details'].get('routing_correct') else 'MISMATCH'}")
        print(f"  Answer: {'YES' if analysis['details'].get('answer_non_empty') else 'NO (abstained)'} | Sources: {'YES' if analysis['details'].get('sources_available') else 'NO'}")
        print(f"  Latency: {analysis['details'].get('latency_ms')}ms | Confidence: {analysis['details'].get('confidence')}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for a in analyses if a["passed"])
    total = len(analyses)
    
    for a in analyses:
        status = "PASS" if a["passed"] else "FAIL"
        print(f"  {status} | {a['category']:25s} | Lang: {a['language']:3s} | Agents: {str(a['details'].get('agents_used')):30s} | Latency: {a['details'].get('latency_ms', 0)}ms")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    # Save detailed results
    with open("e2e_test_results.json", "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "results": all_results,
            "analyses": analyses
        }, f, indent=2)
    
    print("\nDetailed results saved to e2e_test_results.json")
    
    return analyses

if __name__ == "__main__":
    main()