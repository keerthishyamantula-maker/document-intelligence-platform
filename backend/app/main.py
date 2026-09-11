from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.app.core.database import initialize_database
from backend.app.repositories.document_repository import DocumentRepository
from backend.app.services.document_validation_service import validate_document
from backend.app.services.ocr_service import extract_text_from_document
from backend.app.services.extraction_service import extract_structured_data
from backend.app.services.financial_validation_service import validate_financial_document


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Document Intelligence API",
    description=(
        "AI-powered financial document extraction, "
        "validation, and storage API."
    ),
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

FRONTEND_DIR = BASE_DIR / "frontend"
TEMPLATES_DIR = FRONTEND_DIR / "templates"
STATIC_DIR = FRONTEND_DIR / "static"


# ============================================================
# FRONTEND STATIC FILES
# ============================================================

if STATIC_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )


templates = Jinja2Templates(
    directory=str(TEMPLATES_DIR)
)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

try:
    initialize_database()
except Exception:
    # Application should still start.
    # Database failures are handled when database operations occur.
    pass


# ============================================================
# SUPPORTED DOCUMENT TYPES
# ============================================================

SUPPORTED_DOCUMENT_TYPES = {
    "invoice",
    "balance_sheet",
    "profit_and_loss",
    "cash_flow_statement",
}


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/v1/health")
def health():
    return {
        "status": "ok"
    }


# ============================================================
# FRONTEND
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def frontend(request: Request):

    index_file = TEMPLATES_DIR / "index.html"

    if not index_file.exists():
        raise HTTPException(
            status_code=500,
            detail="Frontend template index.html was not found.",
        )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request
        },
    )


# ============================================================
# DOCUMENT VALIDATION ENDPOINT
# ============================================================

@app.post("/api/v1/documents/validate")
async def validate_uploaded_document(
    file: UploadFile = File(...)
):

    try:

        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required.",
            )

        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        return validate_document(
            filename=file.filename,
            content=content,
        )

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Document validation failed.",
        )


# ============================================================
# PROCESS DOCUMENT
# ============================================================

