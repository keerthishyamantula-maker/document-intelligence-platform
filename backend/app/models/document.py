from dataclasses import dataclass
from typing import Any


@dataclass
class Document:
    """
    Represents a processed document stored by the application.
    """

    id: int | None

    document_name: str

    document_type: str

    processing_status: str

    result: dict[str, Any]

    created_at: str

    updated_at: str