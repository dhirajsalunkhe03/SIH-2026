#!/usr/bin/env python3
"""
Multilingual corpus embedding script.
Loads all RAG chunks, generates embeddings using bge-m3, saves to numpy and ChromaDB.
"""

import json
import os
import sys
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from tqdm import tqdm

import torch
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings


@dataclass
class EmbeddingManifest:
    model_name: str
    model_dimension: int
    device: str
    total_chunks: int
    embedded_chunks: int
    failed_chunks: int
    languages: Dict[str, int]
    domains: Dict[str, int]
    created_at: str


class CorpusEmbedder:
    def __init__(self, model_name: str = "BAAI/bge-m3", batch_size: int = 4):
        self.model_name = model_name
        self.batch_size = batch_size
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.embedding_dim = None

        # Set CUDA memory allocator config for 6GB GPU
        if self.device == "cuda":
            os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True,max_split_size_mb:128")

    def load_model(self):
        print(f"Loading model: {self.model_name} on {self.device}")
        self.model = SentenceTransformer(self.model_name, device=self.device)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        print(f"Model loaded. Embedding dimension: {self.embedding_dim}")

    def load_chunks(self, rag_chunks_dir: Path) -> List[Dict]:
        """Load all RAG chunk JSON files, avoiding duplicates."""
        # Priority order: canonical names > EXTRACTED names > RAG_READY names
        canonical_files = [
            "Designs_Act_2000_RAG_CHUNKS.json",
            "Designs_Rules_2001_RAG_CHUNKS.json",
            "GI_Act_1999_RAG_CHUNKS.json",
            "GI_Rules_2002_RAG_CHUNKS.json",
            "Patents_Act_1970_RAG_CHUNKS.json",
            "Patents_Rules_2003_Marathi_RAG_CHUNKS.json",
            "Trade_Marks_Act_1999_RAG_CHUNKS.json",
            "Trade_Marks_Rules_2017_Marathi_RAG_CHUNKS.json",
            "Biological_Diversity_Act_2002_RAG_CHUNKS.json",
            "Biological_Diversity_Act_RAG_CHUNKS.json",
        ]

        all_chunks = []
        seen_chunk_ids = set()

        for fname in canonical_files:
            path = rag_chunks_dir / fname
            if not path.exists():
                print(f"Warning: {fname} not found, skipping")
                continue

            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            chunks = data.get('chunks', [])
            for chunk in chunks:
                chunk_id = chunk.get('chunk_id')
                if chunk_id and chunk_id not in seen_chunk_ids:
                    # Fix missing language field for old chunks
                    if chunk.get('language') == 'MISSING' or not chunk.get('language'):
                        if 'Patents' in chunk.get('document', ''):
                            chunk['language'] = 'en'
                        elif 'Biological' in chunk.get('document', ''):
                            chunk['language'] = 'en'
                        else:
                            chunk['language'] = 'en'

                    # Fix rule_number for Rules documents
                    if chunk.get('document_type') == 'Rules' and not chunk.get('rule_number'):
                        chunk['rule_number'] = chunk.get('section_number')
                        chunk['rule_title'] = chunk.get('section_title')
                        chunk['section_number'] = None
                        chunk['section_title'] = None

                    all_chunks.append(chunk)
                    seen_chunk_ids.add(chunk_id)

        print(f"Loaded {len(all_chunks)} unique chunks from {len(canonical_files)} files")
        return all_chunks

    def generate_embeddings(self, chunks: List[Dict]) -> np.ndarray:
        """Generate embeddings for all chunks using batch processing."""
        texts = [chunk.get('embedding_text', '') for chunk in chunks]

        # Verify all texts are non-empty
        for i, text in enumerate(texts):
            if not text.strip():
                print(f"Warning: Chunk {chunks[i].get('chunk_id')} has empty embedding_text")

        print(f"Generating embeddings for {len(texts)} chunks in batches of {self.batch_size}")

        all_embeddings = []
        with torch.no_grad():
            for i in tqdm(range(0, len(texts), self.batch_size), desc="Embedding"):
                batch_texts = texts[i:i + self.batch_size]
                batch_embeddings = self.model.encode(
                    batch_texts,
                    batch_size=self.batch_size,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                    convert_to_numpy=True
                )
                all_embeddings.append(batch_embeddings)

        embeddings = np.vstack(all_embeddings)
        print(f"Generated embeddings shape: {embeddings.shape}")

        # Verify no NaN/Inf
        if np.isnan(embeddings).any():
            raise ValueError("Embeddings contain NaN values")
        if np.isinf(embeddings).any():
            raise ValueError("Embeddings contain Inf values")

        return embeddings

    def save_embeddings(self, embeddings: np.ndarray, chunks: List[Dict], output_dir: Path):
        """Save embeddings and metadata to disk."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save numpy array
        np.save(output_dir / "embeddings.npy", embeddings)
        print(f"Saved embeddings.npy to {output_dir}")

        # Save metadata mapping
        metadata = []
        for i, chunk in enumerate(chunks):
            metadata.append({
                "index": i,
                "chunk_id": chunk.get('chunk_id'),
                "document": chunk.get('document'),
                "document_type": chunk.get('document_type'),
                "document_year": chunk.get('document_year'),
                "language": chunk.get('language'),
                "domain": chunk.get('domain'),
                "section_number": chunk.get('section_number'),
                "section_title": chunk.get('section_title'),
                "rule_number": chunk.get('rule_number'),
                "rule_title": chunk.get('rule_title'),
                "source_pages": chunk.get('source_pages', []),
                "keywords": chunk.get('keywords', []),
                "cross_references": chunk.get('cross_references', []),
                "filename": f"{chunk.get('document', 'unknown').replace(' ', '_').replace(',', '')}.pdf"
            })

        with open(output_dir / "embedding_metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"Saved embedding_metadata.json to {output_dir}")

        # Save manifest
        lang_counts = {}
        domain_counts = {}
        for chunk in chunks:
            lang = chunk.get('language', 'unknown')
            domain = chunk.get('domain', 'unknown')
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        manifest = EmbeddingManifest(
            model_name=self.model_name,
            model_dimension=self.embedding_dim,
            device=self.device,
            total_chunks=len(chunks),
            embedded_chunks=len(chunks),
            failed_chunks=0,
            languages=lang_counts,
            domains=domain_counts,
            created_at=datetime.now().isoformat()
        )

        with open(output_dir / "embedding_manifest.json", 'w', encoding='utf-8') as f:
            json.dump(asdict(manifest), f, indent=2, ensure_ascii=False)
        print(f"Saved embedding_manifest.json to {output_dir}")

    def create_chromadb(self, embeddings: np.ndarray, chunks: List[Dict], vector_db_dir: Path):
        """Create and populate ChromaDB collection."""
        print(f"Creating ChromaDB at {vector_db_dir}")

        client = chromadb.PersistentClient(
            path=str(vector_db_dir),
            settings=Settings(anonymized_telemetry=False)
        )

        # Create or get collection
        collection = client.get_or_create_collection(
            name="legal_knowledge",
            metadata={"hnsw:space": "cosine"}
        )

        # Prepare data for ChromaDB
        ids = [chunk.get('chunk_id') for chunk in chunks]
        documents = [chunk.get('text', '') for chunk in chunks]
        embeddings_list = embeddings.tolist()

        metadatas = []
        for chunk in chunks:
            source_pages = chunk.get('source_pages', [])
            keywords = chunk.get('keywords', [])
            cross_refs = chunk.get('cross_references', [])
            
            meta = {
                "chunk_id": str(chunk.get('chunk_id', '')),
                "document": str(chunk.get('document', '')),
                "document_type": str(chunk.get('document_type', '')),
                "document_year": int(chunk.get('document_year', 0)) if chunk.get('document_year') else 0,
                "language": str(chunk.get('language', '')),
                "domain": str(chunk.get('domain', '')),
                "section_number": str(chunk.get('section_number', '')),
                "section_title": str(chunk.get('section_title', '')),
                "rule_number": str(chunk.get('rule_number', '')),
                "rule_title": str(chunk.get('rule_title', '')),
                "source_pages": json.dumps(source_pages),
                "keywords": json.dumps(keywords),
                "cross_references": json.dumps(cross_refs),
            }
            metadatas.append(meta)

        # Add in batches
        batch_size = 100
        for i in tqdm(range(0, len(ids), batch_size), desc="ChromaDB insert"):
            end = min(i + batch_size, len(ids))
            collection.add(
                ids=ids[i:end],
                documents=documents[i:end],
                embeddings=embeddings_list[i:end],
                metadatas=metadatas[i:end]
            )

        print(f"Inserted {collection.count()} records into ChromaDB collection 'legal_knowledge'")

        # Verify
        assert collection.count() == len(chunks), "Count mismatch!"
        print("ChromaDB verification passed")

        return collection


def main():
    rag_chunks_dir = Path("/home/dhiraj/Desktop/SIH/rag_pipeline/output/rag_chunks")
    output_dir = Path("/home/dhiraj/Desktop/SIH/rag_pipeline/output/embeddings")
    vector_db_dir = Path("/home/dhiraj/Desktop/SIH/rag_pipeline/vector_db")

    embedder = CorpusEmbedder(model_name="BAAI/bge-m3", batch_size=16)
    embedder.load_model()

    chunks = embedder.load_chunks(rag_chunks_dir)
    embeddings = embedder.generate_embeddings(chunks)
    embedder.save_embeddings(embeddings, chunks, output_dir)
    embedder.create_chromadb(embeddings, chunks, vector_db_dir)

    print("\nEmbedding phase complete!")


if __name__ == '__main__':
    main()