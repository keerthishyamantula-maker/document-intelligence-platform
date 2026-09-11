from io import BytesIO
from pathlib import Path

from PIL import Image
from pypdf import PdfReader


ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_PAGES = 3


def validate_document(filename: str, content: bytes) -> dict:
    """
    Validate an uploaded document before OCR/extraction.

    Requirements from the case study:
    - PDF / JPG / PNG only
    - File must not be empty
    - File must be readable
    - PDF must contain no more than 3 pages
    """

    extension = Path(filename or "").suffix.lower()

    # 1. Check file type
    if extension not in ALLOWED_EXTENSIONS:
        return {
            "file_type": None,
            "is_supported": False,
            "is_readable": False,
            "page_count": None,
            "status": "FAILED",
            "error_code": "UNSUPPORTED_FILE_TYPE",
            "message": "Only PDF / JPG / PNG documents are supported."
        }

    # 2. Check empty file
    if not content:
        return {
            "file_type": extension,
            "is_supported": True,
            "is_readable": False,
            "page_count": None,
            "status": "FAILED",
            "error_code": "EMPTY_FILE",
            "message": "The uploaded file is empty."
        }

    try:
        # 3. Validate PDF
        if extension == ".pdf":
            reader = PdfReader(BytesIO(content))

            page_count = len(reader.pages)

            # Corrupted/invalid PDF
            if page_count == 0:
                return {
                    "file_type": "application/pdf",
                    "is_supported": True,
                    "is_readable": False,
                    "page_count": 0,
                    "status": "FAILED",
                    "error_code": "INVALID_DOCUMENT",
                    "message": "The PDF does not contain any readable pages."
                }

            # Page limit
            if page_count > MAX_PAGES:
                return {
                    "file_type": "application/pdf",
                    "is_supported": True,
                    "is_readable": True,
                    "page_count": page_count,
                    "status": "FAILED",
                    "error_code": "PAGE_LIMIT_EXCEEDED",
                    "message": "Documents must contain no more than 3 pages."
                }

            return {
                "file_type": "application/pdf",
                "is_supported": True,
                "is_readable": True,
                "page_count": page_count,
                "status": "PASS"
            }

        # 4. Validate JPG / JPEG / PNG
        image = Image.open(BytesIO(content))
        image.verify()

        mime_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png"
        }[extension]

        return {
            "file_type": mime_type,
            "is_supported": True,
            "is_readable": True,
            "page_count": 1,
            "status": "PASS"
        }

    except Exception:
        return {
            "file_type": (
                "application/pdf"
                if extension == ".pdf"
                else {
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png"
                }.get(extension)
            ),
            "is_supported": True,
            "is_readable": False,
            "page_count": None,
            "status": "FAILED",
            "error_code": "INVALID_DOCUMENT",
            "message": "The file is corrupted or cannot be read."
        }
        