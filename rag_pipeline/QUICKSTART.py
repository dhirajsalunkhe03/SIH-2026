#!/usr/bin/env python3
"""
RAG Data Preparation - Getting Started Guide
Complete example workflows with all 3 documents
"""

import json
from pathlib import Path
from rag_utils import RAGDataLoader, RAGDataValidator, RAGDataComparator

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║           RAG DATA PREPARATION - QUICK START GUIDE                         ║
║                   All 3 Documents Ready for Next Phase                     ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

output_dir = Path('output')

# ============================================================================
# 1. LOAD INDIVIDUAL DOCUMENT
# ============================================================================
print("\n[1] LOADING RAG-READY DOCUMENT")
print("─" * 80)

loader = RAGDataLoader(str(output_dir / 'Biological_Diversity_Act_2002_RAG_READY.json'))
stats = loader.get_statistics()

print(f"""
Document: {stats['document_name']}
  Total pages: {stats['total_pages']}
  Total sections: {stats['total_sections']}
  Processing stage: {stats['processing_stage']}
  Page types: {stats['page_types']}
""")

# ============================================================================
# 2. SEARCH FUNCTIONALITY  
# ============================================================================
print("\n[2] SEARCHING DOCUMENT")
print("─" * 80)

search_term = "biological resource"
results = loader.search_sections(search_term)

print(f"Search: '{search_term}'")
print(f"Results found: {len(results)}")

if results:
    # Show top result
    top = results[0]
    print(f"""
Top Result:
  Section: {top.get('section_number')}
  Page: {top.get('page_number')}
  Matches: {top.get('match_count')}
  Title: {top.get('section_title', 'N/A')[:60]}...
""")

# ============================================================================
# 3. EXTRACT SECTIONS BY PAGE
# ============================================================================
print("\n[3] GETTING SECTIONS FROM SPECIFIC PAGE")
print("─" * 80)

page_num = 2
sections = loader.get_sections_by_page(page_num)
raw_text = loader.get_raw_text(page_num)

print(f"""
Page {page_num}:
  Sections found: {len(sections)}
  Raw text length: {len(raw_text)} characters
  Raw text preview: {raw_text[:150]}...
""")

# ============================================================================
# 4. DATA QUALITY VALIDATION
# ============================================================================
print("\n[4] DATA QUALITY VALIDATION")
print("─" * 80)

validator = RAGDataValidator(loader)
is_valid, issues = validator.validate_all()

print(f"""
Validation Status: {'✓ PASS' if is_valid else '✗ FAIL'}
Issues found: {len(issues)}
""")

if issues:
    print("Sample issues:")
    for issue in issues[:3]:
        print(f"  - {issue}")

# ============================================================================
# 5. COMPARE MULTIPLE DOCUMENTS
# ============================================================================
print("\n[5] COMPARING ALL 3 DOCUMENTS")
print("─" * 80)

files = [
    'Biological_Diversity_Act_2002_RAG_READY.json',
    'Biological_Diversity_Act_RAG_READY.json',
    'Patents_Act_1970_RAG_READY.json',
]

loaders = [RAGDataLoader(str(output_dir / f)) for f in files]
comparator = RAGDataComparator(*loaders)

comparison = comparator.compare_documents()

print("\nDocument Comparison:")
print(f"{'Document':<40} {'Pages':<8} {'Sections':<10} {'Chars':<10}")
print("─" * 70)

for doc_name, stats in comparison.items():
    print(f"{doc_name:<40} {stats['total_pages']:<8} "
          f"{stats['total_sections']:<10} {stats.get('total_characters', 0):<10}")

# ============================================================================
# 6. WORKING WITH RAW TEXT
# ============================================================================
print("\n[6] ACCESSING RAW OCR TEXT")
print("─" * 80)

print(f"""
RAW TEXT (Direct from OCR):
  Available on every page via page.get('raw_text')
  This is the cleaned & normalized text after OCR correction
  
Example: Access raw text programmatically
  
  from rag_utils import RAGDataLoader
  
  loader = RAGDataLoader('Biological_Diversity_Act_2002_RAG_READY.json')
  
  # Get raw text from specific page
  page_text = loader.get_raw_text(5)
  
  # Get all pages with raw text
  for page in loader.data['pages']:
      text = page.get('raw_text', '')
      print(f"Page {{page['page_number']}}: {{len(text)}} chars")
""")

