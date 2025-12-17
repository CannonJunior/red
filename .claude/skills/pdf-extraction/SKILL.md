---
name: pdf-extraction
description: Extract text and tables from PDF files, handle multiple pages, and export to text format. Use when the user needs to extract or parse text content from PDF documents.
---

# PDF Text Extraction

## Quick start

Extract text from a PDF using pdfplumber:

```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"--- Page {i+1} ---")
        text = page.extract_text()
        print(text)
```

## Saving extracted text

```python
import pdfplumber

output_file = "extracted_text.txt"
with pdfplumber.open("document.pdf") as pdf:
    with open(output_file, 'w') as f:
        for page in pdf.pages:
            text = page.extract_text()
            f.write(text + "\n")
```

## Extracting tables

```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        if tables:
            print(tables[0])
```

## Troubleshooting

- **Scanned PDFs**: If the PDF is an image (scanned), OCR is required. Use pytesseract with pdf2image
- **Encoding issues**: Save output with `encoding='utf-8'` to handle special characters
- **Multiple pages**: Always iterate through `pdf.pages` to get all content