@app.post("/api/v1/documents/process")
async def process_uploaded_document(

    file: UploadFile = File(...),

    # IMPORTANT:
    # document_type comes from multipart/form-data.
    #
    # This MUST use Form(...)
    # otherwise FastAPI treats it as a query parameter.
    document_type: str = Form(...),
):

    # ========================================================
    # NORMALIZE DOCUMENT TYPE
    # ========================================================

    document_type = document_type.strip().lower()


    # ========================================================
    # VALIDATE DOCUMENT TYPE
    # ========================================================

    if document_type not in SUPPORTED_DOCUMENT_TYPES:

        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "UNSUPPORTED_DOCUMENT_TYPE",
                "message": (
                    f"Unsupported document type: {document_type}. "
                    f"Supported types are: "
                    f"{', '.join(sorted(SUPPORTED_DOCUMENT_TYPES))}"
                ),
            },
        )


    # ========================================================
    # VALIDATE FILENAME
    # ========================================================

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "MISSING_FILENAME",
                "message": (
                    "Uploaded file must have a filename."
                ),
            },
        )


    filename = file.filename


    # ========================================================
    # READ FILE
    # ========================================================

    try:

        content = await file.read()

    except Exception:

        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "FILE_READ_FAILED",
                "message": (
                    "Unable to read uploaded file."
                ),
            },
        )


    # ========================================================
    # EMPTY FILE CHECK
    # ========================================================

    if not content:

        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "EMPTY_FILE",
                "message": (
                    "Uploaded file is empty."
                ),
            },
        )


    # ========================================================
    # DOCUMENT VALIDATION
    # ========================================================

    try:

        validation = validate_document(
            filename=filename,
            content=content,
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DOCUMENT_VALIDATION_FAILED",
                "message": (
                    "Document validation failed."
                ),
            },
        )


    # ========================================================
    # STOP IF FILE VALIDATION FAILED
    # ========================================================

    if validation.get("status") != "PASS":

        return {
            "processing_status": "FAILED",

            "file_name": filename,

            "document_type": document_type,

            "file_validation": validation,

            "ocr": None,

            "extraction": None,

            "financial_validation": {
                "document_type": document_type,
                "checks": [],
                "overall_status": "NOT_APPLICABLE",
                "issues": [
                    {
                        "message": (
                            "Financial validation was not "
                            "performed because document "
                            "validation failed."
                        )
                    }
                ],
            },
        }


    # ========================================================
    # OCR / TEXT EXTRACTION
    # ========================================================

    try:

        ocr_result = extract_text_from_document(
            filename=filename,
            content=content,
        )

    except Exception:

        ocr_result = {
            "success": False,
            "ocr_used": True,
            "pages": [],
            "text": "",
            "processing_time_ms": 0,
            "error_code": "OCR_FAILED",
            "message": "Text extraction failed.",
        }


    # ========================================================
    # STOP IF OCR FAILED
    # ========================================================

    if not ocr_result.get("success"):

        return {
            "processing_status": "FAILED",

            "file_name": filename,

            "document_type": document_type,

            "file_validation": validation,

            "ocr": ocr_result,

            "extraction": {
                "success": False,
                "error_code": "OCR_FAILED",
                "message": (
                    "Document OCR failed."
                ),
            },

            "financial_validation": {
                "document_type": document_type,
                "checks": [],
                "overall_status": "NOT_APPLICABLE",
                "issues": [
                    {
                        "message": (
                            "Financial validation was not "
                            "performed because OCR failed."
                        )
                    }
                ],
            },
        }


    # ========================================================
    # AI EXTRACTION
    # ========================================================

    try:

        extraction_result = extract_structured_data(
            document_type=document_type,
            ocr_pages=ocr_result.get("pages", []),
        )

    except Exception:

        extraction_result = {
            "success": False,
            "error_code": "GEMINI_EXTRACTION_FAILED",
            "message": "AI extraction failed.",
        }


    # ========================================================
    # STOP IF AI EXTRACTION FAILED
    # ========================================================

    if not extraction_result.get("success"):

        return {
            "processing_status": "FAILED",

            "file_name": filename,

            "document_type": document_type,

            "file_validation": validation,

            "ocr": {
                "success": ocr_result.get("success"),
                "ocr_used": ocr_result.get("ocr_used"),
                "processing_time_ms": (
                    ocr_result.get("processing_time_ms")
                ),
            },

            "extraction": extraction_result,

            "financial_validation": {
                "document_type": document_type,
                "checks": [],
                "overall_status": "NOT_APPLICABLE",
                "issues": [
                    {
                        "message": (
                            "Financial validation was not "
                            "performed because AI extraction "
                            "failed."
                        )
                    }
                ],
            },
        }


    # ========================================================
    # FINANCIAL VALIDATION
    # ========================================================

    try:

        financial_validation = validate_financial_document(
            document_type=document_type,
            extracted_data=(
                extraction_result.get("data", {})
            ),
        )

    except Exception as exc:

        financial_validation = {
            "document_type": document_type,
            "checks": [],
            "overall_status": "NOT_APPLICABLE",
            "issues": [
                {
                    "message": (
                        "Financial validation could not "
                        "be completed."
                    ),
                    "error": str(exc),
                }
            ],
        }


    # ========================================================
    # PROCESSING STATUS
    # ========================================================

    processing_status = "PASS"

    if financial_validation.get(
        "overall_status"
    ) == "FAIL":

        processing_status = "FAILED"


    # ========================================================
    # FINAL RESULT
    # ========================================================

    result = {

        "processing_status": processing_status,

        "file_name": filename,

        "document_type": document_type,

        "file_validation": validation,

        "ocr": {
            "success": ocr_result.get("success"),
            "ocr_used": ocr_result.get("ocr_used"),
            "processing_time_ms": (
                ocr_result.get("processing_time_ms")
            ),
        },

        "extraction": extraction_result,

        "financial_validation": financial_validation,
    }


    # ========================================================
    # SAVE TO DATABASE
    # ========================================================

    try:

        DocumentRepository.save(
            document_name=filename,
            document_type=document_type,
            processing_status=processing_status,
            result=result,
        )

    except TypeError:

        # Compatibility with an alternative repository
        # method signature.

        try:

            DocumentRepository.save(
                filename,
                document_type,
                processing_status,
                result,
            )

        except Exception:
            pass

    except Exception:
        # Do not expose database internals to the client.
        pass


    # ========================================================
    # RETURN RESULT
    # ========================================================

    return result


# ============================================================
# LIST DOCUMENTS
# ============================================================

@app.get("/api/v1/documents")
def list_documents():

    try:

        documents = DocumentRepository.get_all()

        return {
            "documents": documents,
            "count": len(documents),
        }

    except Exception:

        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DATABASE_READ_FAILED",
                "message": (
                    "Unable to retrieve documents."
                ),
            },
        )


# ============================================================
# GET DOCUMENT BY NAME
# ============================================================

@app.get("/api/v1/documents/{document_name}")
def get_document_by_name(
    document_name: str
):

    try:

        document = DocumentRepository.get_by_name(
            document_name=document_name
        )

        if document is None:

            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "DOCUMENT_NOT_FOUND",
                    "message": (
                        f"Document '{document_name}' "
                        "was not found."
                    ),
                },
            )

        return document

    except HTTPException:
        raise

    except Exception:

        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DATABASE_READ_FAILED",
                "message": (
                    "Unable to retrieve document."
                ),
            },
        )