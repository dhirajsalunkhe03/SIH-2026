# Quick Reference - Using Extracted Legal Documents

## 📁 Location of Extracted Files

```
/home/dhiraj/Desktop/SIH/Datasets/BIO/
├── Biological_Diversity_Act_2002.json (49 KB, 15 pages)
├── Biological_Diversity_Act.json (93 KB, 25 pages)
└── Patents_Act_1970.json (269 KB, 72 pages)
```

## 🚀 Quick Start - Python Examples

### 1. Load and Explore a Document

```python
import json

# Load the extracted document
with open('/home/dhiraj/Desktop/SIH/Datasets/BIO/Patents_Act_1970.json', 'r') as f:
    document = json.load(f)

# View document metadata
print(f"Document: {document['document']['document_name']}")
print(f"Total Pages: {document['document']['total_pages']}")
print(f"Type: {document['document']['document_type']}")

# Access pages
pages = document['pages']
print(f"Number of pages extracted: {len(pages)}")
```

### 2. Extract All Text Content

```python
# Get all text from the document
all_text = []
for page in document['pages']:
    if page['raw_text'].strip():
        all_text.append(page['raw_text'])

full_text = '\n\n'.join(all_text)
print(f"Total characters: {len(full_text)}")

# Save to file
with open('full_document_text.txt', 'w') as f:
    f.write(full_text)
```

### 3. Extract Sections

```python
# Extract all sections from all pages
all_sections = []
for page in document['pages']:
    for section in page.get('sections', []):
        all_sections.append({
            'page': page['page_number'],
            'section': section['section_number'],
            'title': section['section_title'],
            'content': section['content'],
            'is_continuation': section['is_continuation']
        })

print(f"Total sections: {len(all_sections)}")

# Print first 5 sections
for section in all_sections[:5]:
    print(f"Section {section['section']} (Page {section['page']}): {section['title']}")
```

### 4. Search for Keywords

```python
# Search for specific terms in document
search_term = "biodiversity"
results = []

for page in document['pages']:
    text = page['raw_text']
    if search_term.lower() in text.lower():
        results.append({
            'page': page['page_number'],
            'snippet': text[:200] + '...',
            'matches': text.lower().count(search_term.lower())
        })

print(f"Found '{search_term}' in {len(results)} pages")
for result in results[:3]:
    print(f"  Page {result['page']}: {result['matches']} matches")
```

### 5. Extract Definitions

```python
# Extract all definitions
all_definitions = []
for page in document['pages']:
    for defn in page.get('definitions', []):
        all_definitions.append({
            'page': page['page_number'],
            'term': defn['term'],
            'definition': defn['definition']
        })

print(f"Total definitions: {len(all_definitions)}")
for defn in all_definitions[:5]:
    print(f"{defn['term']}: {defn['definition']}")
```

### 6. Get Page Statistics

```python
# Analyze document structure
statistics = {
    'total_pages': len(document['pages']),
    'pages_with_content': 0,
    'empty_pages': 0,
    'total_sections': 0,
    'total_rules': 0,
    'total_definitions': 0,
    'page_types': {}
}

for page in document['pages']:
    # Count pages with content
    if page['raw_text'].strip():
        statistics['pages_with_content'] += 1
    else:
        statistics['empty_pages'] += 1
    
    # Count page types
    page_type = page['page_type']
    statistics['page_types'][page_type] = statistics['page_types'].get(page_type, 0) + 1
    
    # Count extracted elements
    statistics['total_sections'] += len(page.get('sections', []))
    statistics['total_rules'] += len(page.get('rules', []))
    statistics['total_definitions'] += len(page.get('definitions', []))

print(f"Pages with content: {statistics['pages_with_content']}/{statistics['total_pages']}")
print(f"Page types: {statistics['page_types']}")
print(f"Sections: {statistics['total_sections']}")
```

## 📊 JSON Structure Reference

### Document Level
```json
{
  "document": {
    "document_name": "Patents Act, 1970",
    "document_type": "Act",
    "source": "India Code",
    "total_pages": 72
  },
  "pages": [...]
}
```

