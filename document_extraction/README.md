# Document Information Extraction System

A Python-based system for extracting structured information from PDF documents (particularly legal documents like Acts, Rules, and Notifications) and converting them into validated JSON format.

## Features

- **Page-by-page processing**: Extracts one page at a time without combining information
- **OCR support**: Automatically performs OCR on scanned PDF pages
- **Legal document parsing**: Extracts sections, rules, definitions, tables, forms, and schedules
- **Continuation tracking**: Identifies and marks content that continues from previous pages
- **Structured JSON output**: Follows a standardized schema for all documents
- **Error handling**: Robust OCR error correction and validation

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python extract.py --input document.pdf --output output.json
```

## Project Structure

```
document_extraction/
├── extractor/
│   ├── __init__.py
│   ├── pdf_processor.py      # Core PDF processing
│   ├── ocr_handler.py        # OCR and text recognition
│   ├── json_formatter.py     # JSON structure creation
│   └── config.py             # Configuration settings
├── extract.py                # Main entry point
├── requirements.txt          # Dependencies
└── README.md
```

## Document Types Supported

- Acts
- Rules
- Notifications
- Court Judgments
- Patents
- Other legal documents

## JSON Schema

Output follows the standardized schema with:
- Page metadata
- Sections and rules
- Definitions
- Tables and forms
- References and cross-references
- Raw text preservation

See `extractor/config.py` for full schema definition.
