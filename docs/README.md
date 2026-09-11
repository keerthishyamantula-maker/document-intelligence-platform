AI-powered document extraction and financial validation platform for financial documents.

## Overview

This project processes financial documents such as invoices, balance sheets, profit and loss statements, and cash flow statements.

The platform supports PDF, JPG, and PNG files and performs:

1. File validation
2. OCR / text extraction
3. AI-based field and table extraction
4. Structured JSON generation
5. Financial validation
6. Confidence and evidence reporting
7. Document storage
8. Processing status
9. Dashboard-based result viewing

## Supported Documents

The platform supports the following document types:

- Invoice
- Balance Sheet
- Profit & Loss
- Cash Flow Statement

Supported API values:

```text
invoice
balance_sheet
profit_and_loss
cash_flow_statement
Processing Workflow
Upload Document
       |
       v
File Validation
       |
       v
OCR / Text Extraction
       |
       v
AI-based Field & Table Extraction
       |
       v
Structured JSON
       |
       v
Financial Validation
       |
       v
Confidence & Evidence
       |
       v
Database Storage
       |
       v
PASS / FAILED
       |
       v
Dashboard
Features
Document Validation

The system validates:

Supported file type
File readability
Corrupt or empty files
Maximum page limit of 3 pages
Supported document type

Unsupported or invalid documents are rejected before processing.

OCR and Text Extraction

The platform supports both:

Native text-based documents
Scanned/image-based documents

Tesseract OCR is used for scanned documents.

AI Extraction

Google Gemini is used for AI-based document understanding and structured extraction.

The extraction process is designed to:

Extract meaningful visible information
Preserve document values
Extract tables and fields
Identify comparative periods where available
Return null when a value is missing
Never invent missing values
Financial Validation

Financial checks are performed according to document type.

Invoice

Examples of validations:

Quantity × Unit Price ≈ Line Total

Sum of Line Totals ≈ Subtotal / Total

Taxable Amount + Tax ≈ Total

Cash Paid - Total ≈ Change
Balance Sheet

Examples:

Total Capital & Liabilities ≈ Total Assets

Capital / Liability Components ≈ Total Capital & Liabilities

Asset Components ≈ Total Assets

Checks are performed separately for each available reporting period.

Profit & Loss

Examples:

Interest Earned + Other Income ≈ Total Income

Interest Expended
+ Operating Expenses
+ Provisions & Contingencies
≈ Total Expenditure

Total Income - Total Expenditure
≈ Consolidated Net Profit before Minority Interest

Profit before Minority Interest - Minority Interest
≈ Consolidated Net Profit attributable to Group

Current Profit + Brought Forward Profit
≈ Total Available for Appropriation

Comparative periods are validated independently when available.

Cash Flow Statement

Examples:

Operating + Investing + Financing
+ FX / Translation Adjustments
≈ Net Increase / Decrease in Cash

Opening Cash
+ Net Increase / Decrease
+ Applicable Adjustments
≈ Closing Cash

Parentheses are interpreted as negative values.

If a required value is not present in the document, the corresponding validation is marked as:

NOT_APPLICABLE

No missing financial value is invented.

API Endpoints
Health Check
GET /api/v1/health

Example response:

{
  "status": "ok"
}
Process Document
POST /api/v1/documents/process

Multipart form fields:

file
document_type

Supported document type values:

invoice
balance_sheet
profit_and_loss
cash_flow_statement

Example:

file = sample.pdf
document_type = balance_sheet
List Documents
GET /api/v1/documents

Returns previously processed documents stored by the application.

Get Document
GET /api/v1/documents/{document_name}

Returns the stored result for a specific document.

Validate Document
POST /api/v1/documents/validate

Validates an uploaded document before processing.

API Documentation

Interactive Swagger API documentation is available at:

https://document-intelligence-platform-4d2l.onrender.com/docs
Deployment

The application is deployed as a Docker-based web service.

Production application:

https://document-intelligence-platform-4d2l.onrender.com

Backend API:

https://document-intelligence-platform-4d2l.onrender.com/api/v1

Health check:

https://document-intelligence-platform-4d2l.onrender.com/api/v1/health

Swagger:

https://document-intelligence-platform-4d2l.onrender.com/docs
Technology Stack
Backend
Python
FastAPI
Pydantic
SQLAlchemy
PyMuPDF
PyTesseract
Tesseract OCR
Google Gemini
Frontend
HTML
CSS
JavaScript
Jinja2 templates
Database
SQLite
SQLAlchemy ORM
Deployment
Docker
Render
Testing
Pytest
HTTPX
Project Structure
document-intelligence-platform/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       └── documents.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── logging.py
│   │   │
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── document_validation_service.py
│   │   │   ├── ocr_service.py
│   │   │   ├── extraction_service.py
│   │   │   ├── financial_validation_service.py
│   │   │   └── document_service.py
│   │   └── main.py
│   │
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│
├── docs/
│   └── README.md
│
├── sample_outputs/
│
├── Dockerfile
├── .dockerignore
├── .env.example
├── .gitignore
└── README.md
Error Handling

The API returns structured error information for invalid or unsupported requests.

Examples include:

UNSUPPORTED_DOCUMENT_TYPE
INVALID_FILE_TYPE
DOCUMENT_TOO_LARGE
PAGE_LIMIT_EXCEEDED
OCR_TEXT_EMPTY
GEMINI_EXTRACTION_FAILED

The application does not silently generate values when extraction fails.

Processing Status

A document can have the following processing outcomes:

PASS

The document is valid, extraction succeeds, and applicable financial validations pass.

FAILED

The document is invalid, unsupported, corrupted, unprocessed, extraction fails, or applicable financial validation fails.

NOT_APPLICABLE

Used for individual financial checks when the required information is not available in the document.

Security
API keys are stored using environment variables.
.env is excluded from Git.
.env.example is provided for configuration reference.
No API keys or secrets are committed to the repository.
Uploaded documents are validated before processing.
Testing

The project includes automated tests for:

API endpoints
Document validation
Financial validation
Number parsing
Invoice calculations
Balance sheet reconciliation
Error handling

Run the test suite with:

pytest -q
Local Setup

Create and activate a virtual environment:

python -m venv .venv

Windows:

.venv\Scripts\activate

Install dependencies:

pip install -r backend/requirements.txt

Configure environment variables using .env.example.

Start the application:

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001

Open:

http://127.0.0.1:8001

Swagger:

http://127.0.0.1:8001/docs
AI Provider

The application uses Google Gemini for AI-based extraction.

The API key must be supplied through an environment variable and must not be committed to source control.

If the AI provider is unavailable or quota is exhausted, the application reports the extraction failure instead of inventing document values.

Limitations
Maximum supported document size is limited by the application requirements.
Maximum supported page count is 3 pages.
OCR accuracy depends on document scan quality.
Very low-quality or heavily distorted documents may produce incomplete extraction.
AI extraction depends on availability of the configured AI provider.
The free Render instance may spin down after inactivity.
Repository

Source code:

https://github.com/keerthishyamantula-maker/document-intelligence-platform
Documentation

Additional project documentation and solution materials are maintained in the docs directory.