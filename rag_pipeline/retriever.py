#!/usr/bin/env python3
"""
Multilingual legal document retriever using ChromaDB and bge-m3 embeddings.
"""

import json
import os
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import torch

from language_utils import detect_language, LanguageInfo


@dataclass
class RetrievalResult:
    rank: int
    chunk_id: str
    score: float
    document: str
    document_type: str
    document_year: int
    language: str
    domain: str
    section_number: str
    section_title: str
    rule_number: str
    rule_title: str
    text: str
    source_pages: List[int]
    keywords: List[str]
    cross_references: List[str]


class LegalRetriever:
    def __init__(
        self,
        vector_db_path: str = "/home/dhiraj/Desktop/SIH/rag_pipeline/vector_db",
        model_name: str = "BAAI/bge-m3",
        collection_name: str = "legal_knowledge",
        device: str = "cuda",
        use_cpu: bool = False
    ):
        self.vector_db_path = vector_db_path
        self.model_name = model_name
        self.collection_name = collection_name
        
        # Use CPU if explicitly requested or if CUDA not available
        if use_cpu or not torch.cuda.is_available():
            self.device = "cpu"
        else:
            self.device = device
            
        self.model = None
        self.client = None
        self.collection = None

    def load(self):
        """Load model and ChromaDB collection."""
        print(f"Loading model {self.model_name} on {self.device}")
        self.model = SentenceTransformer(self.model_name, device=self.device)
        
        print(f"Connecting to ChromaDB at {self.vector_db_path}")
        self.client = chromadb.PersistentClient(
            path=self.vector_db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_collection(self.collection_name)
        print(f"Loaded collection '{self.collection_name}' with {self.collection.count()} records")

    def _parse_metadata(self, meta: Dict) -> Dict:
        """Parse stored JSON metadata fields."""
        parsed = meta.copy()
        for key in ['source_pages', 'keywords', 'cross_references']:
            if key in meta and isinstance(meta[key], str):
                try:
                    parsed[key] = json.loads(meta[key])
                except json.JSONDecodeError:
                    parsed[key] = []
        return parsed

    def search(
        self,
        query: str,
        top_k: int = 5,
        domain: Optional[Union[str, List[str]]] = None,
        language: Optional[str] = None,
        document_type: Optional[str] = None,
        document: Optional[str] = None
    ) -> List[RetrievalResult]:
        """
        Search for legal provisions matching the query.
        
        Args:
            query: User query in any supported language
            top_k: Number of results to return
            domain: Filter by legal domain (str or list of str)
            language: Filter by document language
            document_type: Filter by 'Act' or 'Rules'
            document: Filter by specific document name
            
        Returns:
            List of RetrievalResult objects ranked by relevance
        """
        if not self.collection:
            raise RuntimeError("Retriever not loaded. Call load() first.")

        # Build where filter
        where_filter = {}
        if domain:
            if isinstance(domain, list):
                # Use $in operator for multiple domains
                where_filter["domain"] = {"$in": domain}
            else:
                where_filter["domain"] = domain
        if language:
            where_filter["language"] = language
        if document_type:
            where_filter["document_type"] = document_type
        if document:
            where_filter["document"] = document

        # Generate query embedding
        with torch.no_grad():
            query_embedding = self.model.encode(
                [query],
                normalize_embeddings=True,
                convert_to_numpy=True
            )[0].tolist()

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"]
        )

        # Parse results
        retrieval_results = []
        if results['ids'] and results['ids'][0]:
            for rank, (chunk_id, document_text, metadata, distance) in enumerate(
                zip(results['ids'][0], results['documents'][0], results['metadatas'][0], results['distances'][0]),
                start=1
            ):
                parsed_meta = self._parse_metadata(metadata)
                
                result = RetrievalResult(
                    rank=rank,
                    chunk_id=chunk_id,
                    score=round(1.0 - distance, 4),  # Convert distance to similarity
                    document=metadata.get('document', ''),
                    document_type=metadata.get('document_type', ''),
                    document_year=metadata.get('document_year', 0),
                    language=metadata.get('language', ''),
                    domain=metadata.get('domain', ''),
                    section_number=metadata.get('section_number', ''),
                    section_title=metadata.get('section_title', ''),
                    rule_number=metadata.get('rule_number', ''),
                    rule_title=metadata.get('rule_title', ''),
                    text=document_text,
                    source_pages=parsed_meta.get('source_pages', []),
                    keywords=parsed_meta.get('keywords', []),
                    cross_references=parsed_meta.get('cross_references', [])
                )
                retrieval_results.append(result)

        return retrieval_results

    def search_multilingual(
        self,
        query: str,
        top_k: int = 5,
        domain: Optional[str] = None,
        language: Optional[str] = None,
        document_type: Optional[str] = None,
        document: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Multilingual search with automatic query language detection.
        
        Returns:
            Dictionary with query info, detected language, and results
        """
        # Detect query language
        lang_info = detect_language(query)
        
        # Search
        results = self.search(
            query=query,
            top_k=top_k,
            domain=domain,
            language=language,
            document_type=document_type,
            document=document
        )
        
        return {
            "query": query,
            "detected_language": {
                "code": lang_info.code,
                "name": lang_info.name,
                "confidence": lang_info.confidence
            },
            "filters": {
                "domain": domain,
                "language": language,
                "document_type": document_type,
                "document": document
            },
            "results": [self._result_to_dict(r) for r in results]
        }

    def _result_to_dict(self, result: RetrievalResult) -> Dict[str, Any]:
        return {
            "rank": result.rank,
            "chunk_id": result.chunk_id,
            "score": result.score,
            "document": result.document,
            "document_type": result.document_type,
            "document_year": result.document_year,
            "language": result.language,
            "domain": result.domain,
            "section_number": result.section_number,
            "section_title": result.section_title,
            "rule_number": result.rule_number,
            "rule_title": result.rule_title,
            "text": result.text[:500] + "..." if len(result.text) > 500 else result.text,
            "source_pages": result.source_pages,
            "keywords": result.keywords,
            "cross_references": result.cross_references
        }


def print_results(query_info: Dict):
    """Pretty print search results."""
    print(f"\n{'='*60}")
    print(f"QUERY: {query_info['query']}")
    print(f"Detected Language: {query_info['detected_language']['name']} ({query_info['detected_language']['code']}) confidence={query_info['detected_language']['confidence']}")
    print(f"Filters: {query_info['filters']}")
    print(f"{'='*60}")
    
    for r in query_info['results']:
        print(f"\n--- Rank {r['rank']} (Score: {r['score']}) ---")
        print(f"Document: {r['document']} ({r['document_type']}, {r['document_year']})")
        print(f"Domain: {r['domain']} | Language: {r['language']}")
        if r['section_number']:
            print(f"Section: {r['section_number']} - {r['section_title']}")
        if r['rule_number']:
            print(f"Rule: {r['rule_number']} - {r['rule_title']}")
        print(f"Source Pages: {r['source_pages']}")
        print(f"Keywords: {r['keywords'][:5] if r['keywords'] else '[]'}")
        print(f"Text: {r['text']}")


if __name__ == '__main__':
    retriever = LegalRetriever()
    retriever.load()
    
    # Test queries
    test_queries = [
        "What is a patent?",
        "पेटेंट क्या है?",
        "पेटंट म्हणजे काय?",
        "What is a geographical indication?",
        "Geographical indication registration process",
    ]
    
    for q in test_queries:
        result = retriever.search_multilingual(q, top_k=3)
        print_results(result)