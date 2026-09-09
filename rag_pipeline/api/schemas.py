#!/usr/bin/env python3
"""
Pydantic schemas for FastAPI request/response models.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class LanguageCode(str, Enum):
    AUTO = "auto"
    EN = "en"
    HI = "hi"
    MR = "mr"
    GU = "gu"
    BN = "bn"
    TA = "ta"
    TE = "te"
    KN = "kn"
    ML = "ml"
    PA = "pa"


class DomainCode(str, Enum):
    ALL = "all"
    BIODIVERSITY = "biodiversity"
    ABS = "abs"
    TRADITIONAL_KNOWLEDGE = "traditional_knowledge"
    PATENTS = "patents"
    TRADEMARKS = "trademarks"
    GI = "gi"
    DESIGNS = "designs"
    GENERAL_LEGAL = "general_legal"


class DocumentTypeCode(str, Enum):
    ACT = "Act"
    RULES = "Rules"
    AMENDMENT_ACT = "Amendment Act"
    NOTIFICATION = "Notification"
    ORDER = "Order"
    OTHER = "Other"


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000, description="User query")
    language: LanguageCode = Field(default=LanguageCode.AUTO, description="Answer language")
    domain: DomainCode = Field(default=DomainCode.ALL, description="Legal domain filter")
    document_type: Optional[DocumentTypeCode] = Field(default=None, description="Document type filter")
    document: Optional[str] = Field(default=None, description="Specific document filter")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    concise: bool = Field(default=True, description="Use concise prompt")


class SourceCitation(BaseModel):
    document: str = Field(..., description="Document name")
    document_type: str = Field(..., description="Document type (Act/Rules)")
    document_year: Optional[int] = Field(default=None, description="Document year")
    section: Optional[str] = Field(default=None, description="Section number")
    section_title: Optional[str] = Field(default=None, description="Section title")
    rule: Optional[str] = Field(default=None, description="Rule number")
    rule_title: Optional[str] = Field(default=None, description="Rule title")
    pages: List[int] = Field(default_factory=list, description="Source page numbers")
    language: str = Field(default="", description="Document language")
    domain: str = Field(default="", description="Legal domain")
    score: float = Field(default=0.0, description="Relevance score")


class LatencyInfo(BaseModel):
    retrieval_ms: int = Field(..., description="Retrieval time in milliseconds")
    generation_ms: int = Field(..., description="Generation time in milliseconds")
    translation_to_english_ms: int = Field(default=0, description="Translation to English time in milliseconds")
    translation_to_target_ms: int = Field(default=0, description="Translation to target language time in milliseconds")
    total_ms: int = Field(..., description="Total time in milliseconds")


class DetectedLanguage(BaseModel):
    code: str
    name: str
    confidence: float


class ChatResponse(BaseModel):
    success: bool = True
    query: str
    detected_language: DetectedLanguage
    answer_language: str
    domain: str
    answer: str
    confidence: str
    sources: List[SourceCitation] = Field(default_factory=list)
    latency: LatencyInfo
    error: Optional[str] = None
    agents_used: List[str] = Field(default_factory=list)
    routing_domain: Optional[str] = None
    routing_reason: Optional[str] = None
    is_multi_domain: bool = False


class HealthResponse(BaseModel):
    status: str
    service: str
    ollama: bool
    qwen_model: str
    chromadb: bool
    retriever: bool


class DetailedHealthResponse(BaseModel):
    status: str
    service: str
    version: str
    ollama: Dict[str, Any]
    chromadb: Dict[str, Any]
    embedding_model: Dict[str, Any]
    retriever: Dict[str, Any]
    rag_engine: Dict[str, Any]


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None


# Domain display names for UI
DOMAIN_DISPLAY = {
    DomainCode.ALL: "All Domains",
    DomainCode.BIODIVERSITY: "Biodiversity",
    DomainCode.ABS: "Access & Benefit Sharing (ABS)",
    DomainCode.TRADITIONAL_KNOWLEDGE: "Traditional Knowledge",
    DomainCode.PATENTS: "Patents",
    DomainCode.TRADEMARKS: "Trademarks",
    DomainCode.GI: "Geographical Indications",
    DomainCode.DESIGNS: "Designs",
    DomainCode.GENERAL_LEGAL: "General Legal",
}

# Language display names for UI
LANGUAGE_DISPLAY = {
    LanguageCode.AUTO: "Auto Detect",
    LanguageCode.EN: "English",
    LanguageCode.HI: "Hindi (हिंदी)",
    LanguageCode.MR: "Marathi (मराठी)",
    LanguageCode.GU: "Gujarati (ગુજરાતી)",
    LanguageCode.BN: "Bengali (বাংলা)",
    LanguageCode.TA: "Tamil (தமிழ்)",
    LanguageCode.TE: "Telugu (తెలుగు)",
    LanguageCode.KN: "Kannada (ಕನ್ನಡ)",
    LanguageCode.ML: "Malayalam (മലയാളം)",
    LanguageCode.PA: "Punjabi (ਪੰਜਾਬੀ)",
}