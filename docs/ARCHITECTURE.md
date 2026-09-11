 System Architecture

```mermaid
flowchart TD
    A[User] --> B[Frontend Web Application]

    B --> C[FastAPI Backend]

    C --> D[Document Validation]
    D --> E[OCR / Text Extraction]

    E --> F[AI Field & Table Extraction]
    F --> G[Structured JSON]

    G --> H[Financial Validation]

    H --> I[Confidence & Evidence]
    I --> J[Document Repository]
    J --> K[(SQLite Database)]

    H --> L[PASS / FAILED Result]

    L --> B

    F --> M[Google Gemini]
    E --> N[Tesseract OCR]

    C --> O[REST API]
    O --> P[Swagger / OpenAPI]

    B --> Q[Dashboard]
    Q --> R[Document Result View]
    R --> S[Raw JSON View]
Processing Flow

The platform processes documents through the following pipeline:

Upload → Document Validation → OCR/Text Extraction → AI-based Field & Table Extraction → Structured JSON → Financial Validation → Confidence/Evidence → Storage → PASS/FAILED → Dashboard

Main Components
Frontend

Provides:

Document type selection
PDF/JPG/PNG upload
Processing interface
Dashboard
Extracted field display
Financial validation results
Raw JSON view
FastAPI Backend

Provides the REST API and coordinates document processing.

Document Validation

Checks:

Supported file type
Readability
Corrupt or empty documents
Maximum page count
Supported document type
OCR / Text Extraction

Handles both:

Native text-based documents
Scanned/image-based documents

Tesseract OCR is used for image-based documents.

AI Extraction

Google Gemini performs AI-based extraction of:

Document fields
Tables
Financial values
Comparative periods
Other meaningful visible information

Missing values are represented as null rather than invented.

Financial Validation

Performs document-specific arithmetic and reconciliation checks for:

Invoice
Balance Sheet
Profit & Loss
Cash Flow Statement
Database

Stores processed document information and structured results.

API Documentation

Swagger/OpenAPI is available through the FastAPI documentation interface.