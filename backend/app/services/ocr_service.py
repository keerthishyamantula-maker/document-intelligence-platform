import io
import logging
import time
from pathlib import Path

import fitz
import pytesseract
from PIL import Image


logger = logging.getLogger(__name__)

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
}


def _ocr_image(
    image: Image.Image,
    psm: int,
) -> str:
    """
    Run Tesseract with a specified page segmentation mode.
    """

    try:
        text = pytesseract.image_to_string(
            image,
            config=f"--psm {psm}",
        )

        return text.strip()

    except Exception:

        logger.exception(
            "Tesseract OCR failed."
        )

        return ""


def _extract_header_text(
    image: Image.Image,
) -> str:
    """
    Extract the top/header portion of a financial document.

    Financial statement reporting periods normally appear
    near the top of page 1.

    Multiple OCR modes are used because scanned financial
    statements often have column-based headers.
    """

    width, height = image.size

    # The top ~35% of the first page generally contains:
    # company name
    # statement title
    # reporting period
    # currency / units
    #
    # We deliberately do not OCR the entire page for this
    # operation because dates later in the document can be
    # unrelated to the reporting period.
    header_height = int(height * 0.35)

    header_image = image.crop(
        (
            0,
            0,
            width,
            header_height,
        )
    )

    results = []

    # PSM 6: uniform block
    text_6 = _ocr_image(
        header_image,
        psm=6,
    )

    if text_6:
        results.append(text_6)

    # PSM 11: sparse text
    text_11 = _ocr_image(
        header_image,
        psm=11,
    )

    if text_11:
        results.append(text_11)

    # PSM 12: sparse text with OSD
    text_12 = _ocr_image(
        header_image,
        psm=12,
    )

    if text_12:
        results.append(text_12)

    return "\n\n".join(results)


def extract_text_from_document(
    filename: str,
    content: bytes,
) -> dict:

    start_time = time.perf_counter()

    extension = Path(
        filename
    ).suffix.lower()

    pages = []

    try:

        # =================================================
        # PDF
        # =================================================

        if extension == ".pdf":

            pdf = fitz.open(
                stream=content,
                filetype="pdf",
            )

            try:

                for page_number, page in enumerate(
                    pdf,
                    start=1,
                ):

                    # Render at 2x resolution.
                    pixmap = page.get_pixmap(
                        matrix=fitz.Matrix(
                            2,
                            2,
                        ),
                        alpha=False,
                    )

                    image_bytes = pixmap.tobytes(
                        "png"
                    )

                    image = Image.open(
                        io.BytesIO(
                            image_bytes
                        )
                    )

                    # Normal full-page OCR.
                    text = _ocr_image(
                        image,
                        psm=6,
                    )

                    page_result = {
                        "page_number": page_number,
                        "text": text,
                    }

                    # -------------------------------------------------
                    # Dedicated header OCR
                    # -------------------------------------------------

                    if page_number == 1:

                        header_text = (
                            _extract_header_text(
                                image
                            )
                        )

                        page_result[
                            "header_text"
                        ] = header_text

                    pages.append(
                        page_result
                    )

            finally:

                pdf.close()

        # =================================================
        # JPG / JPEG / PNG
        # =================================================

        elif extension in SUPPORTED_IMAGE_EXTENSIONS:

            image = Image.open(
                io.BytesIO(content)
            )

            text = _ocr_image(
                image,
                psm=6,
            )

            pages.append(
                {
                    "page_number": 1,
                    "text": text,
                    "header_text": _extract_header_text(
                        image
                    ),
                }
            )

        else:

            return {
                "success": False,
                "ocr_used": False,
                "pages": [],
                "text": "",
                "processing_time_ms": round(
                    (
                        time.perf_counter()
                        - start_time
                    )
                    * 1000,
                    2,
                ),
                "error_code": (
                    "UNSUPPORTED_DOCUMENT_FORMAT"
                ),
                "message": (
                    "Unsupported document format."
                ),
            }

        processing_time_ms = round(
            (
                time.perf_counter()
                - start_time
            )
            * 1000,
            2,
        )

        combined_text = "\n\n".join(
            page.get(
                "text",
                "",
            )
            for page in pages
        )

        combined_header_text = "\n\n".join(
            page.get(
                "header_text",
                "",
            )
            for page in pages
            if page.get(
                "header_text"
            )
        )

        return {
            "success": True,
            "ocr_used": True,
            "pages": pages,
            "text": combined_text,
            "header_text": combined_header_text,
            "processing_time_ms": (
                processing_time_ms
            ),
        }

    except pytesseract.TesseractNotFoundError:

        logger.exception(
            "Tesseract executable was not found."
        )

        return {
            "success": False,
            "ocr_used": True,
            "pages": [],
            "text": "",
            "processing_time_ms": round(
                (
                    time.perf_counter()
                    - start_time
                )
                * 1000,
                2,
            ),
            "error_code": (
                "OCR_ENGINE_NOT_FOUND"
            ),
            "message": (
                "Tesseract OCR is not installed "
                "or could not be found."
            ),
        }

    except Exception:

        logger.exception(
            "Unexpected OCR failure."
        )

        return {
            "success": False,
            "ocr_used": True,
            "pages": [],
            "text": "",
            "processing_time_ms": round(
                (
                    time.perf_counter()
                    - start_time
                )
                * 1000,
                2,
            ),
            "error_code": "OCR_FAILED",
            "message": (
                "Text extraction failed."
            ),
        }