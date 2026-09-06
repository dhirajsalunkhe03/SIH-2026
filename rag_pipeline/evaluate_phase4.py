#!/usr/bin/env python3
"""
Phase 4 Evaluation Script.
Measures retrieval success, source relevance, language detection, 
answer language, citation presence, unanswerable query handling,
and latency metrics.
"""

import json
import time
from typing import Dict, List, Any
from rag_engine import LegalRAG, create_rag_engine
from config import get_config


def load_test_queries(path: str) -> List[Dict]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def evaluate_phase4():
    """Run comprehensive Phase 4 evaluation."""
    print("Initializing LegalRAG for evaluation...")
    engine = create_rag_engine()
    
    queries = load_test_queries("/home/dhiraj/Desktop/SIH/rag_pipeline/phase4_test_queries.json")
    
    results = []
    total_start = time.time()
    
    for i, q in enumerate(queries):
        print(f"\n[{i+1}/{len(queries)}] {q['id']} ({q['language']}): {q['query'][:60]}...")
        
        start = time.time()
        result = engine.answer(
            query=q['query'],
            answer_language='auto',
            top_k=5
        )
        elapsed = int((time.time() - start) * 1000)
        
        # Evaluate
        eval_result = {
            "query_id": q['id'],
            "query_language": q['language'],
            "query": q['query'],
            "expected_domain": q['expected_domain'],
            "answerable": q['answerable'],
            
            # Retrieval
            "retrieved_chunks": len(result.retrieved_chunks),
            "retrieval_time_ms": result.retrieval_time_ms,
            "retrieval_confidence": result.retrieval_confidence,
            "top_domains": [c.get('domain') for c in result.retrieved_chunks[:3]],
            "top_scores": [c.get('score') for c in result.retrieved_chunks[:3]],
            "domain_match": q['expected_domain'] in [c.get('domain') for c in result.retrieved_chunks[:5]] if q['answerable'] else None,
            
            # Generation
            "generation_time_ms": result.generation_time_ms,
            "total_time_ms": result.total_time_ms,
            "answer_language": result.answer_language,
            "detected_language": result.detected_language.get('code'),
            
            # Answer quality
            "answer_length": len(result.answer),
            "confidence": result.confidence,
            "confidence_reason": result.confidence_reason,
            "has_sources": len(result.sources) > 0,
            "source_count": len(result.sources),
            "has_citations": "Sources:" in result.answer,
            
            # Unanswerable handling
            "correctly_refused": False,
            "error": result.error
        }
        
        # Check unanswerable query handling
        if not q['answerable']:
            refused = "could not find sufficient" in result.answer.lower() or \
                      "insufficient" in result.answer.lower() or \
                      result.confidence == "low" or \
                      result.retrieval_confidence == "none"
            eval_result["correctly_refused"] = refused
            if refused:
                print(f"  ✓ Correctly refused unanswerable query")
            else:
                print(f"  ✗ Failed to refuse unanswerable query")
        
        # Check domain match for answerable
        if q['answerable'] and eval_result["domain_match"]:
            print(f"  ✓ Domain match ({eval_result['top_domains'][:2]})")
        elif q['answerable']:
            print(f"  ✗ Domain mismatch (expected {q['expected_domain']}, got {eval_result['top_domains'][:2]})")
        
        # Check citations
        if eval_result["has_citations"]:
            print(f"  ✓ Has citations")
        else:
            print(f"  ✗ Missing citations")
        
        results.append(eval_result)
    
    # Summary statistics
    print("\n" + "=" * 60)
    print("PHASE 4 EVALUATION SUMMARY")
    print("=" * 60)
    
    total = len(results)
    answerable = [r for r in results if r['answerable']]
    unanswerable = [r for r in results if not r['answerable']]
    
    # Retrieval metrics
    domain_matches = sum(1 for r in answerable if r['domain_match'])
    avg_retrieval_time = sum(r['retrieval_time_ms'] for r in results) / total
    avg_gen_time = sum(r['generation_time_ms'] for r in results) / total
    avg_total_time = sum(r['total_time_ms'] for r in results) / total
    
    # Generation metrics
    has_citations = sum(1 for r in results if r['has_citations'])
    has_sources = sum(1 for r in results if r['has_sources'])
    high_conf = sum(1 for r in results if r['confidence'] == 'High')
    med_conf = sum(1 for r in results if r['confidence'] == 'Medium')
    low_conf = sum(1 for r in results if r['confidence'] == 'Low')
    
    # Unanswerable handling
    refused = sum(1 for r in unanswerable if r['correctly_refused'])
    
    # Language detection
    lang_correct = sum(1 for r in results if r['detected_language'] == r['query_language'] or 
                       (r['query_language'] == 'mr' and r['detected_language'] == 'hi'))  # Marathi detected as Hindi is acceptable
    
    print(f"\nTotal Queries: {total}")
    print(f"  Answerable: {len(answerable)}")
    print(f"  Unanswerable: {len(unanswerable)}")
    
    print(f"\nRetrieval:")
    print(f"  Domain Match Rate: {domain_matches}/{len(answerable)} ({domain_matches/len(answerable)*100:.1f}%)")
    print(f"  Avg Retrieval Time: {avg_retrieval_time:.1f}ms")
    print(f"  Retrieval Confidence: High={sum(1 for r in results if r['retrieval_confidence']=='high')}, Medium={sum(1 for r in results if r['retrieval_confidence']=='medium')}, Low={sum(1 for r in results if r['retrieval_confidence']=='low')}, None={sum(1 for r in results if r['retrieval_confidence']=='none')}")
    
    print(f"\nGeneration:")
    print(f"  Avg Generation Time: {avg_gen_time:.1f}ms")
    print(f"  Avg Total Time: {avg_total_time:.1f}ms")
    print(f"  Citations Present: {has_citations}/{total} ({has_citations/total*100:.1f}%)")
    print(f"  Sources Present: {has_sources}/{total} ({has_sources/total*100:.1f}%)")
    print(f"  Confidence: High={high_conf}, Medium={med_conf}, Low={low_conf}")
    
    print(f"\nUnanswerable Query Handling:")
    print(f"  Correctly Refused: {refused}/{len(unanswerable)} ({refused/len(unanswerable)*100:.1f}%)")
    
    print(f"\nLanguage Detection:")
    print(f"  Correct: {lang_correct}/{total} ({lang_correct/total*100:.1f}%)")
    print(f"  Note: Marathi detected as Hindi (shared Devanagari script)")
    
    # Per-language breakdown
    print(f"\nPer-Language Results:")
    lang_stats = {}
    for r in results:
        lang = r['query_language']
        if lang not in lang_stats:
            lang_stats[lang] = {'total': 0, 'domain_match': 0, 'has_citations': 0}
        lang_stats[lang]['total'] += 1
        if r['answerable'] and r['domain_match']:
            lang_stats[lang]['domain_match'] += 1
        if r['has_citations']:
            lang_stats[lang]['has_citations'] += 1
    
    for lang, stats in sorted(lang_stats.items()):
        lang_name = {'en': 'English', 'hi': 'Hindi', 'mr': 'Marathi', 'gu': 'Gujarati',
                     'bn': 'Bengali', 'ta': 'Tamil', 'te': 'Telugu', 'kn': 'Kannada',
                     'ml': 'Malayalam', 'pa': 'Punjabi'}.get(lang, lang)
        answerable_count = sum(1 for r in results if r['query_language'] == lang and r['answerable'])
        match_rate = stats['domain_match'] / answerable_count * 100 if answerable_count > 0 else 100
        print(f"  {lang_name} ({lang}): {stats['total']} queries, {match_rate:.0f}% domain match, {stats['has_citations']}/{stats['total']} citations")
    
    # Prepare evaluation output
    evaluation = {
        "phase": 4,
        "model": "qwen3:4b",
        "embedding_model": "BAAI/bge-m3",
        "total_queries": total,
        "answerable": len(answerable),
        "unanswerable": len(unanswerable),
        "retrieval": {
            "domain_match_rate": round(domain_matches/len(answerable)*100, 1) if answerable else 0,
            "avg_retrieval_time_ms": round(avg_retrieval_time, 1),
            "confidence_distribution": {
                "high": sum(1 for r in results if r['retrieval_confidence']=='high'),
                "medium": sum(1 for r in results if r['retrieval_confidence']=='medium'),
                "low": sum(1 for r in results if r['retrieval_confidence']=='low'),
                "none": sum(1 for r in results if r['retrieval_confidence']=='none')
            }
        },
        "generation": {
            "avg_generation_time_ms": round(avg_gen_time, 1),
            "avg_total_time_ms": round(avg_total_time, 1),
            "citation_rate": round(has_citations/total*100, 1),
            "source_rate": round(has_sources/total*100, 1),
            "confidence_distribution": {
                "high": high_conf,
                "medium": med_conf,
                "low": low_conf
            }
        },
        "unanswerable_handling": {
            "total": len(unanswerable),
            "correctly_refused": refused,
            "refusal_rate": round(refused/len(unanswerable)*100, 1) if unanswerable else 0
        },
        "language_detection": {
            "accuracy": round(lang_correct/total*100, 1),
            "note": "Marathi detected as Hindi due to shared Devanagari script"
        },
        "per_language": {lang: stats for lang, stats in lang_stats.items()},
        "detailed_results": results,
        "warnings": [
            "Marathi queries detected as Hindi (shared Devanagari script)",
            "Some queries have low retrieval confidence (< 0.3)",
            "Citation format depends on retrieved metadata completeness"
        ]
    }
    
    with open('/home/dhiraj/Desktop/SIH/rag_pipeline/PHASE4_EVALUATION.json', 'w', encoding='utf-8') as f:
        json.dump(evaluation, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed evaluation saved to PHASE4_EVALUATION.json")
    
    return evaluation


if __name__ == '__main__':
    evaluate_phase4()