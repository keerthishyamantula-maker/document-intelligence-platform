from io import BytesIO

from PIL import Image
from pypdf import PdfReader


ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


def validate_document(filename: str, content: bytes) -> dict:
    filename_lower = filename.lower()

    extension = "." + filename_lower.split(".")[-1]

    if extension not in ALLOWED_EXTENSIONS:
        return {
            "valid": False,
            "message": "Only PDF, JPG, JPEG, and PNG files are allowed."
        }

    if not content:
        return {
            "valid": False,
            "message": "The uploaded file is empty."
        }

    try:
        if extension == ".pdf":
            reader = PdfReader(BytesIO(content))

            return {
                "valid": True,
                "file_type": "PDF",
                "pages": len(reader.pages)
            }

        else:
            image = Image.open(BytesIO(content))
            image.verify()

            return {
                "valid": True,
                "file_type": extension.replace(".", "").upper()
            }

    except Exception:
        return {
            "valid": False,
            "message": "The file is corrupted or is not a valid document."
        }