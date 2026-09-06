# RAG Pipeline - Phase 1: Data Preparation 
## Complete Project Structure & Getting Started

```
/home/dhiraj/Desktop/SIH/rag_pipeline/
├── 📄 README.md                          # Full documentation
├── 📄 DATA_PREP_SUMMARY.md               # Executive summary  
├── 📄 requirements.txt                   # Dependencies (none needed!)
│
├── 🐍 Core Modules (430 lines)
│   ├── data_prep.py                      # Main RAG preparation pipeline
│   ├── batch_prepare.py                  # Batch processor for multiple docs
│   └── rag_utils.py                      # Data loader & utilities
│
├── 🚀 Demo & Getting Started
│   ├── QUICKSTART.py                     # Complete usage examples
│   └── venv/                             # Python 3.12 environment
│
└── 📊 Output Directory (401 KB)
    ├── batch_report.json                 # Processing statistics
    ├── sections_export.csv               # Sections data table
    │
    ├── Biological_Diversity_Act_2002_RAG_READY.json     (48 KB)
    ├── Biological_Diversity_Act_RAG_READY.json          (91 KB)
    └── Patents_Act_1970_RAG_READY.json                 (262 KB)
```

## ⚡ Quick Start (Choose Your Path)

### Path 1: Run Everything at Once
```bash
cd /home/dhiraj/Desktop/SIH/rag_pipeline
python3 batch_prepare.py /home/dhiraj/Desktop/SIH/Datasets/BIO output
```
✓ Processes all 3 documents  
✓ Generates RAG-ready JSONs  
✓ Creates batch report  
✓ Time: <1 second  

### Path 2: Learn & Explore
```bash
cd /home/dhiraj/Desktop/SIH/rag_pipeline
python3 QUICKSTART.py
```
✓ Shows all features step-by-step  
✓ Demonstrates each API  
✓ Includes code examples  
✓ Time: ~30 seconds  

### Path 3: Analyze Existing Output
```bash
# Show document statistics
python3 rag_utils.py output/Biological_Diversity_Act_2002_RAG_READY.json stats

# Search document
python3 rag_utils.py output/Biological_Diversity_Act_2002_RAG_READY.json search "biological"

# Validate quality
python3 rag_utils.py output/Biological_Diversity_Act_2002_RAG_READY.json validate

# Export sections
python3 rag_utils.py output/Biological_Diversity_Act_2002_RAG_READY.json export sections.csv
```

### Path 4: Interactive Python
```python
from rag_utils import RAGDataLoader, RAGDataValidator

# Load document
loader = RAGDataLoader('output/Biological_Diversity_Act_2002_RAG_READY.json')

# Get statistics
stats = loader.get_statistics()
print(f"Pages: {stats['total_pages']}, Sections: {stats['total_sections']}")

# Search
results = loader.search_sections('benefit sharing')
print(f"Found {len(results)} matches")

# Validate
validator = RAGDataValidator(loader)
is_valid, issues = validator.validate_all()
print(f"Valid: {is_valid}, Issues: {len(issues)}")
```

## 📋 What Each File Does

### `data_prep.py` - Single Document Processing
**Purpose:** Transform one raw extracted JSON to RAG-ready format

**Usage:**
```bash
python3 data_prep.py input.json [output.json]
```

**Processing Steps:**
1. Clean OCR text (fix l/1, O/0, artifacts)
2. Validate JSON schema
3. Merge continuation sections
4. Normalize legal terminology
5. Add metadata

**Output:** RAG-ready JSON file

---

### `batch_prepare.py` - Multi-Document Processing
**Purpose:** Process all JSON files in a directory

**Usage:**
```bash
python3 batch_prepare.py [input_dir] [output_dir]
```

**Features:**
- Auto-discovers JSON files
- Processes in sequence
- Generates batch report
- Tracks statistics
- Error handling

**Output:** Multiple RAG-ready JSONs + batch_report.json

---

### `rag_utils.py` - Data Access & Analysis
**Purpose:** Load, query, validate, and export RAG data

