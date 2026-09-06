# Document Extraction System - Quick Start Guide

## Installation

```bash
# 1. Navigate to the project directory
cd /home/dhiraj/Desktop/SIH/document_extraction

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# For full OCR support, also install Tesseract:
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr

# macOS:
brew install tesseract

# Windows:
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

## Basic Usage

### Command Line

Extract a PDF document to JSON:

```bash
python extract.py --input document.pdf --output output.json
```

With verbose logging:

```bash
python extract.py --input document.pdf --output output.json --verbose
```

### Python API

```python
from extractor import JSONFormatter, PDFProcessor, OCRHandler
from extractor.config import OCR_CONFIG

# Initialize components
ocr_handler = OCRHandler(OCR_CONFIG)
pdf_processor = PDFProcessor(ocr_handler)
json_formatter = JSONFormatter()

# Create a document
json_formatter.create_document(
    doc_name="My Document",
    doc_type="Act",
    total_pages=5
)

# Create and add a page
page = json_formatter.create_page(page_number=1, page_type="content")

# Add a section
section = json_formatter.create_section(
    section_number="1",
    section_title="Title",
    content="Content here...",
    is_continuation=False
)
page['sections'].append(section)

# Add page to document
json_formatter.add_page(page)

# Save to file
json_formatter.to_file("output.json")
```

## Key Components

### PDFProcessor
- Extracts text from PDF pages
- Handles both direct text extraction and OCR fallback
- Detects page types (content, table_of_contents, definitions, schedules, forms)
- Identifies continuation pages
- Extracts document structure (sections, rules, definitions)

### OCRHandler
- Performs OCR on scanned pages
- Corrects common OCR errors
- Validates text confidence
- Preserves formatting
- Marks unclear text regions

### JSONFormatter
- Creates structured JSON documents
- Manages pages, sections, rules, definitions
- Supports tables and forms
- Validates JSON structure
- Reads/writes from files

## JSON Output Structure

```json
{
  "document": {
    "document_name": "Document Name",
    "document_type": "Act",
    "source": "India Code",
    "total_pages": 5
  },
  "pages": [
    {
      "page_number": 1,
      "page_type": "content",
      "title": null,
      "chapter": null,
      "sections": [
        {
          "section_number": "1",
          "section_title": "Short title",
          "content": "This Act may be called...",
          "is_continuation": false
        }
      ],
      "rules": [],
      "definitions": [
        {
          "term": "Authority",
          "definition": "means the Central Government..."
        }
      ],
      "references": [],
      "tables": [],
      "forms": [],
      "raw_text": "Full page text..."
    }
  ]
}
```

## Features

### Document Recognition
- Automatic page type detection
- Support for multiple document types (Acts, Rules, Notifications)
- Continuation tracking across pages
- Section and rule number extraction

### OCR Capabilities
- Automatic OCR for scanned documents
- Error correction for common OCR mistakes
- Confidence scoring
- Unclear region marking

### Content Extraction
- Sections and subsections
- Rules and subrules
- Definitions
- Tables
- Forms
- References and cross-references

### Data Validation
- JSON schema validation
- Text confidence checking
- Missing field detection
- Structural integrity verification

## Configuration

Edit `extractor/config.py` to customize:

- **OCR Settings**: Language, PSM mode, confidence thresholds
- **Legal Patterns**: Regex patterns for sections, rules, definitions
- **Extraction Rules**: What to preserve, what to remove
- **Schema**: Default JSON structure templates

## Error Handling

The system handles:
- Missing or corrupted PDF files
- Pages with no extractable text
- OCR failures with fallback mechanisms
- Invalid JSON structures
- File I/O errors

Enable verbose logging to see detailed error information:

```bash
python extract.py --input document.pdf --verbose
```

## Examples

Run the examples script to see practical usage:

```bash
python examples.py
```

This demonstrates:
- Creating documents programmatically
- Processing pages
- Handling OCR
- Working with the JSON formatter

## Troubleshooting

### OCR not working
- Ensure Tesseract is installed and in PATH
- Check that pdf2image can convert PDF pages to images
- Verify PIL/Pillow is properly installed

### Text extraction issues
- PDF might be scanned (needs OCR)
- PDF might have copy protection
- Try enabling OCR fallback

### JSON validation errors
- Ensure all required fields are populated
- Check for encoding issues
- Verify page numbers are sequential

## Supported Document Types

- **Act**: Legislative acts and statutes
- **Rule**: Rules and regulations
- **Notification**: Government notifications and orders
- **Court Judgment**: Court decisions and orders
- **Patent**: Patent documents
- **Other**: General documents

## Performance Notes

- Processing speed depends on PDF quality and page complexity
- OCR is slower but more reliable for scanned documents
- Large documents (100+ pages) may take several minutes
- Memory usage scales with PDF size

## Future Enhancements

- [ ] Automatic document type detection
- [ ] Multi-language OCR support
- [ ] Table extraction and conversion
- [ ] Form field recognition
- [ ] Batch processing multiple PDFs
- [ ] Web API endpoint
- [ ] Database integration
- [ ] Advanced cross-reference linking

## Support

For issues or questions:
1. Check the examples.py for usage patterns
2. Review extractor/config.py for configuration options
3. Enable verbose logging for diagnostics
4. Check Python version compatibility (3.8+)
