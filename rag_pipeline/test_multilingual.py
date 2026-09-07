#!/usr/bin/env python3
"""
Multilingual test script for Phase 5B.
Tests the complete translation + RAG pipeline.
"""

import json
import time
from rag_engine import create_rag_engine


def run_test(engine, query: str, lang_code: str, test_name: str) -> dict:
    """Run a single test and return results."""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"Query: {query}")
    print(f"Language: {lang_code}")
    
    start = time.time()
    try:
        result = engine.answer(query, answer_language=lang_code)
        elapsed = int((time.time() - start) * 1000)
        
        success = result.confidence != "low" or (result.confidence == "low" and "No relevant context" not in str(result.error))
        
        return {
            "test_name": test_name,
            "query": query,
            "language": lang_code,
            "detected_language": result.detected_language.get("code", "unknown"),
            "answer_language": result.answer_language,
            "success": success,
            "confidence": result.confidence,
            "retrieval_ms": result.retrieval_time_ms,
            "generation_ms": result.generation_time_ms,
            "translation_to_english_ms": result.translation_to_english_ms,
            "translation_to_target_ms": result.translation_to_target_ms,
            "total_ms": result.total_time_ms,
            "sources_count": len(result.sources),
            "has_sources": len(result.sources) > 0,
            "error": result.error
        }
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return {
            "test_name": test_name,
            "query": query,
            "language": lang_code,
            "success": False,
            "error": str(e),
            "elapsed_ms": elapsed
        }


def main():
    print("Initializing RAG engine...")
    engine = create_rag_engine()
    
    # Test cases: (query, language_code, test_name)
    tests = [
        # Basic tests - 3 core languages
        ("What is a patent?", "en", "English_basic"),
        ("पेटेंट क्या है?", "hi", "Hindi_basic"),
        ("पेटंट म्हणजे काय?", "mr", "Marathi_basic"),
        
        # Extended languages
        ("પેટન્ટ શું છે?", "gu", "Gujarati_basic"),
        ("পেটেন্ট কী?", "bn", "Bengali_basic"),
        ("பேட்டண்ட் என்றால் என்ன?", "ta", "Tamil_basic"),
        ("పేటెంట్ అంటే ఏమిటి?", "te", "Telugu_basic"),
        ("ಪೆಟೆಂಟ್ ಎಂದಿಗ?", "kn", "Kannada_basic"),
        ("പെട്ടന്റ് എന്താണ്?", "ml", "Malayalam_basic"),
        ("ਪੇਟੈਂਟ ਕੀ ਹੈ?", "pa", "Punjabi_basic"),
        
        # Legal grounding tests
        ("What does Section 11 of the Patents Act, 1970 deal with?", "en", "English_legal_section11"),
        ("पेटेंट अधिनियम, 1970 की धारा 11 क्या है?", "hi", "Hindi_legal_section11"),
        ("पेटंट कायद्याची कलम ११ काय आहे?", "mr", "Marathi_legal_section11"),
    ]
    
    results = []
    for query, lang, name in tests:
        result = run_test(engine, query, lang, name)
        results.append(result)
        status = "PASS" if result.get("success", False) else "FAIL"
        print(f"  Status: {status}")
        if result.get("success"):
            print(f"  Confidence: {result['confidence']}")
            print(f"  Sources: {result['sources_count']}")
            print(f"  Latency: trans_en={result['translation_to_english_ms']}ms, gen={result['generation_ms']}ms, trans_target={result['translation_to_target_ms']}ms, total={result['total_ms']}ms")
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
    
    print(f"\nPer-language results:")
    lang_results = {}
    for r in results:
        lang = r["language"]
        if lang not in lang_results:
            lang_results[lang] = {"passed": 0, "total": 0}
        lang_results[lang]["total"] += 1
        if r.get("success", False):
            lang_results[lang]["passed"] += 1
    
    for lang, stats in lang_results.items():
        print(f"  {lang}: {stats['passed']}/{stats['total']} passed")
    
    # Save detailed results
    output = {
        "phase": "5B",
        "translation_model": "NLLB-200 (facebook/nllb-200-distilled-600M)",
        "test_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": round(passed/total*100, 1)
        },
        "per_language": lang_results,
        "detailed_results": results
    }
    
    with open("phase5b_multilingual_tests.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed results saved to phase5b_multilingual_tests.json")
    
    return results


if __name__ == "__main__":
    main()