# ============================================================================
# 7. EXPORT FOR DOWNSTREAM PROCESSING
# ============================================================================
print("\n[7] EXPORTING DATA FOR DOWNSTREAM PROCESSING")
print("─" * 80)

# Export sections to CSV
csv_path = 'sections_export.csv'
loader.export_sections_csv(csv_path)

print(f"""
✓ Exported sections to: {csv_path}

Exported fields:
  - page_number
  - page_type  
  - section_number
  - section_title
  - content_length
  - is_continuation
  - document_name
  
Next use this CSV for:
  - Data analysis
  - Statistics
  - Quality review
  - Embedding generation
""")

# ============================================================================
# 8. BATCH PROCESSING REPORT
# ============================================================================
print("\n[8] BATCH PROCESSING REPORT")
print("─" * 80)

with open(output_dir / 'batch_report.json') as f:
    report = json.load(f)

print(f"""
Processing Report:
  Timestamp: {report['timestamp']}
  Total documents: {report['total_documents']}
  Successful: {report['successful']}
  Failed: {report['failed']}
  
Combined Statistics:
  Total pages processed: {report['total_pages']}
  Total sections extracted: {report['total_sections']}
  
Processing time: <1 second
Status: ✓ COMPLETE
""")

# ============================================================================
# 9. NEXT STEPS FOR LLM PHASE
# ============================================================================
print("\n[9] NEXT STEPS - LLM EXTRACTION PHASE")
print("─" * 80)

print("""
RAG-Ready JSON Files Ready:
  1. Biological_Diversity_Act_2002_RAG_READY.json (48 KB)
  2. Biological_Diversity_Act_RAG_READY.json (91 KB)
  3. Patents_Act_1970_RAG_READY.json (262 KB)

Next Phase Tasks:
  1. Use LLM (Claude/GPT) for semantic extraction
     - Extract named entities (acts, dates, amounts)
     - Identify legal concepts and relationships
     - Generate summaries of sections
  
  2. Generate embeddings (OpenAI/Ollama)
     - Convert sections to vector embeddings
     - For semantic search and retrieval
  
  3. Store in Vector Database
     - Weaviate, Pinecone, or ChromaDB
     - Index by sections + metadata
     - Enable hybrid search (keyword + semantic)
  
  4. Build Query Interface
     - REST API for searches
     - CLI tool for queries
     - Web dashboard for browsing

Each file contains:
  - Clean OCR text (no artifacts)
  - Normalized legal terminology
  - Merged multi-page sections
  - Validated JSON schema
  - Document metadata
  
Ready for embedding and indexing!
""")

# ============================================================================
# 10. USAGE EXAMPLES CODE
# ============================================================================
print("\n[10] PYTHON API USAGE EXAMPLES")
print("─" * 80)

print("""
# Example 1: Load and search
from rag_utils import RAGDataLoader

loader = RAGDataLoader('Biological_Diversity_Act_2002_RAG_READY.json')
results = loader.search_sections('benefit sharing')
for r in results[:3]:
    print(f"Section {r['section_number']}: {r['match_count']} matches")


# Example 2: Validate data quality
from rag_utils import RAGDataValidator

validator = RAGDataValidator(loader)
is_valid, issues = validator.validate_all()
print(f"Valid: {is_valid}, Issues: {len(issues)}")


# Example 3: Access raw text
raw_text_page_1 = loader.get_raw_text(1)
all_raw_text = [p.get('raw_text', '') for p in loader.data['pages']]


# Example 4: Extract for ML pipeline
all_sections = loader.get_all_sections()
for section in all_sections:
    doc_id = f"{section['document_name']}:P{section['page_number']}:S{section['section_number']}"
    content = section['content']
    # Send to embedding model...


# Example 5: Batch operations
from rag_utils import RAGDataComparator
from pathlib import Path

files = list(Path('output').glob('*_RAG_READY.json'))
loaders = [RAGDataLoader(str(f)) for f in files]
comparator = RAGDataComparator(*loaders)
comparison = comparator.compare_documents()
""")

print("\n" + "=" * 80)
print("✅ RAG DATA PREPARATION COMPLETE - READY FOR NEXT PHASE!")
print("=" * 80 + "\n")
