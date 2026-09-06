#!/usr/bin/env python3
"""
Retrieval evaluation script.
Calculates precision metrics based on available ground truth.
"""

import json
from typing import List, Dict, Any
from retriever import LegalRetriever


def evaluate_retrieval():
    """Evaluate retrieval quality using available test data."""
    retriever = LegalRetriever()
    retriever.load()
    
    # Load test queries
    with open('/home/dhiraj/Desktop/SIH/rag_pipeline/test_queries.json', 'r', encoding='utf-8') as f:
        test_queries = json.load(f)
    
    # Load previous test results
    with open('/home/dhiraj/Desktop/SIH/rag_pipeline/retrieval_test_results.json', 'r', encoding='utf-8') as f:
        test_results = json.load(f)
    
    results = test_results['detailed_results']
    
    # Calculate Precision@K for domain matching
    k_values = [1, 3, 5]
    precision_at_k = {k: 0 for k in k_values}
    total_queries = len(results)
    
    for r in results:
        expected_domain = r['expected_domain']
        found_domains = r['found_domains']
        
        for k in k_values:
            top_k_domains = found_domains[:k]
            if expected_domain in top_k_domains:
                precision_at_k[k] += 1
    
    precision_at_k = {k: round(v / total_queries * 100, 1) for k, v in precision_at_k.items()}
    
    # Calculate Recall@5 (how many expected domains appear in top 5)
    recall_at_5 = sum(1 for r in results if r['expected_domain'] in r['found_domains'][:5]) / total_queries * 100
    
    # Cross-language analysis
    cross_lang_total = sum(1 for r in results if r['is_cross_language'])
    cross_lang_rate = cross_lang_total / total_queries * 100
    
    # Score distribution
    all_scores = []
    for r in results:
        all_scores.extend(r['top_scores'])
    
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
    min_score = min(all_scores) if all_scores else 0
    max_score = max(all_scores) if all_scores else 0
    
    # Per-domain analysis
    domain_stats = {}
    for r in results:
        domain = r['expected_domain']
        if domain not in domain_stats:
            domain_stats[domain] = {'total': 0, 'matches': 0}
        domain_stats[domain]['total'] += 1
        if r['domain_match']:
            domain_stats[domain]['matches'] += 1
    
    domain_precision = {}
    for domain, stats in domain_stats.items():
        domain_precision[domain] = round(stats['matches'] / stats['total'] * 100, 1)
    
    # Language analysis
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
    
    evaluation = {
        'total_queries': total_queries,
        'precision': {f'P@{k}': v for k, v in precision_at_k.items()},
        'recall_at_5': round(recall_at_5, 1),
        'cross_language_rate': round(cross_lang_rate, 1),
        'score_stats': {
            'avg': round(avg_score, 4),
            'min': round(min_score, 4),
            'max': round(max_score, 4)
        },
        'domain_precision': domain_precision,
        'language_stats': lang_stats,
        'notes': [
            'Precision@K measures whether expected domain appears in top K results',
            'Cross-language rate measures queries where retrieved language differs from query language',
            'Domain match is binary (expected domain in top 5)',
            'Ground truth limited to expected domain only - not full relevance judgments',
            'Marathi queries detected as Hindi due to shared Devanagari script'
        ]
    }
    
    with open('/home/dhiraj/Desktop/SIH/rag_pipeline/evaluation_results.json', 'w', encoding='utf-8') as f:
        json.dump(evaluation, f, indent=2, ensure_ascii=False)
    
    print("EVALUATION SUMMARY")
    print("=" * 50)
    print(f"Total queries: {total_queries}")
    for k, v in precision_at_k.items():
        print(f"Precision@{k}: {v}%")
    print(f"Recall@5: {round(recall_at_5, 1)}%")
    print(f"Cross-language rate: {round(cross_lang_rate, 1)}%")
    print(f"Avg similarity score: {round(avg_score, 4)}")
    print(f"\nPer-domain precision:")
    for domain, prec in domain_precision.items():
        print(f"  {domain}: {prec}%")
    print(f"\nPer-language stats:")
    for lang, stats in lang_stats.items():
        print(f"  {lang}: {stats['matches']}/{stats['total']} domain match, {stats['cross_lang']} cross-lang")
    
    print("\nNote: Marathi queries detected as Hindi due to shared Devanagari script")
    print("Note: Cross-language retrieval working - Indian language queries retrieve English documents")
    print("\nEvaluation saved to evaluation_results.json")
    
    return evaluation


if __name__ == '__main__':
    evaluate_retrieval()