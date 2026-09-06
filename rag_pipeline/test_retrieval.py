#!/usr/bin/env python3
"""
Test retrieval across languages and domains.
"""

import json
from typing import List, Dict, Any
from retriever import LegalRetriever


def load_test_queries(path: str) -> List[Dict]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_retrieval_tests():
    retriever = LegalRetriever()
    retriever.load()
    
    queries = load_test_queries("/home/dhiraj/Desktop/SIH/rag_pipeline/test_queries.json")
    
    results = []
    cross_lang_results = []
    
    for q in queries:
        print(f"\n{'='*60}")
        print(f"Test {q['id']} ({q['language']}): {q['query']}")
        print(f"Expected Domain: {q['expected_domain']}")
        
        result = retriever.search_multilingual(q['query'], top_k=5)
        
        # Check if expected domain appears in top results
        found_domains = [r['domain'] for r in result['results']]
        domain_match = q['expected_domain'] in found_domains
        
        print(f"Detected Language: {result['detected_language']['name']} ({result['detected_language']['code']})")
        print(f"Domain Match: {domain_match} (Found: {found_domains[:3]})")
        
        for r in result['results'][:3]:
            sec = f"Sec {r['section_number']}" if r['section_number'] else ""
            rule = f"Rule {r['rule_number']}" if r['rule_number'] else ""
            print(f"  {r['rank']}. [{r['score']}] {r['document']} {sec} {rule} | Domain: {r['domain']} | Lang: {r['language']}")
        
        # Track cross-language retrieval
        query_lang = q['language']
        result_langs = [r['language'] for r in result['results']]
        is_cross_lang = any(rl != query_lang and rl != 'MISSING' for rl in result_langs)
        
        results.append({
            'query_id': q['id'],
            'query_language': q['language'],
            'query': q['query'],
            'expected_domain': q['expected_domain'],
            'detected_language': result['detected_language']['code'],
            'domain_match': domain_match,
            'found_domains': found_domains[:5],
            'is_cross_language': is_cross_lang,
            'result_languages': result_langs[:5],
            'top_scores': [r['score'] for r in result['results'][:5]]
        })
        
        if is_cross_lang:
            cross_lang_results.append({
                'query_id': q['id'],
                'query_language': query_lang,
                'retrieved_languages': result_langs[:5],
                'top_result': result['results'][0] if result['results'] else None
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("RETRIEVAL TEST SUMMARY")
    print(f"{'='*60}")
    total = len(results)
    domain_matches = sum(1 for r in results if r['domain_match'])
    cross_lang_count = len(cross_lang_results)
    
    print(f"Total queries: {total}")
    print(f"Domain matches: {domain_matches}/{total} ({domain_matches/total*100:.1f}%)")
    print(f"Cross-language retrievals: {cross_lang_count}/{total} ({cross_lang_count/total*100:.1f}%)")
    
    # Per-language breakdown
    lang_stats = {}
    for r in results:
        lang = r['query_language']
        if lang not in lang_stats:
            lang_stats[lang] = {'total': 0, 'matches': 0, 'cross_lang': 0}
        lang_stats[lang]['total'] += 1
        if r['domain_match']:
            lang_stats[lang]['matches'] += 1
        if r['is_cross_language']:
            lang_stats[lang]['cross_lang'] += 1
    
    print(f"\nPer-language breakdown:")
    for lang, stats in lang_stats.items():
        lang_name = {'en': 'English', 'hi': 'Hindi', 'mr': 'Marathi', 'gu': 'Gujarati', 
                     'bn': 'Bengali', 'ta': 'Tamil', 'te': 'Telugu', 'kn': 'Kannada', 
                     'ml': 'Malayalam', 'pa': 'Punjabi'}.get(lang, lang)
        print(f"  {lang_name} ({lang}): {stats['matches']}/{stats['total']} domain match, {stats['cross_lang']} cross-lang")
    
    print(f"\nCross-language examples:")
    for c in cross_lang_results[:10]:
        top = c['top_result']
        if top:
            print(f"  {c['query_id']} ({c['query_language']}): Retrieved {top['language']} document ({top['domain']}) score={top['score']}")
    
    # Save detailed results
    output = {
        'summary': {
            'total_queries': total,
            'domain_matches': domain_matches,
            'domain_match_rate': round(domain_matches/total*100, 1),
            'cross_language_retrievals': cross_lang_count,
            'cross_language_rate': round(cross_lang_count/total*100, 1)
        },
        'per_language': lang_stats,
        'cross_language_examples': cross_lang_results,
        'detailed_results': results
    }
    
    with open('/home/dhiraj/Desktop/SIH/rag_pipeline/retrieval_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed results saved to retrieval_test_results.json")


if __name__ == '__main__':
    run_retrieval_tests()