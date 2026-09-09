#!/usr/bin/env python3
"""
Configuration for Phase 8 Production Legal RAG system.

Supports environment variable overrides for production deployment.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Optional


def _get_env(key: str, default: str) -> str:
    """Get environment variable with default."""
    return os.getenv(key, default)


def _get_env_int(key: str, default: int) -> int:
    """Get environment variable as integer with default."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _get_env_float(key: str, default: float) -> float:
    """Get environment variable as float with default."""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def _get_env_bool(key: str, default: bool) -> bool:
    """Get environment variable as boolean with default."""
    val = os.getenv(key, str(default)).lower()
    return val in ('true', '1', 'yes', 'on')


def _get_base_dir() -> Path:
    """Get base directory from environment or default."""
    return Path(os.getenv("RAG_BASE_DIR", "/home/dhiraj/Desktop/SIH/rag_pipeline"))


def _get_vector_db_path() -> str:
    """Get vector DB path from environment or default."""
    return os.getenv("RAG_VECTOR_DB_PATH", str(_get_base_dir() / "vector_db"))


def _get_logs_dir() -> Path:
    """Get logs directory from environment or default."""
    return Path(os.getenv("RAG_LOGS_DIR", str(_get_base_dir() / "logs")))


def _get_output_dir() -> Path:
    """Get output directory from environment or default."""
    return Path(os.getenv("RAG_OUTPUT_DIR", str(_get_base_dir() / "output")))


@dataclass
class RetrieverConfig:
    """Configuration for the legal retriever."""
    vector_db_path: str = field(default_factory=_get_vector_db_path)
    model_name: str = field(default_factory=lambda: _get_env("RAG_EMBEDDING_MODEL", "BAAI/bge-m3"))
    collection_name: str = field(default_factory=lambda: _get_env("RAG_COLLECTION_NAME", "legal_knowledge"))
    device: str = field(default_factory=lambda: _get_env("RAG_EMBEDDING_DEVICE", "cuda"))
    default_top_k: int = field(default_factory=lambda: _get_env_int("RAG_DEFAULT_TOP_K", 5))
    default_filters: Dict = field(default_factory=dict)
    use_cpu: bool = field(default_factory=lambda: _get_env_bool("RAG_EMBEDDING_USE_CPU", True))


@dataclass
class EmbedderConfig:
    """Configuration for the embedding model."""
    model_name: str = field(default_factory=lambda: _get_env("RAG_EMBEDDING_MODEL", "BAAI/bge-m3"))
    device: str = field(default_factory=lambda: _get_env("RAG_EMBEDDING_DEVICE", "cuda"))
    batch_size: int = field(default_factory=lambda: _get_env_int("RAG_EMBEDDING_BATCH_SIZE", 4))
    max_seq_length: int = field(default_factory=lambda: _get_env_int("RAG_EMBEDDING_MAX_SEQ_LEN", 512))
    normalize_embeddings: bool = True


@dataclass
class OllamaConfig:
    """Configuration for Ollama/Qwen3."""
    model: str = field(default_factory=lambda: _get_env("RAG_OLLAMA_MODEL", "qwen3:4b"))
    host: str = field(default_factory=lambda: _get_env("RAG_OLLAMA_HOST", "http://localhost:11434"))
    temperature: float = field(default_factory=lambda: _get_env_float("RAG_OLLAMA_TEMPERATURE", 0.1))
    top_p: float = field(default_factory=lambda: _get_env_float("RAG_OLLAMA_TOP_P", 0.9))
    max_tokens: int = field(default_factory=lambda: _get_env_int("RAG_OLLAMA_MAX_TOKENS", 512))
    timeout: int = field(default_factory=lambda: _get_env_int("RAG_OLLAMA_TIMEOUT", 120))
    system_prompt_concise: bool = True


@dataclass
class TranslationConfig:
    """Configuration for NLLB-200 translation model."""
    enabled: bool = field(default_factory=lambda: _get_env_bool("RAG_TRANSLATION_ENABLED", True))
    device: str = field(default_factory=lambda: _get_env("RAG_TRANSLATION_DEVICE", "cuda"))
    torch_dtype: str = field(default_factory=lambda: _get_env("RAG_TRANSLATION_DTYPE", "float16"))
    model_name: str = field(default_factory=lambda: _get_env("RAG_TRANSLATION_MODEL", "facebook/nllb-200-distilled-600M"))
    max_length: int = field(default_factory=lambda: _get_env_int("RAG_TRANSLATION_MAX_LEN", 512))
    num_beams: int = field(default_factory=lambda: _get_env_int("RAG_TRANSLATION_NUM_BEAMS", 5))
    cpu_fallback: bool = field(default_factory=lambda: _get_env_bool("RAG_TRANSLATION_CPU_FALLBACK", True))