**Main Classes:**
- `RAGDataLoader` - Access and search
- `RAGDataValidator` - Quality checks
- `RAGDataComparator` - Compare documents

**CLI Usage:**
```bash
python3 rag_utils.py <json_file> stats
python3 rag_utils.py <json_file> search "query"
python3 rag_utils.py <json_file> validate
python3 rag_utils.py <json_file> export <csv_file>
```

**Python Usage:**
```python
from rag_utils import RAGDataLoader

loader = RAGDataLoader('file.json')
sections = loader.get_all_sections()
results = loader.search_sections('term')
stats = loader.get_statistics()
loader.export_sections_csv('output.csv')
```

---

### `QUICKSTART.py` - Getting Started Demo
**Purpose:** Complete working example of all features

**Shows:**
1. Loading RAG-ready document
2. Searching sections
3. Extracting page data
4. Quality validation
5. Multi-document comparison
6. Accessing raw text
7. Exporting to CSV
8. Review batch report
9. Next phase roadmap
10. Code examples

**Usage:**
```bash
python3 QUICKSTART.py
```

---

## 📊 Processing Statistics

### Input Data
```
Biological Diversity Act, 2002    → 15 pages  → 42.3 KB
Biological Diversity Act          → 25 pages  → 45.8 KB
Patents Act, 1970                 → 72 pages  → 58.2 KB
───────────────────────────────────────────────────────
TOTAL                            → 112 pages → 146.3 KB
```

### Processing Output
```
OCR Artifacts Fixed:          517
Sections Merged:                3
Normalizations Applied:        58
Schema Compliance:           100%
Processing Time:            <1 sec
Output Size:              401 KB
```

### Output Files Generated
```
✓ Biological_Diversity_Act_2002_RAG_READY.json      (48 KB)
✓ Biological_Diversity_Act_RAG_READY.json           (91 KB)
✓ Patents_Act_1970_RAG_READY.json                  (262 KB)
✓ batch_report.json                                (724 B)
✓ sections_export.csv                            (if exported)
```

## 🔧 Technology Stack

**Requirements:**
- Python 3.12+
- Linux/Mac/Windows
- ~50 MB RAM
- ~500 KB disk

**Dependencies:**
- None! (uses only stdlib)
- `json` - JSON parsing
- `re` - Pattern matching
- `pathlib` - File operations
- `logging` - Logging
- `csv` - CSV export
- `dataclasses` - Data structures

**No pip packages needed!**

## 📚 Documentation Files

### README.md
- Architecture overview
- Component documentation
- Processing pipeline details
- Quick reference
- Features & limitations
- Next steps

### DATA_PREP_SUMMARY.md
- Executive summary
- Results & statistics
- Code modules breakdown
- Key features
- File formats
- Next phase roadmap

### This File (INDEX.md)
- Project structure
- Quick start paths
- File descriptions
- Common commands
- Troubleshooting

## 🚀 Common Tasks

### Process New Documents
```bash
python3 data_prep.py /path/to/new_document.json output/new_RAG_READY.json
```

### Search All Documents
```bash
for file in output/*_RAG_READY.json; do
    echo "File: $file"
    python3 rag_utils.py "$file" search "your_term"
done
```

### Get Document Statistics
```bash
python3 -c "
from rag_utils import RAGDataLoader
for f in ['output/Biological_Diversity_Act_2002_RAG_READY.json', 
          'output/Biological_Diversity_Act_RAG_READY.json',
          'output/Patents_Act_1970_RAG_READY.json']:
    loader = RAGDataLoader(f)
    stats = loader.get_statistics()
    print(f\"{stats['document_name']}: {stats['total_sections']} sections, {stats['total_pages']} pages\")
"
```

