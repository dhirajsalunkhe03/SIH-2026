# RAG Pipeline - SIH 2026 Problem Statement 45

AI-based Traditional Knowledge, Biodiversity, Access & Benefit Sharing (ABS), and Intellectual Property (IP) Legal Intelligence System.

## Project Structure

```
rag_pipeline/
├── Phase 1: Data Preparation (PDF → JSON)
│   ├── data_prep.py         # Single document pipeline
│   ├── batch_prepare.py     # Batch processing
│   ├── rag_utils.py         # Utilities for loading/querying
│   └── QUICKSTART.py        # Quick start guide
│
├── Phase 2: Legal Data Quality Pipeline (JSON → Canonical + RAG Chunks)
│   ├── inspect_json.py      # Inspect JSON structure & quality
│   ├── validate_extraction.py # Validate legal extraction quality
│   ├── repair_extraction.py # Repair broken extractions
│   ├── legal_normalizer.py  # Normalize legal hierarchy
│   ├── merge_sections.py    # Merge sections across pages
│   ├── canonicalize.py      # Create canonical legal JSON
│   ├── create_rag_chunks.py # Generate semantic RAG chunks
│   ├── phase2_pipeline.py   # Orchestrate full pipeline
│   └── PHASE2_SUMMARY.md    # Detailed Phase 2 documentation
│
├── Phase 3: Embeddings & Retrieval (Future)
│   └── (To be implemented)
│
└── Output Directories
    ├── output/validated/    # _VALIDATED, _REPAIRED, _MERGED + reports
    ├── output/canonical/    # _NORMALIZED, _CANONICAL + reports
    └── output/rag_chunks/   # _RAG_CHUNKS + reports
```

---

## Phase 1: Data Preparation (Complete)

Transforms raw PDF-extracted JSON into RAG-ready normalized data.

### Key Scripts
- **`data_prep.py`** — Main pipeline: OCR cleaning → JSON validation → Section merging → Legal normalization → Metadata
- **`batch_prepare.py`** — Batch process multiple documents
- **`rag_utils.py`** — Load, query, validate, export RAG-ready data

### Features
- Pattern-based OCR correction (no ML)
- Schema validation & repair
- Multi-page section continuation merging
- Legal terminology standardization
- Zero external dependencies

### Usage
```bash
# Single document
python3 data_prep.py /home/dhiraj/Desktop/SIH/Datasets/BIO/Biological_Diversity_Act_2002.json

# Batch process all
python3 batch_prepare.py

# Analyze output
python3 rag_utils.py output/Biological_Diversity_Act_2002_RAG_READY.json stats
python3 rag_utils.py output/Biological_Diversity_Act_2002_RAG_READY.json search "benefit sharing"
```

---

## Phase 2: Legal Data Quality Pipeline (Complete)

**Why Phase 2?** Phase 1 output passes JSON schema validation but has critical content issues:
- Sections with empty titles/content
- Legal text only in `raw_text`, not extracted structures
- Incorrect page_type classifications
- Amendment acts not distinguished from principal acts
- Sections split across pages not merged
- OCR artifacts in extracted text

**Phase 2 Pipeline Stages:**

```
RAW EXTRACTED JSON
        ↓
   VALIDATION (validate_extraction.py)
   → Structural + Content + Legal Pattern validation
        ↓
    REPAIR (repair_extraction.py)
   → Deterministic recovery from raw_text
   → Amendment act detection (substitution/insertion/omission/repeal)
   → Continuation page marking
        ↓
   LEGAL NORMALIZATION (legal_normalizer.py)
   → Section → Subsection → Clause → Sub-clause hierarchy
   → Provisos, Explanations extraction
   → Cross-references, Keywords, Entities, Dates, Authorities
        ↓
   SECTION MERGING (merge_sections.py)
   → Merge multi-page sections using continuation flags + content continuity
   → Skip TOC entries, preserve uncertain merges
        ↓
   CANONICALIZATION (canonicalize.py)
   → Normalized document metadata (type, year, jurisdiction, domain)
   → Canonical page/section structure with raw_text preserved
        ↓
   RAG CHUNK GENERATION (create_rag_chunks.py)
   → One section = one RAG document (semantic chunking)
   → embedding_text with context prepended for retrieval
   → Legal wording preserved exactly
        ↓
   FINAL OUTPUTS
```

### Files Created

| Script | Input | Output |
|--------|-------|--------|
| `inspect_json.py` | `.json` | `inspection_report.json` + terminal summary |
| `validate_extraction.py` | `.json` | `validation_report.json` + `_VALIDATED.json` |
| `repair_extraction.py` | `.json` | `_REPAIRED.json` + `.repair_report.json` |
| `merge_sections.py` | `.json` | `_MERGED.json` + `.merge_report.json` |
| `legal_normalizer.py` | `.json` | `_NORMALIZED.json` + `.normalize_report.json` |
| `canonicalize.py` | `.json` | `_CANONICAL.json` + `.canonical_report.json` |
| `create_rag_chunks.py` | `.json` | `_RAG_CHUNKS.json` + `.rag_chunk_report.json` |
| `phase2_pipeline.py` | Directory | All above + `phase2_summary.json` |

### Usage

```bash
# Full pipeline on source files (cleaner OCR)
python3 phase2_pipeline.py /home/dhiraj/Desktop/SIH/Datasets/BIO

# Or individual steps
python3 inspect_json.py input.json
python3 validate_extraction.py input.json
python3 repair_extraction.py input.json
python3 merge_sections.py input.json
python3 legal_normalizer.py input.json
python3 canonicalize.py input.json
python3 create_rag_chunks.py input.json
```

### Output Structure

