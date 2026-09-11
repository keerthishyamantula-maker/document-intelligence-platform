# Document Intelligence Platform

AI Engineer Internship – Technical Case Study

## 1. Project Overview

The Document Intelligence Platform is an AI-powered document processing system for extracting and validating financial information from business documents.

The system accepts PDF, JPG, and PNG documents and supports:

- Invoice
- Balance Sheet
- Profit & Loss
- Cash Flow Statement

The platform performs document validation, OCR/text extraction, AI-based structured extraction, financial validation, confidence/evidence handling, database storage, and result visualization through a web dashboard.

---

## 2. System Workflow

The complete processing flow is:

Upload Document
→ File Validation
→ OCR / Text Extraction
→ AI-based Field & Table Extraction
→ Structured JSON
→ Financial Validation
→ Confidence / Evidence
→ Database Storage
→ PASS / FAILED
→ Dashboard

The system is designed to avoid inventing missing information. When information is not available in the source document, the corresponding value is represented as null or NOT_APPLICABLE where appropriate.

---

## 3. Supported Documents

### Invoice

The system extracts meaningful invoice information such as:

- Invoice number
- Invoice date
- Seller information
- Buyer information
- GST / tax information
- Line items
- Quantity
- Unit price
- Line totals
- Subtotal
- Tax
- Total
- Amount paid
- Change

### Balance Sheet

The system extracts financial statement information including:

- Reporting periods
- Capital
- Reserves
- Deposits
- Assets
- Liabilities
- Total assets
- Total capital and liabilities
- Other meaningful statement fields

### Profit & Loss

The system extracts:

- Reporting periods
- Interest earned
- Other income
- Total income
- Interest expended
- Operating expenses
- Provisions and contingencies
- Total expenditure
- Profit before minority interest
- Minority interest
- Consolidated net profit
- Appropriation-related values
- Other meaningful statement fields

### Cash Flow Statement

The system extracts:

- Reporting periods
- Operating activities
- Investing activities
- Financing activities
- Foreign exchange / translation effects where available
- Net increase or decrease in cash
- Opening cash and cash equivalents
- Closing cash and cash equivalents
- Other meaningful statement fields

---

## 4. Document Validation

Before extraction, uploaded documents are validated for:

- Supported file type
- Empty or corrupt files
- Readability
- Page count
- Maximum page limit

Documents exceeding the allowed page limit or failing basic validation are rejected before further processing.

---

## 5. OCR and Text Extraction

The platform supports both native text documents and scanned/image-based documents.

For scanned financial documents, OCR is performed using Tesseract OCR.

PDF pages are processed using PyMuPDF and OCR is applied when readable text is not directly available.

This allows the system to process image-based financial statements and invoices.

---

## 6. AI-Based Extraction

Google Gemini is used for AI-based structured document extraction.

The extracted OCR/text content is sent to the AI extraction service with the selected document type.

The AI is instructed to:

- Extract meaningful visible information
- Preserve the source values
- Return structured JSON
- Preserve reporting periods
- Extract tables and line items
- Use null when information is missing
- Never invent values
- Preserve negative values and parentheses where applicable

The resulting structured data is then passed to the financial validation layer.

---

## 7. Financial Validation

Document-specific financial reconciliation checks are implemented.

### Invoice Validation

Examples include:

- Quantity × Unit Price ≈ Line Total
- Line totals reconcile with subtotal / total
- Taxable amount + tax ≈ total
- Amount paid − total ≈ change

### Balance Sheet Validation

Examples include:

- Total Assets ≈ Total Capital and Liabilities
- Component values reconcile with reported totals
- Validation is performed separately for each reporting period

### Profit & Loss Validation

Examples include:

- Interest Earned + Other Income ≈ Total Income
- Interest Expended + Operating Expenses + Provisions and Contingencies ≈ Total Expenditure
- Total Income − Total Expenditure ≈ Consolidated Net Profit before Minority Interest
- Profit before Minority Interest − Minority Interest ≈ Consolidated Net Profit attributable to Group
- Current Profit + Brought Forward Profit ≈ Total Available for Appropriation
- Comparative periods are validated separately

### Cash Flow Validation

Examples include:

- Operating + Investing + Financing + FX / Translation effects ≈ Net Increase / Decrease
- Opening Cash + Net Increase / Decrease + applicable adjustments ≈ Closing Cash
- Parentheses are interpreted as negative values
- Each reporting period is validated separately

