#!/usr/bin/env python3
"""
Configuration for Phase 4 RAG system.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class RetrieverConfig:
    """Configuration for the legal retriever."""
    vector_db_path: str = "/home/dhiraj/Desktop/SIH/rag_pipeline/vector_db"
    model_name: str = "BAAI/bge-m3"
    collection_name: str = "legal_knowledge"
    device: str = "cuda"
    default_top_k: int = 5
    default_filters: Dict = field(default_factory=dict)


@dataclass
class EmbedderConfig:
    """Configuration for the embedding model."""
    model_name: str = "BAAI/bge-m3"
    device: str = "cuda"
    batch_size: int = 4
    max_seq_length: int = 512
    normalize_embeddings: bool = True


@dataclass
class OllamaConfig:
    """Configuration for Ollama/Qwen3."""
    model: str = "qwen3:4b"
    host: str = "http://localhost:11434"
    temperature: float = 0.1
    top_p: float = 0.9
    max_tokens: int = 512
    timeout: int = 120
    system_prompt_concise: bool = True


@dataclass
class ContextConfig:
    """Configuration for context building."""
    max_context_chars: int = 1500
    max_sources: int = 3
    include_keywords: bool = True
    include_cross_references: bool = True
    truncate_long_texts: bool = True


@dataclass
class RetrievalThresholds:
    """Thresholds for retrieval confidence handling."""
    high_confidence: float = 0.6
    medium_confidence: float = 0.4
    low_confidence: float = 0.25
    no_context_threshold: float = 0.15
    min_score_for_generation: float = 0.3


@dataclass
class LanguageConfig:
    """Language configuration."""
    supported_languages: Dict[str, str] = field(default_factory=lambda: {
        'en': 'English',
        'hi': 'Hindi',
        'mr': 'Marathi',
        'gu': 'Gujarati',
        'bn': 'Bengali',
        'ta': 'Tamil',
        'te': 'Telugu',
        'kn': 'Kannada',
        'ml': 'Malayalam',
        'pa': 'Punjabi',
        'auto': 'Auto-detect'
    })
    default_answer_language: str = 'auto'
    fallback_language: str = 'en'


@dataclass
class LoggingConfig:
    """Logging configuration."""
    log_dir: Path = field(default_factory=lambda: Path("/home/dhiraj/Desktop/SIH/rag_pipeline/logs"))
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(levelname)s - %(message)s"
    log_query: bool = True
    log_retrieval: bool = True
    log_generation: bool = True
    log_latency: bool = True


@dataclass
class Phase4Config:
    """Main configuration container."""
    retriever: RetrieverConfig = field(default_factory=RetrieverConfig)
    embedder: EmbedderConfig = field(default_factory=EmbedderConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    thresholds: RetrievalThresholds = field(default_factory=RetrievalThresholds)
    language: LanguageConfig = field(default_factory=LanguageConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Paths
    base_dir: Path = field(default_factory=lambda: Path("/home/dhiraj/Desktop/SIH/rag_pipeline"))
    output_dir: Path = field(default_factory=lambda: Path("/home/dhiraj/Desktop/SIH/rag_pipeline/output"))
    vector_db_dir: Path = field(default_factory=lambda: Path("/home/dhiraj/Desktop/SIH/rag_pipeline/vector_db"))
    logs_dir: Path = field(default_factory=lambda: Path("/home/dhiraj/Desktop/SIH/rag_pipeline/logs"))
    
    # Test data
    test_queries_path: Path = field(default_factory=lambda: Path("/home/dhiraj/Desktop/SIH/rag_pipeline/test_queries.json"))
    phase4_test_queries_path: Path = field(default_factory=lambda: Path("/home/dhiraj/Desktop/SIH/rag_pipeline/phase4_test_queries.json"))
    
    def __post_init__(self):
        """Ensure directories exist."""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.vector_db_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
_config: Optional[Phase4Config] = None


def get_config() -> Phase4Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Phase4Config()
    return _config


def reload_config() -> Phase4Config:
    """Reload configuration."""
    global _config
    _config = Phase4Config()
    return _config


if __name__ == '__main__':
    cfg = get_config()
    print("Phase 4 Configuration:")
    print(f"  Retriever: {cfg.retriever.model_name} on {cfg.retriever.device}")
    print(f"  Ollama: {cfg.ollama.model} (temp={cfg.ollama.temperature})")
    print(f"  Context max chars: {cfg.context.max_context_chars}")
    print(f"  Default top_k: {cfg.retriever.default_top_k}")
    print(f"  Confidence thresholds: high={cfg.thresholds.high_confidence}, medium={cfg.thresholds.medium_confidence}, low={cfg.thresholds.low_confidence}")
    print(f"  Supported languages: {list(cfg.language.supported_languages.keys())}")