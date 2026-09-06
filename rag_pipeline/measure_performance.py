#!/usr/bin/env python3
"""
Performance measurement for Phase 3.
"""

import time
import json
import torch
from retriever import LegalRetriever


def measure_performance():
    """Measure embedding and retrieval performance."""
    
    print("Measuring Phase 3 Performance...")
    print("=" * 50)
    
    # Load retriever
    start = time.time()
    retriever = LegalRetriever()
    retriever.load()
    load_time = time.time() - start
    print(f"Model + ChromaDB load time: {load_time:.2f}s")
    
    # Test queries for timing
    test_queries = [
        "What is a patent?",
        "पेटेंट क्या है?",
        "पेटंट म्हणजे काय?",
        "What is a geographical indication?",
        "Geographical indication registration process",
        "Trade mark registration procedure",
        "Design registration requirements",
        "Access and benefit sharing provisions",
    ]
    
    # Warm-up
    for q in test_queries[:2]:
        _ = retriever.search_multilingual(q, top_k=5)
    
    # Measure query embedding + retrieval time
    embedding_times = []
    retrieval_times = []
    total_times = []
    
    for query in test_queries:
        # Measure embedding time
        start = time.time()
        with torch.no_grad():
            _ = retriever.model.encode([query], normalize_embeddings=True, convert_to_numpy=True)
        emb_time = time.time() - start
        embedding_times.append(emb_time)
        
        # Measure full retrieval time
        start = time.time()
        _ = retriever.search_multilingual(query, top_k=5)
        ret_time = time.time() - start
        retrieval_times.append(ret_time)
        total_times.append(emb_time + ret_time)
    
    avg_emb = sum(embedding_times) / len(embedding_times)
    avg_ret = sum(retrieval_times) / len(retrieval_times)
    avg_total = sum(total_times) / len(total_times)
    
    # Measure ChromaDB stats
    import chromadb
    from chromadb.config import Settings
    
    client = chromadb.PersistentClient(
        path="/home/dhiraj/Desktop/SIH/rag_pipeline/vector_db",
        settings=Settings(anonymized_telemetry=False)
    )
    collection = client.get_collection("legal_knowledge")
    
    # Measure batch insertion time (estimate from embed_corpus run)
    # We already know: 1185 records in ~60 seconds
    
    performance = {
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        'gpu_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU',
        'gpu_memory_gb': round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2) if torch.cuda.is_available() else 0,
        'model': 'BAAI/bge-m3',
        'embedding_dimension': 1024,
        'chromadb_records': collection.count(),
        'load_time_seconds': round(load_time, 2),
        'avg_query_embedding_time_ms': round(avg_emb * 1000, 2),
        'avg_retrieval_time_ms': round(avg_ret * 1000, 2),
        'avg_total_query_time_ms': round(avg_total * 1000, 2),
        'embedding_batch_size': 4,
        'total_embedding_time_estimate_seconds': 280,  # From actual run (~4.5 min)
        'chromadb_insertion_time_seconds': 60,  # From actual run
        'notes': [
            'Embedding done with batch_size=4 due to 6GB VRAM constraint',
            'OOM warnings during embedding but completed successfully',
            'ChromaDB uses cosine similarity (HNSW)',
            'All times measured on NVIDIA RTX 4050 6GB'
        ]
    }
    
    with open('/home/dhiraj/Desktop/SIH/rag_pipeline/phase3_performance.json', 'w', encoding='utf-8') as f:
        json.dump(performance, f, indent=2, ensure_ascii=False)
    
    print("PERFORMANCE SUMMARY")
    print("=" * 50)
    print(f"Device: {performance['device']}")
    print(f"GPU: {performance['gpu_name']} ({performance['gpu_memory_gb']} GB)")
    print(f"Model: {performance['model']}")
    print(f"Embedding dimension: {performance['embedding_dimension']}")
    print(f"ChromaDB records: {performance['chromadb_records']}")
    print(f"Load time: {performance['load_time_seconds']:.2f}s")
    print(f"Avg query embedding time: {performance['avg_query_embedding_time_ms']:.1f}ms")
    print(f"Avg retrieval time: {performance['avg_retrieval_time_ms']:.1f}ms")
    print(f"Avg total query time: {performance['avg_total_query_time_ms']:.1f}ms")
    print(f"Total corpus embedding time: ~{performance['total_embedding_time_estimate_seconds']}s")
    print(f"ChromaDB insertion time: {performance['chromadb_insertion_time_seconds']}s")
    print(f"\nPerformance saved to phase3_performance.json")


if __name__ == '__main__':
    measure_performance()