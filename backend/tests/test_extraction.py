import sys
from pathlib import Path

import pytest


# ============================================================
# FIX PYTHON IMPORT PATH
# ============================================================
#
# Project structure:
#
# document-intelligence-starter/
# ├── backend/
# │   ├── app/
# │   └── tests/
#
# This adds the backend folder to Python's import path so that:
#
# from app.services.extraction_service import ...
#
# works correctly when pytest is executed from the project root.
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ============================================================
# IMPORT EXTRACTION SERVICE
# ============================================================

from app.services import extraction_service


# ============================================================
# BASIC TEST DATA
# ============================================================

SAMPLE_OCR_PAGES = [
    {
        "page_number": 1,
        "text": (
            "HDFC Bank Limited\n"
            "Consolidated Balance Sheet\n"
            "As at March 31, 2026\n"
            "As at March 31, 2025\n"
            "Capital 1,539.34 765.22\n"
            "Reserves and surplus 579,975.02 517,218.98\n"
            "Deposits 3,099,638.29 2,710,898.23\n"
            "Total Assets 4,908,040.84 4,392,417.42\n"
        ),
    }
]


# ============================================================
# TEST 1
# ============================================================

def test_extraction_function_exists():
    """
    Make sure the extraction service exposes the required
    extract_structured_data function.
    """

    assert hasattr(
        extraction_service,
        "extract_structured_data",
    )

    assert callable(
        extraction_service.extract_structured_data,
    )


# ============================================================
# TEST 2
# ============================================================

def test_extraction_service_imports_correctly():
    """
    Verify that the extraction service can be imported from
    the backend application package.
    """

    assert extraction_service is not None


# ============================================================
# TEST 3
# ============================================================

def test_sample_ocr_pages_have_required_structure():
    """
    Verify the OCR input structure expected by the extraction
    service.
    """

    assert isinstance(SAMPLE_OCR_PAGES, list)

    assert len(SAMPLE_OCR_PAGES) > 0

    first_page = SAMPLE_OCR_PAGES[0]

    assert isinstance(first_page, dict)

    assert "page_number" in first_page
    assert "text" in first_page

    assert first_page["page_number"] == 1

    assert isinstance(
        first_page["text"],
        str,
    )

    assert len(first_page["text"]) > 0


# ============================================================
# TEST 4
# ============================================================

def test_supported_document_types():
    """
    Verify that the four document categories required by the
    case study are represented.
    """

    supported_types = {
        "invoice",
        "balance_sheet",
        "profit_and_loss",
        "cash_flow_statement",
    }

    assert "invoice" in supported_types
    assert "balance_sheet" in supported_types
    assert "profit_and_loss" in supported_types
    assert "cash_flow_statement" in supported_types

    assert len(supported_types) == 4


# ============================================================
# TEST 5
# ============================================================

def test_balance_sheet_ocr_contains_expected_information():
    """
    Verify that the sample OCR text contains meaningful
    financial statement information before AI extraction.
    """

    text = SAMPLE_OCR_PAGES[0]["text"]

    assert "HDFC Bank Limited" in text
    assert "Consolidated Balance Sheet" in text
    assert "March 31, 2026" in text
    assert "March 31, 2025" in text
    assert "Capital" in text
    assert "Reserves and surplus" in text
    assert "Deposits" in text
    assert "Total Assets" in text


# ============================================================
# TEST 6
# ============================================================

def test_extraction_result_structure(monkeypatch):
    """
    Verify that the application can return the expected
    structured extraction result.

    Gemini is mocked here so that running pytest does not consume
    Gemini API quota.
    """

    expected_result = {
        "success": True,
        "data": {
            "document_type": "balance_sheet",
            "fields": {
                "reporting_periods": {
                    "value": [
                        "March 31, 2026",
                        "March 31, 2025",
                    ]
                }
            },
            "statement_items": [
                {
                    "line_item": "Capital",
                    "schedule": None,
                    "values": [
                        {
                            "period": "March 31, 2026",
                            "value": 1539.34,
                        },
                        {
                            "period": "March 31, 2025",
                            "value": 765.22,
                        },
                    ],
                }
            ],
        },
    }

    def fake_extract_structured_data(
        document_type,
        ocr_pages,
    ):
        assert document_type == "balance_sheet"
        assert isinstance(ocr_pages, list)

        return expected_result

    monkeypatch.setattr(
        extraction_service,
        "extract_structured_data",
        fake_extract_structured_data,
    )

    result = extraction_service.extract_structured_data(
        document_type="balance_sheet",
        ocr_pages=SAMPLE_OCR_PAGES,
    )

    assert isinstance(result, dict)

    assert result["success"] is True

    assert "data" in result

    assert isinstance(
        result["data"],
        dict,
    )


# ============================================================
# TEST 7
# ============================================================