Each validation check records the relevant formula, inputs, calculated value, reported value, variance, and result.

Possible validation results are:

- PASS
- FAIL
- NOT_APPLICABLE

If a required value is not present in the source document, the system does not invent it.

---

## 8. API

The backend is implemented using FastAPI.

### Health Check

```text
GET /api/v1/health
Process Document
POST /api/v1/documents/process

Multipart form fields:

file
document_type
List Documents
GET /api/v1/documents
Get Document Result
GET /api/v1/documents/{document_name}
Swagger / OpenAPI

The FastAPI Swagger interface is available at:

https://document-intelligence-platform-4d2l.onrender.com/docs
9. Frontend

The frontend provides a simple dashboard for:

Selecting the document type
Uploading documents
Processing documents
Viewing validation status
Viewing extracted fields
Viewing financial validation results
Viewing issues
Viewing raw structured JSON
Viewing previously processed documents

The frontend communicates with the FastAPI backend through REST APIs.

10. Database

The application uses SQLAlchemy for database persistence.

Processed documents and their structured processing results are stored so that they can be retrieved through the document APIs and dashboard.

11. Project Structure
document-intelligence-starter/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       └── documents.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── logging.py
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── document_validation_service.py
│   │   │   ├── ocr_service.py
│   │   │   ├── extraction_service.py
│   │   │   ├── financial_validation_service.py
│   │   │   └── document_service.py
│   │   ├── main.py
│   │   └── validators.py
│   │
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── templates/
│
├── docs/
│   ├── README.md
│   ├── ARCHITECTURE.md
│   └── Document Intelligence Platform Architecture.png
│
├── sample_outputs/
├── data/
├── Dockerfile
├── .dockerignore
├── .env.example
├── .gitignore
└── README.md
12. Architecture

The system architecture is documented separately.

Architecture diagram:

The architecture contains the frontend, FastAPI backend, OCR/text extraction, AI extraction, financial validation, database, and external services.

13. Testing

Automated tests are included for:

API behaviour
Document extraction
Financial validation

The project test suite currently passes successfully.

Run tests locally with:

pytest -q
14. Local Setup

Create and activate a Python virtual environment.

Install dependencies:

pip install -r backend/requirements.txt

Configure environment variables using:

.env.example

Start the application:

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001

Open:

http://127.0.0.1:8001

Swagger:

http://127.0.0.1:8001/docs
15. Deployment

The application is deployed as a Docker-based web service on Render.

Production URL:

https://document-intelligence-platform-4d2l.onrender.com

Swagger:

https://document-intelligence-platform-4d2l.onrender.com/docs

The Docker image installs the Tesseract OCR system dependency required for scanned document processing.

Secrets and API keys are not committed to the repository.

16. Environment Variables

API keys are configured through environment variables.

Example:

GEMINI_API_KEY=your_api_key_here

The actual API key must never be committed to GitHub.

The repository provides .env.example as a configuration reference.

17. Error Handling

The system handles processing failures through structured error responses.

Examples include:

Unsupported document type
Invalid file
Empty document
Excessive page count
OCR failure
AI extraction failure
Financial validation failure

When AI extraction fails, the system does not generate fabricated financial data.

18. AI Provider Quota

The application uses Google Gemini for AI-based extraction.

Availability of AI extraction depends on the configured Gemini API quota. If the provider returns a quota/resource exhaustion error, the application reports the extraction failure instead of generating or substituting fabricated values.

19. Security

Security-related practices include:

API keys stored through environment variables
.env excluded from Git
.env.example provided for configuration
Input file validation
File type validation
Page count validation
Exception handling
No hardcoded API credentials
20. Repository

GitHub repository:

https://github.com/keerthishyamantula-maker/document-intelligence-platform
21. Summary

This project implements an end-to-end AI-powered document intelligence workflow combining:

Document validation
OCR
AI-based extraction
Structured JSON generation
Financial reconciliation
REST APIs
Database persistence
Web dashboard
Automated testing
Docker-based deployment

The implementation is designed specifically for the four required financial document categories: Invoice, Balance Sheet, Profit & Loss, and Cash Flow Statement.
## Live Deployment

### Frontend / Application
https://document-intelligence-platform-4d2l.onrender.com

### API Documentation (Swagger)
https://document-intelligence-platform-4d2l.onrender.com/docs

### Health Check
https://document-intelligence-platform-4d2l.onrender.com/api/v1/health

### GitHub Repository
https://github.com/keerthishyamantula-maker/document-intelligence-platform