@dataclass
class ContextConfig:
    """Configuration for context building."""
    max_context_chars: int = field(default_factory=lambda: _get_env_int("RAG_MAX_CONTEXT_CHARS", 1500))
    max_sources: int = field(default_factory=lambda: _get_env_int("RAG_MAX_SOURCES", 3))
    include_keywords: bool = True
    include_cross_references: bool = True
    truncate_long_texts: bool = True


@dataclass
class RetrievalThresholds:
    """Thresholds for retrieval confidence handling."""
    high_confidence: float = field(default_factory=lambda: _get_env_float("RAG_HIGH_CONFIDENCE", 0.6))
    medium_confidence: float = field(default_factory=lambda: _get_env_float("RAG_MEDIUM_CONFIDENCE", 0.4))
    low_confidence: float = field(default_factory=lambda: _get_env_float("RAG_LOW_CONFIDENCE", 0.25))
    no_context_threshold: float = field(default_factory=lambda: _get_env_float("RAG_NO_CONTEXT_THRESHOLD", 0.15))
    min_score_for_generation: float = field(default_factory=lambda: _get_env_float("RAG_MIN_SCORE_GENERATION", 0.3))


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
class APIConfig:
    """API server configuration."""
    host: str = field(default_factory=lambda: _get_env("RAG_API_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _get_env_int("RAG_API_PORT", 8000))
    cors_origins: str = field(default_factory=lambda: _get_env("RAG_CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501,http://localhost:3000"))
    request_timeout: int = field(default_factory=lambda: _get_env_int("RAG_API_REQUEST_TIMEOUT", 180))
    workers: int = field(default_factory=lambda: _get_env_int("RAG_API_WORKERS", 1))
    # Rate limiting (set to 0 to disable)
    rate_limit_requests: int = field(default_factory=lambda: _get_env_int("RAG_API_RATE_LIMIT", 60))
    rate_limit_window: int = field(default_factory=lambda: _get_env_int("RAG_API_RATE_WINDOW", 60))


@dataclass
class LoggingConfig:
    """Logging configuration."""
    log_dir: Path = field(default_factory=_get_logs_dir)
    log_level: str = field(default_factory=lambda: _get_env("RAG_LOG_LEVEL", "INFO"))
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_query: bool = True
    log_retrieval: bool = True
    log_generation: bool = True
    log_latency: bool = True
    log_translation: bool = True


@dataclass
class Phase8Config:
    """Main configuration container for Phase 8."""
    retriever: RetrieverConfig = field(default_factory=RetrieverConfig)
    embedder: EmbedderConfig = field(default_factory=EmbedderConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    translation: TranslationConfig = field(default_factory=TranslationConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    thresholds: RetrievalThresholds = field(default_factory=RetrievalThresholds)
    language: LanguageConfig = field(default_factory=LanguageConfig)
    api: APIConfig = field(default_factory=APIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Paths
    base_dir: Path = field(default_factory=_get_base_dir)
    output_dir: Path = field(default_factory=_get_output_dir)
    vector_db_dir: Path = field(default_factory=lambda: Path(_get_vector_db_path()))
    logs_dir: Path = field(default_factory=_get_logs_dir)
    
    # Test data
    test_queries_path: Path = field(default_factory=lambda: _get_base_dir() / "test_queries.json")
    phase4_test_queries_path: Path = field(default_factory=lambda: _get_base_dir() / "phase4_test_queries.json")
    
    def __post_init__(self):
        """Ensure directories exist."""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.vector_db_dir.mkdir(parents=True, exist_ok=True)

    def get_cors_origins_list(self) -> list:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.api.cors_origins.split(",") if origin.strip()]


# Backward compatibility alias
Phase4Config = Phase8Config


# Global config instance
_config: Optional[Phase8Config] = None


def get_config() -> Phase8Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Phase8Config()
    return _config


def reload_config() -> Phase8Config:
    """Reload configuration (forces re-read of environment variables)."""
    global _config
    _config = Phase8Config()
    return _config


if __name__ == '__main__':
    cfg = get_config()
    print("Phase 8 Configuration:")
    print(f"  Base Dir: {cfg.base_dir}")
    print(f"  Vector DB: {cfg.retriever.vector_db_path}")
    print(f"  Retriever: {cfg.retriever.model_name} on {cfg.retriever.device}")
    print(f"  Ollama: {cfg.ollama.model} (temp={cfg.ollama.temperature})")
    print(f"  API: {cfg.api.host}:{cfg.api.port}")
    print(f"  CORS Origins: {cfg.api.get_cors_origins_list()}")
    print(f"  Context max chars: {cfg.context.max_context_chars}")
    print(f"  Default top_k: {cfg.retriever.default_top_k}")
    print(f"  Confidence thresholds: high={cfg.thresholds.high_confidence}, medium={cfg.thresholds.medium_confidence}, low={cfg.thresholds.low_confidence}")
    print(f"  Supported languages: {list(cfg.language.supported_languages.keys())}")