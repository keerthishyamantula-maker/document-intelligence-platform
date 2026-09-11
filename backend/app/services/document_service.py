from typing import Any

from backend.app.repositories.document_repository import (
    DocumentRepository,
)
from backend.app.services.document_validation_service import (
    validate_document,
)
from backend.app.services.ocr_service import (
    extract_text_from_document,
)
from backend.app.services.extraction_service import (
    extract_structured_data,
)
from backend.app.services.financial_validation_service import (
    validate_financial_document,
)


SUPPORTED_DOCUMENT_TYPES = {
    "invoice",
    "balance_sheet",
    "profit_and_loss",
    "cash_flow_statement",
}


def process_document(
    filename: str,
    content: bytes,
    document_type: str,
) -> dict[str, Any]:
    """
    Complete document processing pipeline.

    Pipeline:
        1. Validate file
        2. OCR
        3. Gemini extraction
        4. Financial validation
        5. Persist result
        6. Return structured JSON
    """

    # --------------------------------------------------------
    # 1. Validate document type
    # --------------------------------------------------------

    if document_type not in SUPPORTED_DOCUMENT_TYPES:
        return {
            "processing_status": "FAILED",
            "file_name": filename,
            "document_type": document_type,
            "file_validation": {
                "status": "FAILED",
                "message": "Unsupported document type.",
            },
            "issues": [
                {
                    "message": (
                        f"Unsupported document type: {document_type}"
                    )
                }
            ],
        }

    # --------------------------------------------------------
    # 2. Validate file
    # --------------------------------------------------------

    try:
        file_validation = validate_document(
            filename=filename,
            content=content,
        )
    except Exception:
        return {
            "processing_status": "FAILED",
            "file_name": filename,
            "document_type": document_type,
            "file_validation": {
                "status": "FAILED",
                "message": "Document validation failed.",
            },
            "issues": [
                {
                    "message": "Unable to validate uploaded document."
                }
            ],
        }

    if file_validation.get("status") != "PASS":
        result = {
            "processing_status": "FAILED",
            "file_name": filename,
            "document_type": document_type,
            "file_validation": file_validation,
            "issues": [
                {
                    "message": "Document failed file validation."
                }
            ],
        }

        _save_result(
            filename=filename,
            document_type=document_type,
            processing_status="FAILED",
            result=result,
        )

        return result

    # --------------------------------------------------------
    # 3. OCR
    # --------------------------------------------------------

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

    if not ocr_result.get("success"):
        result = {
            "processing_status": "FAILED",
            "file_name": filename,
            "document_type": document_type,
            "file_validation": file_validation,
            "ocr": ocr_result,
            "issues": [
                {
                    "message": "OCR/text extraction failed."
                }
            ],
        }

        _save_result(
            filename=filename,
            document_type=document_type,
            processing_status="FAILED",
            result=result,
        )

        return result

    # --------------------------------------------------------
    # 4. Gemini extraction
    # --------------------------------------------------------

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

    if not extraction_result.get("success"):
        result = {
            "processing_status": "FAILED",
            "file_name": filename,
            "document_type": document_type,
            "file_validation": file_validation,
            "ocr": {
                "success": ocr_result.get("success"),
                "ocr_used": ocr_result.get("ocr_used"),
                "processing_time_ms": ocr_result.get(
                    "processing_time_ms"
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
                            "Financial validation was not performed "
                            "because extraction failed."
                        )
                    }
                ],
            },
            "issues": [
                {
                    "message": "Gemini extraction failed."
                }
            ],
        }

        _save_result(
            filename=filename,
            document_type=document_type,
            processing_status="FAILED",
            result=result,
        )

        return result

    # --------------------------------------------------------
    # 5. Financial validation
    # --------------------------------------------------------

    try:
        financial_validation = validate_financial_document(
            document_type=document_type,
            extracted_data=extraction_result.get(
                "data",
                {},
            ),
        )
    except Exception:
        financial_validation = {
            "document_type": document_type,
            "checks": [],
            "overall_status": "NOT_APPLICABLE",
            "issues": [
                {
                    "message": (
                        "Financial validation could not be completed."
                    )
                }
            ],
        }

    # --------------------------------------------------------
    # 6. Determine processing status
    # --------------------------------------------------------

    financial_status = financial_validation.get(
        "overall_status",
        "NOT_APPLICABLE",
    )

    failed_checks = [
        check
        for check in financial_validation.get("checks", [])
        if check.get("status") == "FAIL"
    ]

    if failed_checks:
        processing_status = "FAILED"
    else:
        processing_status = "PASS"

    # --------------------------------------------------------
    # 7. Build final response
    # --------------------------------------------------------

    result = {
        "processing_status": processing_status,
        "file_name": filename,
        "document_type": document_type,
        "file_validation": file_validation,
        "ocr": {
            "success": ocr_result.get("success"),
            "ocr_used": ocr_result.get("ocr_used"),
            "processing_time_ms": ocr_result.get(
                "processing_time_ms"
            ),
        },
        "extraction": extraction_result,
        "financial_validation": financial_validation,
        "issues": financial_validation.get(
            "issues",
            [],
        ),
    }

    # --------------------------------------------------------
    # 8. Persist result
    # --------------------------------------------------------

    _save_result(
        filename=filename,
        document_type=document_type,
        processing_status=processing_status,
        result=result,
    )

    return result


def _save_result(
    filename: str,
    document_type: str,
    processing_status: str,
    result: dict[str, Any],
) -> None:
    """
    Store processing result in the database.

    Database failures are intentionally handled here so that
    they do not expose internal stack traces to API users.
    """

    try:
        DocumentRepository.save(
            document_name=filename,
            document_type=document_type,
            processing_status=processing_status,
            result=result,
        )
    except Exception:
        # The processing result is still returned to the caller.
        # Database failures should be logged by the application
        # logging layer later.
        pass