import json
import sqlite3
from pathlib import Path
from typing import Any


# ============================================================
# DATABASE LOCATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DATABASE_PATH = DATA_DIR / "documents.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection() -> sqlite3.Connection:
    """
    Create a connection to the SQLite database.
    """

    connection = sqlite3.connect(
        DATABASE_PATH,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def initialize_database() -> None:
    """
    Create the documents table if it does not already exist.
    """

    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                document_name TEXT NOT NULL UNIQUE,

                document_type TEXT NOT NULL,

                processing_status TEXT NOT NULL,

                result_json TEXT NOT NULL,

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL
            )
            """
        )

        connection.commit()

    finally:
        connection.close()


# ============================================================
# SAVE DOCUMENT
# ============================================================

def save_document(
    document_name: str,
    document_type: str,
    processing_status: str,
    result: dict[str, Any],
    created_at: str,
) -> dict[str, Any]:
    """
    Insert or update a processed document.
    """

    connection = get_connection()

    try:

        result_json = json.dumps(
            result,
            ensure_ascii=False,
        )

        connection.execute(
            """
            INSERT INTO documents (
                document_name,
                document_type,
                processing_status,
                result_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)

            ON CONFLICT(document_name)
            DO UPDATE SET
                document_type = excluded.document_type,
                processing_status = excluded.processing_status,
                result_json = excluded.result_json,
                updated_at = excluded.updated_at
            """,
            (
                document_name,
                document_type,
                processing_status,
                result_json,
                created_at,
                created_at,
            ),
        )

        connection.commit()

        return {
            "success": True,
            "document_name": document_name,
        }

    finally:
        connection.close()


# ============================================================
# GET ONE DOCUMENT
# ============================================================

def get_document(
    document_name: str,
) -> dict[str, Any] | None:
    """
    Retrieve one document by its filename.
    """

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT
                id,
                document_name,
                document_type,
                processing_status,
                result_json,
                created_at,
                updated_at
            FROM documents
            WHERE document_name = ?
            """,
            (document_name,),
        ).fetchone()

        if row is None:
            return None

        result = json.loads(
            row["result_json"]
        )

        return {
            "id": row["id"],
            "document_name": row["document_name"],
            "document_type": row["document_type"],
            "processing_status": row["processing_status"],
            "result": result,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    finally:
        connection.close()


# ============================================================
# GET ALL DOCUMENTS
# ============================================================

def get_all_documents() -> list[dict[str, Any]]:
    """
    Retrieve all processed documents.

    Newest documents are returned first.
    """

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                id,
                document_name,
                document_type,
                processing_status,
                created_at,
                updated_at
            FROM documents
            ORDER BY created_at DESC
            """
        ).fetchall()

        documents = []

        for row in rows:

            documents.append(
                {
                    "id": row["id"],
                    "document_name": row["document_name"],
                    "document_type": row["document_type"],
                    "processing_status": row["processing_status"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )

        return documents

    finally:
        connection.close()


# ============================================================
# DELETE DOCUMENT
# ============================================================

def delete_document(
    document_name: str,
) -> bool:
    """
    Delete a document by filename.

    This is mainly useful during development/testing.
    """

    connection = get_connection()

    try:

        cursor = connection.execute(
            """
            DELETE FROM documents
            WHERE document_name = ?
            """,
            (document_name,),
        )

        connection.commit()

        return cursor.rowcount > 0

    finally:
        connection.close()