### Page Level
```json
{
  "page_number": 1,
  "page_type": "content",           // content, table_of_contents, definition, schedule, form, preamble
  "title": null,
  "chapter": null,
  "sections": [...],
  "rules": [...],
  "definitions": [...],
  "references": [],
  "tables": [],
  "forms": [],
  "raw_text": "Full text of the page..."
}
```

### Section/Rule Level
```json
{
  "section_number": "1",
  "section_title": "Short title",
  "content": "This Act may be called...",
  "is_continuation": false
}
```

## 🔍 Common Use Cases

### Use Case 1: Text Mining
```python
# Extract all sections for text mining/NLP analysis
sections_text = []
for page in document['pages']:
    for section in page['sections']:
        if section['content']:
            sections_text.append(section['content'])

# Can then use with spaCy, NLTK, etc.
```

### Use Case 2: Document Comparison
```python
# Compare two acts
def compare_documents(doc1_path, doc2_path):
    with open(doc1_path) as f:
        doc1 = json.load(f)
    with open(doc2_path) as f:
        doc2 = json.load(f)
    
    sections1 = sum(len(p['sections']) for p in doc1['pages'])
    sections2 = sum(len(p['sections']) for p in doc2['pages'])
    
    print(f"Doc1 sections: {sections1}")
    print(f"Doc2 sections: {sections2}")

compare_documents('Biological_Diversity_Act_2002.json', 
                  'Biological_Diversity_Act.json')
```

### Use Case 3: Build Search Index
```python
# Create searchable index
search_index = {}
for page in document['pages']:
    for section in page['sections']:
        if section['section_number'] not in search_index:
            search_index[section['section_number']] = {
                'title': section['section_title'],
                'pages': [],
                'content': []
            }
        search_index[section['section_number']]['pages'].append(page['page_number'])
        if section['content']:
            search_index[section['section_number']]['content'].append(section['content'])

# Search
query_section = "1"
if query_section in search_index:
    print(search_index[query_section])
```

## 📝 Document-Specific Notes

### Biological Diversity Act, 2002 (15 pages)
- Focus: Conservation of biological resources
- Contains: Preliminary sections, regulation of access to biodiversity
- Key sections: 1-12 (basic definitions and authorities)

### Biological Diversity Act (25 pages)
- Similar to 2002 Act but with different provisions
- Contains: Additional rules and definitions
- Key sections: Multiple chapters with detailed provisions

### Patents Act, 1970 (72 pages)
- Focus: Patent registration and protection
- Contains: Comprehensive patent law provisions
- Key sections: Multiple chapters covering applications, grants, revocation

## ⚙️ Advanced Features

### Re-extraction (if needed)
```bash
cd /home/dhiraj/Desktop/SIH/document_extraction
source venv/bin/activate
python3 extract.py --input /path/to/document.pdf --output output.json --verbose
```

### Validate JSON
```python
import json

def validate_json_file(filepath):
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Check required fields
        required_doc_fields = ['document_name', 'document_type', 'total_pages']
        required_page_fields = ['page_number', 'page_type', 'raw_text']
        
        doc = data['document']
        for field in required_doc_fields:
            assert field in doc, f"Missing {field}"
        
        for page in data['pages']:
            for field in required_page_fields:
                assert field in page, f"Page {page['page_number']} missing {field}"
        
        print("✅ JSON is valid!")
        return True
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False

validate_json_file('Patents_Act_1970.json')
```

## 📞 Support & Documentation

- **Full Documentation**: See `/home/dhiraj/Desktop/SIH/document_extraction/README.md`
- **Quick Start Guide**: See `/home/dhiraj/Desktop/SIH/document_extraction/QUICKSTART.md`
- **Examples**: See `/home/dhiraj/Desktop/SIH/document_extraction/examples.py`
- **Extraction Tool**: `/home/dhiraj/Desktop/SIH/document_extraction/extract.py`

---
**Created**: 2026-09-05  
**Ready for Use**: ✅ All 3 documents (112 pages total)
