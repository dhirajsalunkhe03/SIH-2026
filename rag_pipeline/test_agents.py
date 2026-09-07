#!/usr/bin/env python3
"""
Test script for Phase 6 multi-agent architecture.
Tests single-domain, multi-domain, and multilingual agent routing.
"""

import json
import time
from rag_engine import create_rag_engine


def run_test(engine, query: str, expected_agents: list, test_name: str, lang: str = "en") -> dict:
    """Run a single test and return results."""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"Query: {query}")
    print(f"Language: {lang}")
    print(f"Expected agents: {expected_agents}")
    
    start = time.time()
    try:
        result = engine.answer(query, answer_language=lang)
        elapsed = int((time.time() - start) * 1000)
        
        # Get routing info if available
        agents_used = getattr(result, 'agents_used', [])
        routing_domain = getattr(result, 'routing_domain', None)
        routing_reason = getattr(result, 'routing_reason', None)
        
        # Check if expected agents were used (for single domain tests)
        success = True
        if expected_agents:
            # For single domain, check if primary expected agent was used
            if len(expected_agents) == 1 and expected_agents[0] not in agents_used:
                success = False
            # For multi-domain, check if all expected agents were used
            elif len(expected_agents) > 1:
                for exp in expected_agents:
                    if exp not in agents_used:
                        success = False
                        break
        
        return {
            "test_name": test_name,
            "query": query,
            "language": lang,
            "expected_agents": expected_agents,
            "agents_used": agents_used,
            "routing_domain": routing_domain,
            "routing_reason": routing_reason,
            "success": success,
            "confidence": result.confidence,
            "sources_count": len(result.sources) if hasattr(result, 'sources') else 0,
            "total_ms": result.total_time_ms if hasattr(result, 'total_time_ms') else elapsed,
            "error": None
        }
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return {
            "test_name": test_name,
            "query": query,
            "language": lang,
            "expected_agents": expected_agents,
            "success": False,
            "error": str(e),
            "elapsed_ms": elapsed
        }


def main():
    print("Initializing RAG engine...")
    engine = create_rag_engine()
    
    # Test cases: (query, expected_agents, test_name, language)
    tests = [
        # Single-domain tests
        ("What is a patent?", ["ip"], "Single_domain_IP_patent", "en"),
        ("What is a geographical indication?", ["ip"], "Single_domain_IP_GI", "en"),
        ("What is access and benefit sharing?", ["abs"], "Single_domain_ABS", "en"),
        ("What is traditional knowledge?", ["tk"], "Single_domain_TK", "en"),
        ("What does Section 11 of the Patents Act deal with?", ["ip", "legal"], "Single_domain_Legal_IP_section11", "en"),
        
        # Multi-domain tests
        ("Can traditional knowledge be protected through patents?", ["tk", "ip"], "Multi_domain_TK_IP", "en"),
        ("What obligations apply when accessing biological resources with traditional knowledge?", ["abs", "tk", "legal"], "Multi_domain_ABS_TK_Legal", "en"),
        ("What are the patent implications of traditional knowledge?", ["ip", "tk"], "Multi_domain_IP_TK", "en"),
        
        # Multilingual tests
        ("पेटेंट क्या है?", ["ip"], "Hindi_IP_patent", "hi"),
        ("पेटंट म्हणजे काय?", ["ip"], "Marathi_IP_patent", "mr"),
        ("पारंपरिक ज्ञान क्या है?", ["tk"], "Hindi_TK", "hi"),
        ("पारंपरिक ज्ञान काय आहे?", ["tk"], "Marathi_TK", "mr"),
        ("जैविक विविधता अधिनियम के तहत लाभ साझाकरण क्या है?", ["abs"], "Hindi_ABS", "hi"),
    ]
    
    results = []
    for query, expected, name, lang in tests:
        result = run_test(engine, query, expected, name, lang)
        results.append(result)
        status = "PASS" if result.get("success", False) else "FAIL"
        print(f"  Status: {status}")
        if result.get("success"):
            print(f"  Agents used: {result['agents_used']}")
            print(f"  Routing: {result['routing_reason']}")
            print(f"  Confidence: {result['confidence']}")
            print(f"  Sources: {result['sources_count']}")
        else:
            print(f"  Error: {result.get('error', 'Unknown')}")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for r in results if r.get("success", False))
    total = len(results)
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success rate: {passed/total*100:.1f}%")
    
    # Per-category results
    categories = {
        "Single-domain": [r for r in results if "Single_domain" in r["test_name"]],
        "Multi-domain": [r for r in results if "Multi_domain" in r["test_name"]],
        "Multilingual": [r for r in results if "Hindi" in r["test_name"] or "Marathi" in r["test_name"]],
    }
    
    for cat, cat_results in categories.items():
        cat_passed = sum(1 for r in cat_results if r.get("success", False))
        cat_total = len(cat_results)
        print(f"\n{cat}: {cat_passed}/{cat_total} passed")
        for r in cat_results:
            status = "✓" if r.get("success", False) else "✗"
            print(f"  {status} {r['test_name']}: agents={r.get('agents_used', [])}")
    
    # Legal grounding test
    print(f"\n{'='*60}")
    print("LEGAL GROUNDING TEST")
    print(f"{'='*60}")
    
    legal_query = "What does Section 11 of the Patents Act, 1970 deal with?"
    print(f"Query: {legal_query}")
    result = engine.answer(legal_query)
    print(f"Agents used: {getattr(result, 'agents_used', 'N/A')}")
    print(f"Confidence: {result.confidence}")
    print(f"Sources: {len(result.sources) if hasattr(result, 'sources') else 'N/A'}")
    
    # Check for section preservation
    section_preserved = False
    for src in result.sources:
        if src.get('section') == '11' or '11' in str(src.get('section', '')):
            section_preserved = True
            break
    print(f"Section 11 preserved in sources: {section_preserved}")
    print(f"Answer preview: {result.answer[:500]}...")
    
    # Save detailed results
    output = {
        "phase": "6",
        "test_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": round(passed/total*100, 1)
        },
        "categories": {cat: len(res) for cat, res in categories.items()},
        "detailed_results": results,
        "legal_grounding": {
            "query": legal_query,
            "agents_used": getattr(result, 'agents_used', 'N/A'),
            "confidence": result.confidence,
            "sources_count": len(result.sources) if hasattr(result, 'sources') else 0,
            "section_11_preserved": section_preserved
        }
    }
    
    with open("phase6_agent_tests.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed results saved to phase6_agent_tests.json")
    
    return results


if __name__ == "__main__":
    main()