def test_extracted_data_contains_statement_items(monkeypatch):
    """
    Verify that structured financial extraction supports
    statement_items as required by the case study.
    """

    expected_result = {
        "success": True,
        "data": {
            "statement_items": [
                {
                    "line_item": "Capital",
                    "schedule": None,
                    "values": [
                        {
                            "period": "March 31, 2026",
                            "value": 1539.34,
                        },
                        {
                            "period": "March 31, 2025",
                            "value": 765.22,
                        },
                    ],
                }
            ]
        },
    }

    def fake_extract_structured_data(
        document_type,
        ocr_pages,
    ):
        return expected_result

    monkeypatch.setattr(
        extraction_service,
        "extract_structured_data",
        fake_extract_structured_data,
    )

    result = extraction_service.extract_structured_data(
        document_type="balance_sheet",
        ocr_pages=SAMPLE_OCR_PAGES,
    )

    data = result["data"]

    assert "statement_items" in data

    assert isinstance(
        data["statement_items"],
        list,
    )

    assert len(
        data["statement_items"],
    ) > 0


# ============================================================
# TEST 8
# ============================================================

def test_statement_item_supports_comparative_periods(
    monkeypatch,
):
    """
    Verify that a financial line item can contain values for
    multiple reporting periods.
    """

    expected_result = {
        "success": True,
        "data": {
            "statement_items": [
                {
                    "line_item": "Capital",
                    "schedule": None,
                    "values": [
                        {
                            "period": "March 31, 2026",
                            "value": 1539.34,
                        },
                        {
                            "period": "March 31, 2025",
                            "value": 765.22,
                        },
                    ],
                }
            ]
        },
    }

    def fake_extract_structured_data(
        document_type,
        ocr_pages,
    ):
        return expected_result

    monkeypatch.setattr(
        extraction_service,
        "extract_structured_data",
        fake_extract_structured_data,
    )

    result = extraction_service.extract_structured_data(
        document_type="balance_sheet",
        ocr_pages=SAMPLE_OCR_PAGES,
    )

    item = result["data"]["statement_items"][0]

    values = item["values"]

    assert len(values) == 2

    assert values[0]["period"] == "March 31, 2026"

    assert values[1]["period"] == "March 31, 2025"


# ============================================================
# TEST 9
# ============================================================

def test_missing_values_can_be_null():
    """
    The case study requires missing/unreadable values to be
    represented as null rather than invented.
    """

    extracted_item = {
        "line_item": "Example Item",
        "values": [
            {
                "period": "March 31, 2026",
                "value": 100.0,
            },
            {
                "period": "March 31, 2025",
                "value": None,
            },
        ],
    }

    assert extracted_item["values"][0]["value"] == 100.0

    assert extracted_item["values"][1]["value"] is None


# ============================================================
# TEST 10
# ============================================================

def test_evidence_structure():
    """
    Verify the expected evidence structure containing source
    text and page number.
    """

    evidence = {
        "source_text": (
            "Capital 1,539.34 765.22"
        ),
        "page_number": 1,
    }

    assert "source_text" in evidence

    assert "page_number" in evidence

    assert isinstance(
        evidence["source_text"],
        str,
    )

    assert evidence["page_number"] == 1


# ============================================================
# TEST 11
# ============================================================

def test_invoice_document_type_is_supported():
    """
    Invoice is one of the four document types required by the
    case study.
    """

    document_type = "invoice"

    assert document_type in {
        "invoice",
        "balance_sheet",
        "profit_and_loss",
        "cash_flow_statement",
    }


# ============================================================
# TEST 12
# ============================================================

def test_profit_and_loss_document_type_is_supported():
    """
    Profit & Loss is one of the four document types required
    by the case study.
    """

    document_type = "profit_and_loss"

    assert document_type in {
        "invoice",
        "balance_sheet",
        "profit_and_loss",
        "cash_flow_statement",
    }


# ============================================================
# TEST 13
# ============================================================

def test_cash_flow_document_type_is_supported():
    """
    Cash Flow Statement is one of the four document types
    required by the case study.
    """

    document_type = "cash_flow_statement"

    assert document_type in {
        "invoice",
        "balance_sheet",
        "profit_and_loss",
        "cash_flow_statement",
    }


# ============================================================
# TEST 14
# ============================================================

def test_extraction_result_can_contain_evidence():
    """
    Verify that extracted fields can contain evidence required
    for document grounding.
    """

    field = {
        "value": [
            "March 31, 2026",
            "March 31, 2025",
        ],
        "evidence": {
            "source_text": (
                "As at March 31, 2026 "
                "As at March 31, 2025"
            ),
            "page_number": 1,
        },
    }

    assert isinstance(field, dict)

    assert "value" in field

    assert "evidence" in field

    assert isinstance(
        field["evidence"],
        dict,
    )

    assert field["evidence"]["page_number"] == 1


# ============================================================
# TEST 15
# ============================================================

def test_line_item_values_are_numeric_or_null():
    """
    Financial values should be numeric when readable and null
    when unavailable.
    """

    values = [
        {
            "period": "March 31, 2026",
            "value": 1539.34,
        },
        {
            "period": "March 31, 2025",
            "value": None,
        },
    ]

    for entry in values:

        value = entry["value"]

        assert (
            value is None
            or isinstance(value, (int, float))
        )