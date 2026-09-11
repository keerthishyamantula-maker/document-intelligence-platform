import io
import logging
import time
from pathlib import Path

import fitz
import pytesseract
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# On Windows, use the standard installation path when it exists.
# On Linux/Docker (Render), leave tesseract_cmd unset so pytesseract
# uses the `tesseract` executable installed in the Docker image PATH.
_WINDOWS_TESSERACT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
if _WINDOWS_TESSERACT.exists():
    pytesseract.pytesseract.tesseract_cmd = str(_WINDOWS_TESSERACT)

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _prepare_image(image: Image.Image) -> Image.Image:
    """Create a clean grayscale image for OCR without changing document content."""
    image = image.convert("L")
    image = ImageOps.autocontrast(image)
    return image


def _ocr_image(image: Image.Image, psm: int) -> str:
    """Run Tesseract with a specified page segmentation mode."""
    try:
        text = pytesseract.image_to_string(
            _prepare_image(image),
            config=f"--psm {psm}",
        )
        return text.strip()
    except pytesseract.TesseractNotFoundError:
        raise
    except Exception:
        logger.exception("Tesseract OCR failed.")
        return ""


def _extract_header_text(image: Image.Image) -> str:
    """OCR the top/header portion where statement periods normally appear."""
    width, height = image.size
    header_height = int(height * 0.35)
    header_image = image.crop((0, 0, width, header_height))

    results = []
    for psm in (6, 11, 12):
        text = _ocr_image(header_image, psm=psm)
        if text:
            results.append(text)

    return "\n\n".join(results)


def extract_text_from_document(filename: str, content: bytes) -> dict:
    start_time = time.perf_counter()
    extension = Path(filename).suffix.lower()
    pages = []

    try:
        if extension == ".pdf":
            pdf = fitz.open(stream=content, filetype="pdf")
            try:
                for page_number, page in enumerate(pdf, start=1):
                    pixmap = page.get_pixmap(
                        matrix=fitz.Matrix(2, 2),
                        alpha=False,
                    )
                    image_bytes = pixmap.tobytes("png")
                    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

                    # Use the primary layout mode for the main text. Header OCR
                    # is retained separately so reporting-period extraction can
                    # prioritize the statement header.
                    text = _ocr_image(image, psm=6)

                    page_result = {
                        "page_number": page_number,
                        "text": text,
                    }

                    if page_number == 1:
                        page_result["header_text"] = _extract_header_text(image)

                    pages.append(page_result)
            finally:
                pdf.close()

        elif extension in SUPPORTED_IMAGE_EXTENSIONS:
            image = Image.open(io.BytesIO(content)).convert("RGB")
            pages.append({
                "page_number": 1,
                "text": _ocr_image(image, psm=6),
                "header_text": _extract_header_text(image),
            })

        else:
            return {
                "success": False,
                "ocr_used": False,
                "pages": [],
                "text": "",
                "processing_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                "error_code": "UNSUPPORTED_DOCUMENT_FORMAT",
                "message": "Unsupported document format.",
            }

        processing_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        combined_text = "\n\n".join(page.get("text", "") for page in pages)
        combined_header_text = "\n\n".join(
            page.get("header_text", "")
            for page in pages
            if page.get("header_text")
        )

        return {
            "success": True,
            "ocr_used": True,
            "pages": pages,
            "text": combined_text,
            "header_text": combined_header_text,
            "processing_time_ms": processing_time_ms,
        }

    except pytesseract.TesseractNotFoundError:
        logger.exception("Tesseract executable was not found.")
        return {
            "success": False,
            "ocr_used": True,
            "pages": [],
            "text": "",
            "processing_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
            "error_code": "OCR_ENGINE_NOT_FOUND",
            "message": "Tesseract OCR is not installed or could not be found.",
        }

    except Exception:
        logger.exception("Unexpected OCR failure.")
        return {
            "success": False,
            "ocr_used": True,
            "pages": [],
            "text": "",
            "processing_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
            "error_code": "OCR_FAILED",
            "message": "Text extraction failed.",
        }