### Extract Data for ML Pipeline
```bash
python3 -c "
from rag_utils import RAGDataLoader
import json

loader = RAGDataLoader('output/Biological_Diversity_Act_2002_RAG_READY.json')
sections = loader.get_all_sections()

# Convert to embeddings format
data = [
    {
        'id': f\"P{s['page_number']}S{s['section_number']}\",
        'text': s.get('content', ''),
        'metadata': {
            'page': s['page_number'],
            'section': s['section_number'],
            'title': s.get('section_title', '')
        }
    }
    for s in sections
]

print(json.dumps(data, indent=2))
"
```

## 🐛 Troubleshooting

### "Module not found" error
```bash
# Make sure you're in the venv
source venv/bin/activate
cd /home/dhiraj/Desktop/SIH/rag_pipeline
python3 script.py
```

### "No JSON files found"
```bash
# Check input directory exists and has JSON files
ls /home/dhiraj/Desktop/SIH/Datasets/BIO/*.json
```

### "Permission denied"
```bash
# Make scripts executable
chmod +x data_prep.py batch_prepare.py rag_utils.py QUICKSTART.py
```

### "Empty output"
```bash
# Check that input files have valid JSON structure
python3 -m json.tool /path/to/input.json | head -20
```

## 📖 Code Examples

### Example 1: Basic Usage
```python
from rag_utils import RAGDataLoader

# Load document
loader = RAGDataLoader('output/Patents_Act_1970_RAG_READY.json')

# Get all sections
sections = loader.get_all_sections()
print(f"Total sections: {len(sections)}")

# Access raw text
for page_num in range(1, 4):
    text = loader.get_raw_text(page_num)
    print(f"Page {page_num}: {len(text)} chars")
```

### Example 2: Search & Analysis
```python
from rag_utils import RAGDataLoader

loader = RAGDataLoader('output/Patents_Act_1970_RAG_READY.json')

# Search for term
results = loader.search_sections('patent')
print(f"Found {len(results)} matches for 'patent'")

# Analyze top results
for r in results[:3]:
    print(f"  Section {r['section_number']} (Page {r['page_number']}): "
          f"{r['match_count']} matches")
```

### Example 3: Quality Validation
```python
from rag_utils import RAGDataLoader, RAGDataValidator

loader = RAGDataLoader('output/Patents_Act_1970_RAG_READY.json')

# Validate quality
validator = RAGDataValidator(loader)
is_valid, issues = validator.validate_all()

print(f"Valid: {is_valid}")
print(f"Issues found: {len(issues)}")

if issues:
    for issue in issues[:5]:
        print(f"  - {issue}")
```

### Example 4: Batch Analysis
```python
from rag_utils import RAGDataLoader, RAGDataComparator
from pathlib import Path

# Load all documents
files = list(Path('output').glob('*_RAG_READY.json'))
loaders = [RAGDataLoader(str(f)) for f in files]

# Compare
comparator = RAGDataComparator(*loaders)
comparison = comparator.compare_documents()

# Print summary
for doc, stats in comparison.items():
    print(f"{doc}: {stats['total_pages']} pages, {stats['total_sections']} sections")
```

## ✅ Status & Next Steps

### Current Phase: ✅ COMPLETE
- [x] OCR text cleaning
- [x] JSON validation
- [x] Section merging
- [x] Legal normalization
- [x] Batch processing
- [x] Data utilities
- [x] Documentation

### Next Phase: LLM Extraction
- [ ] Semantic extraction with Claude/GPT
- [ ] Entity recognition (acts, dates, amounts)
- [ ] Concept linking
- [ ] Section summarization
- [ ] Reference resolution

### Phase After: Embeddings & Vector DB
- [ ] Generate embeddings (OpenAI/Ollama)
- [ ] Store in vector database
- [ ] Build indexing system
- [ ] Create query interface

## 📞 Support

All files have:
- Comprehensive docstrings
- Detailed comments
- Error messages
- Logging output

Check logs for detailed processing information:
```bash
# Run with verbose output
python3 data_prep.py input.json output.json 2>&1 | tee processing.log
```

---

**Status**: ✅ **PHASE 1 COMPLETE**  
**Next**: LLM Extraction Phase  
**Ready**: RAG-ready JSON files + utilities  

Start with: `python3 QUICKSTART.py`
