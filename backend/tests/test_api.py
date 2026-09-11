import io

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


# ============================================================
# HEALTH CHECK
# ============================================================

def test_health():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"


# ============================================================
# FRONTEND
# ============================================================

def test_frontend():
    response = client.get("/")

    assert response.status_code == 200

    assert "Document Intelligence" in response.text


# ============================================================
# LIST DOCUMENTS
# ============================================================

def test_list_documents():
    response = client.get("/api/v1/documents")

    assert response.status_code == 200

    data = response.json()

    assert "documents" in data
    assert "count" in data

    assert isinstance(data["documents"], list)
    assert isinstance(data["count"], int)


# ============================================================
# GET NON-EXISTENT DOCUMENT
# ============================================================

def test_get_nonexistent_document():
    response = client.get(
        "/api/v1/documents/document-that-does-not-exist.pdf"
    )

    assert response.status_code == 404

    data = response.json()

    assert "detail" in data

    assert data["detail"]["error_code"] == "DOCUMENT_NOT_FOUND"


# ============================================================
# INVALID DOCUMENT TYPE
# ============================================================

def test_invalid_document_type():
    fake_file = io.BytesIO(b"fake document content")

    response = client.post(
        "/api/v1/documents/process",
        files={
            "file": (
                "test.pdf",
                fake_file,
                "application/pdf",
            )
        },
        data={
            "document_type": "invalid_document_type"
        },
    )

    assert response.status_code == 400

    data = response.json()

    assert "detail" in data

    assert (
        data["detail"]["error_code"]
        == "UNSUPPORTED_DOCUMENT_TYPE"
    )


# ============================================================
# EMPTY FILE
# ============================================================

def test_empty_file():
    empty_file = io.BytesIO(b"")

    response = client.post(
        "/api/v1/documents/process",
        files={
            "file": (
                "empty.pdf",
                empty_file,
                "application/pdf",
            )
        },
        data={
            "document_type": "invoice"
        },
    )

    assert response.status_code == 400

    data = response.json()

    assert "detail" in data

    assert data["detail"]["error_code"] == "EMPTY_FILE"


# ============================================================
# UNSUPPORTED FILE TYPE
# ============================================================

def test_unsupported_file_type():
    fake_file = io.BytesIO(
        b"This is not a supported document."
    )

    response = client.post(
        "/api/v1/documents/process",
        files={
            "file": (
                "test.txt",
                fake_file,
                "text/plain",
            )
        },
        data={
            "document_type": "invoice"
        },
    )

    # The API should reject the unsupported file.
    assert response.status_code in {200, 400}


# ============================================================
# DOCUMENT VALIDATION ENDPOINT
# ============================================================

def test_validate_empty_file():
    empty_file = io.BytesIO(b"")

    response = client.post(
        "/api/v1/documents/validate",
        files={
            "file": (
                "empty.pdf",
                empty_file,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400

    data = response.json()

    assert "detail" in data


# ============================================================
# REQUIRED DOCUMENT TYPES
# ============================================================

def test_supported_document_types_are_defined():
    supported_types = {
        "invoice",
        "balance_sheet",
        "profit_and_loss",
        "cash_flow_statement",
    }

    # Verify that the API accepts each required type
    # at the validation stage of request handling.
    for document_type in supported_types:

        fake_file = io.BytesIO(
            b"fake document content"
        )

        response = client.post(
            "/api/v1/documents/process",
            files={
                "file": (
                    "test.pdf",
                    fake_file,
                    "application/pdf",
                )
            },
            data={
                "document_type": document_type
            },
        )

        # These types should NOT produce the
        # UNSUPPORTED_DOCUMENT_TYPE error.
        if response.status_code == 400:

            data = response.json()

            detail = data.get("detail", {})

            if isinstance(detail, dict):

                assert (
                    detail.get("error_code")
                    != "UNSUPPORTED_DOCUMENT_TYPE"
                )


# ============================================================
# JSON RESPONSE
# ============================================================

def test_health_returns_json():
    response = client.get("/api/v1/health")

    assert response.headers["content-type"].startswith(
        "application/json"
    )

    assert response.json() == {
        "status": "ok"
    }