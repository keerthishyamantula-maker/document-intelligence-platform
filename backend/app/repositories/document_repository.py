from datetime import datetime, timezone
from typing import Any

from backend.app.core.database import (
    get_all_documents,
    get_document,
    save_document,
)


class DocumentRepository:
    """
    Repository layer responsible for storing and retrieving
    processed document results.
    """

    # ========================================================
    # SAVE DOCUMENT
    # ========================================================

    @staticmethod
    def save(
        document_name: str,
        document_type: str,
        processing_status: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Save a processed document result.

        If the same document name already exists, the database
        record is updated instead of creating a duplicate.
        """

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        return save_document(
            document_name=document_name,
            document_type=document_type,
            processing_status=processing_status,
            result=result,
            created_at=timestamp,
        )

    # ========================================================
    # GET ONE DOCUMENT
    # ========================================================

    @staticmethod
    def get_by_name(
        document_name: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve a document using its filename.
        """

        return get_document(
            document_name=document_name
        )

    # ========================================================
    # GET ALL DOCUMENTS
    # ========================================================

    @staticmethod
    def get_all() -> list[dict[str, Any]]:
        """
        Retrieve all processed documents.
        """

        return get_all_documents()