```
output/
├── validated/
│   ├── *_VALIDATED.json      # Validation results
│   ├── *_REPAIRED.json       # Repaired sections
│   ├── *_MERGED.json         # Merged sections
│   └── *.repair_report.json  # Repair actions
│   └── *.merge_report.json   # Merge actions
├── canonical/
│   ├── *_NORMALIZED.json     # Normalized hierarchy
│   ├── *_CANONICAL.json      # Canonical legal JSON
│   └── *.normalize_report.json
│   └── *.canonical_report.json
└── rag_chunks/
    ├── *_RAG_CHUNKS.json     # RAG chunks with embedding_text
    └── *.rag_chunk_report.json
```

---

## Processing Results (Source Files: Datasets/BIO/)

| Document | Pages | Sections (Before) | Sections (After Repair) | Sections (After Merge) | RAG Chunks |
|----------|-------|-------------------|------------------------|----------------------|------------|
| Biological Diversity (Amendment) Act, 2023 | 15 | 11 | 29 | 27 | 18 |
| Biological Diversity Act, 2002 | 25 | 5 | 154 | 80 | 68 |
| Patents Act, 1970 | 72 | 21 | 397 | 204 | 148 |
| **Total** | **112** | **37** | **580** | **311** | **234** |

### Quality Improvements
- **Sections recovered from raw_text**: 543 additional sections extracted
- **Legal hierarchy parsed**: 100+ sections with subsections/clauses/provisos
- **Cross-references extracted**: 500+ legal references
- **Keywords extracted**: 1000+ domain-specific terms
- **Amendments detected**: Properly tagged (substitution, insertion, omission, repeal)

---

## Sample Outputs

### Canonical Legal JSON Structure
```json
{
  "document": {
    "document_name": "Biological Diversity Act, 2002",
    "document_type": "Act",
    "year": 2002,
    "jurisdiction": "India",
    "source": "India Code",
    "primary_domain": "Biodiversity",
    "secondary_domains": ["Access and Benefit Sharing", "Traditional Knowledge"]
  },
  "pages": [
    {
      "page_number": 6,
      "page_type": "content",
      "sections": [
        {
          "section_number": "3",
          "section_title": "Certain persons not to undertake Biodiversity related activities...",
          "content": "Full legal text...",
          "subsections": [
            {"number": "(1)", "text": "...", "clauses": [
              {"number": "(a)", "text": "..."},
              {"number": "(b)", "text": "..."}
            ]},
            {"number": "(2)", "text": "..."}
          ],
          "provisos": [],
          "explanations": [],
          "cross_references": [{"reference_text": "section 3", "reference_type": "section", "target": "3"}],
          "keywords": ["biological resources", "national biodiversity authority"],
          "source_pages": [6],
          "is_continuation": false
        }
      ],
      "raw_text": "Original OCR text...",
      "ocr_notes": []
    }
  ]
}
```

### RAG Chunk Structure
```json
{
  "chunk_id": "bio_act_2002_sec_7",
  "document": "Biological Diversity Act, 2002",
  "document_type": "Act",
  "document_year": 2002,
  "section_number": "7",
  "section_title": "Prior intimation to State Biodiversity Board...",
  "text": "Complete legal provision with subsections, provisos, explanations...",
  "embedding_text": "Document: Biological Diversity Act, 2002\nDomain: Biodiversity\nSection 7: Prior intimation...\n\n[Complete provision]\n\nKeywords: biological resources, access, benefit sharing",
  "source_pages": [4, 5],
  "domain": "Biodiversity",
  "keywords": ["biological resources", "access", "benefit sharing"],
  "cross_references": [...],
  "metadata": {
    "jurisdiction": "India",
    "source": "India Code",
    "has_hierarchy": true,
    "is_continuation": false,
    "is_amendment": false
  }
}
```

---

## Safety Rules (Phase 2)

✅ **No LLM used** — All deterministic Python rules  
✅ **No legal text invented** — Only recovered from existing `raw_text`  
✅ **raw_text preserved** — In all outputs as audit trail  
✅ **Amendment acts separated** — Not conflated with principal Acts  
✅ **Uncertain merges flagged** — Not forced, marked `merge_status: "uncertain"`  
✅ **null for unknown** — Never guess missing metadata  

---

## Next Steps: Phase 3

**Phase 3 — Embeddings & Retrieval**

Ready inputs in `output/rag_chunks/`:
- 234 chunks with `embedding_text` field for embedding
- Full canonical documents in `output/canonical/` with `raw_text` audit trail

### Phase 3 Tasks
1. Generate embeddings (sentence-transformers, legal-specific models)
2. Vector database (ChromaDB, FAISS, Qdrant)
3. Hybrid retrieval (dense + BM25)
4. RAG query interface with citations
5. Evaluation on legal QA benchmarks

---

## Quick Reference

```bash
# Phase 1: Data Preparation
python3 batch_prepare.py

# Phase 2: Legal Quality Pipeline
python3 phase2_pipeline.py /home/dhiraj/Desktop/SIH/Datasets/BIO

# Inspect results
python3 inspect_json.py output/Biological_Diversity_Act_RAG_READY.json
python3 validate_extraction.py output/Biological_Diversity_Act_RAG_READY.json

# View Phase 2 summary
cat PHASE2_SUMMARY.md
```

---

## Requirements

- Python 3.8+
- Standard library only (json, re, pathlib, typing, dataclasses, logging, subprocess)
- No external ML/LLM dependencies

---

## Status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Data Prep | ✅ Complete | JSON extraction + basic normalization |
| Phase 2: Legal Quality | ✅ Complete | Validation, repair, normalization, merge, canonicalize, RAG chunks |
| Phase 3: Embeddings | 🔲 Planned | Vector DB, retrieval, RAG interface |

**Data Ready for Phase 3:** 234 semantic RAG chunks with legal hierarchy, cross-references, and domain keywords.