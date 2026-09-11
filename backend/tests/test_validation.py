from backend.app.services.financial_validation_service import (
    validate_financial_document,
)


# ============================================================
# BALANCE SHEET TESTS
# ============================================================

def test_balance_sheet_passes_when_assets_equal_liabilities():

    extracted_data = {
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
                "line_item": "Total Assets",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 1000.00,
                    },
                    {
                        "period": "March 31, 2025",
                        "value": 900.00,
                    },
                ],
            },
            {
                "line_item": "Total Capital and Liabilities",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 1000.00,
                    },
                    {
                        "period": "March 31, 2025",
                        "value": 900.00,
                    },
                ],
            },
        ],
    }

    result = validate_financial_document(
        document_type="balance_sheet",
        extracted_data=extracted_data,
    )

    assert result["document_type"] == "balance_sheet"
    assert result["overall_status"] == "PASS"

    # Only the main total-vs-total check is applicable because
    # component line items are not present in this synthetic case.
    assert len(result["checks"]) == 6

# The first two checks are the total-vs-total
# reconciliation for the two reporting periods.
    assert result["checks"][0]["status"] == "PASS"
    assert result["checks"][0]["variance"] == 0.0

    assert result["checks"][1]["status"] == "PASS"
    assert result["checks"][1]["variance"] == 0.0

# The remaining component checks are NOT_APPLICABLE
# because this synthetic test does not provide component values.
    for check in result["checks"][2:]:
        assert check["status"] == "NOT_APPLICABLE"


def test_balance_sheet_fails_when_assets_do_not_match():

    extracted_data = {
        "fields": {
            "reporting_periods": {
                "value": [
                    "March 31, 2026",
                ]
            }
        },
        "statement_items": [
            {
                "line_item": "Total Assets",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 1000.00,
                    },
                ],
            },
            {
                "line_item": "Total Capital and Liabilities",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 950.00,
                    },
                ],
            },
        ],
    }

    result = validate_financial_document(
        document_type="balance_sheet",
        extracted_data=extracted_data,
    )

    assert result["overall_status"] == "FAIL"
    assert len(result["checks"]) == 3

    assert result["checks"][0]["status"] == "FAIL"
    assert result["checks"][0]["variance"] == -50.0

    # Component checks are not applicable because component
    # line items were not supplied.
    assert result["checks"][1]["status"] == "NOT_APPLICABLE"
    assert result["checks"][2]["status"] == "NOT_APPLICABLE"


def test_balance_sheet_is_not_applicable_when_required_value_missing():

    extracted_data = {
        "fields": {
            "reporting_periods": {
                "value": [
                    "March 31, 2026",
                ]
            }
        },
        "statement_items": [
            {
                "line_item": "Total Assets",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 1000.00,
                    },
                ],
            },
        ],
    }

    result = validate_financial_document(
        document_type="balance_sheet",
        extracted_data=extracted_data,
    )

    assert result["overall_status"] == "NOT_APPLICABLE"
    assert len(result["checks"]) == 3

    assert all(
        check["status"] == "NOT_APPLICABLE"
        for check in result["checks"]
    )


# ============================================================
# PROFIT & LOSS TESTS
# ============================================================

def test_profit_and_loss_passes_all_main_checks():

    extracted_data = {
        "fields": {
            "reporting_periods": {
                "value": [
                    "March 31, 2026",
                ]
            }
        },
        "statement_items": [
            {
                "line_item": "Interest Earned",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 600.00,
                    },
                ],
            },
            {
                "line_item": "Other Income",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 100.00,
                    },
                ],
            },
            {
                "line_item": "Total Income",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 700.00,
                    },
                ],
            },
            {
                "line_item": "Interest Expended",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 300.00,
                    },
                ],
            },
            {
                "line_item": "Operating Expenses",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 150.00,
                    },
                ],
            },
            {
                "line_item": "Provisions and Contingencies",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 50.00,
                    },
                ],
            },
            {
                "line_item": "Total Expenditure",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 500.00,
                    },
                ],
            },
            {
                "line_item": (
                    "Consolidated Net Profit for the year "
                    "before Minority Interest"
                ),
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 200.00,
                    },
                ],
            },
            {
                "line_item": "Less / Minority Interest",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 20.00,
                    },
                ],
            },
            {
                "line_item": (
                    "Consolidated Net Profit for the year "
                    "attributable to the Group"
                ),
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 180.00,
                    },
                ],
            },
            {
                "line_item": (
                    "Brought forward consolidated profit "
                    "attributable to the Group"
                ),
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 50.00,
                    },
                ],
            },
            {
                "line_item": "Total Profit",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 230.00,
                    },
                ],
            },
        ],
    }

    result = validate_financial_document(
        document_type="profit_and_loss",
        extracted_data=extracted_data,
    )

    assert result["document_type"] == "profit_and_loss"
    assert result["overall_status"] == "PASS"
    assert len(result["checks"]) == 5

    for check in result["checks"]:
        assert check["status"] == "PASS"


def test_profit_and_loss_fails_when_total_income_is_wrong():

    extracted_data = {
        "fields": {
            "reporting_periods": {
                "value": [
                    "March 31, 2026",
                ]
            }
        },
        "statement_items": [
            {
                "line_item": "Interest Earned",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 600.00,
                    },
                ],
            },
            {
                "line_item": "Other Income",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 100.00,
                    },
                ],
            },
            {
                "line_item": "Total Income",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 650.00,
                    },
                ],
            },
        ],
    }

    result = validate_financial_document(
        document_type="profit_and_loss",
        extracted_data=extracted_data,
    )

    assert result["overall_status"] == "FAIL"

    first_check = result["checks"][0]

    assert first_check["status"] == "FAIL"
    assert first_check["calculated"] == 700.00
    assert first_check["reported"] == 650.00
    assert first_check["variance"] == 50.00


def test_profit_and_loss_does_not_confuse_profit_rows():

    extracted_data = {
        "fields": {
            "reporting_periods": {
                "value": [
                    "March 31, 2026",
                ]
            }
        },
        "statement_items": [
            {
                "line_item": (
                    "Consolidated Net Profit for the year "
                    "before Minority Interest"
                ),
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 200.00,
                    },
                ],
            },
            {
                "line_item": (
                    "Consolidated Net Profit for the year "
                    "attributable to the Group"
                ),
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 180.00,
                    },
                ],
            },
        ],
    }

    result = validate_financial_document(
        document_type="profit_and_loss",
        extracted_data=extracted_data,
    )

    assert result["overall_status"] in {
        "NOT_APPLICABLE",
        "FAIL",
    }


# ============================================================
# CASH FLOW TESTS
# ============================================================

def test_cash_flow_passes():

    extracted_data = {
        "fields": {
            "reporting_periods": {
                "value": [
                    "March 31, 2026",
                ]
            }
        },
        "statement_items": [
            {
                "line_item": "Net Cash from Operating Activities",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 500.00,
                    },
                ],
            },
            {
                "line_item": "Net Cash from Investing Activities",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": -100.00,
                    },
                ],
            },
            {
                "line_item": "Net Cash from Financing Activities",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": -50.00,
                    },
                ],
            },
            {
                "line_item": "Net Change in Cash",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 350.00,
                    },
                ],
            },
            {
                "line_item": "Opening Cash",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 1000.00,
                    },
                ],
            },
            {
                "line_item": "Closing Cash",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 1350.00,
                    },
                ],
            },
        ],
    }

    result = validate_financial_document(
        document_type="cash_flow_statement",
        extracted_data=extracted_data,
    )

    assert result["document_type"] == "cash_flow_statement"
    assert result["overall_status"] == "PASS"
    assert len(result["checks"]) == 2

    for check in result["checks"]:
        assert check["status"] == "PASS"


def test_cash_flow_fails_when_net_change_is_wrong():

    extracted_data = {
        "fields": {
            "reporting_periods": {
                "value": [
                    "March 31, 2026",
                ]
            }
        },
        "statement_items": [
            {
                "line_item": "Net Cash from Operating Activities",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 500.00,
                    },
                ],
            },
            {
                "line_item": "Net Cash from Investing Activities",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": -100.00,
                    },
                ],
            },
            {
                "line_item": "Net Cash from Financing Activities",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": -50.00,
                    },
                ],
            },
            {
                "line_item": "Net Change in Cash",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 400.00,
                    },
                ],
            },
        ],
    }

    result = validate_financial_document(
        document_type="cash_flow_statement",
        extracted_data=extracted_data,
    )

    assert result["overall_status"] == "FAIL"

    first_check = result["checks"][0]

    assert first_check["status"] == "FAIL"
    assert first_check["calculated"] == 350.00
    assert first_check["reported"] == 400.00
    assert first_check["variance"] == -50.00


def test_cash_flow_handles_negative_parentheses():

    extracted_data = {
        "fields": {
            "reporting_periods": {
                "value": [
                    "March 31, 2026",
                ]
            }
        },
        "statement_items": [
            {
                "line_item": "Net Cash from Operating Activities",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": "500.00",
                    },
                ],
            },
            {
                "line_item": "Net Cash from Investing Activities",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": "(100.00)",
                    },
                ],
            },
            {
                "line_item": "Net Cash from Financing Activities",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": "(50.00)",
                    },
                ],
            },
            {
                "line_item": "Net Change in Cash",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": "350.00",
                    },
                ],
            },
        ],
    }

    result = validate_financial_document(
        document_type="cash_flow_statement",
        extracted_data=extracted_data,
    )

    assert result["overall_status"] == "PASS"
    assert result["checks"][0]["status"] == "PASS"


# ============================================================
# GENERIC / EDGE CASE TESTS
# ============================================================

def test_unsupported_document_type():

    result = validate_financial_document(
        document_type="unknown_type",
        extracted_data={},
    )

    assert result["document_type"] == "unknown_type"
    assert result["overall_status"] == "NOT_APPLICABLE"
    assert len(result["checks"]) == 0
    assert len(result["issues"]) == 1


def test_empty_extracted_data_is_not_applicable():

    result = validate_financial_document(
        document_type="balance_sheet",
        extracted_data={},
    )

    assert result["document_type"] == "balance_sheet"
    assert result["overall_status"] == "NOT_APPLICABLE"
    assert result["checks"] == []


def test_missing_reporting_periods_uses_statement_item_periods():

    extracted_data = {
        "statement_items": [
            {
                "line_item": "Total Assets",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 1000.00,
                    },
                ],
            },
            {
                "line_item": "Total Capital and Liabilities",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 1000.00,
                    },
                ],
            },
        ],
    }

    result = validate_financial_document(
        document_type="balance_sheet",
        extracted_data=extracted_data,
    )

    assert result["overall_status"] == "PASS"
    assert len(result["checks"]) == 3
    assert result["checks"][0]["period"] == "March 31, 2026"
    assert result["checks"][0]["status"] == "PASS"


def test_small_rounding_difference_passes():

    extracted_data = {
        "fields": {
            "reporting_periods": {
                "value": [
                    "March 31, 2026",
                ]
            }
        },
        "statement_items": [
            {
                "line_item": "Total Assets",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 1000.00,
                    },
                ],
            },
            {
                "line_item": "Total Capital and Liabilities",
                "values": [
                    {
                        "period": "March 31, 2026",
                        "value": 1000.05,
                    },
                ],
            },
        ],
    }

    result = validate_financial_document(
        document_type="balance_sheet",
        extracted_data=extracted_data,
    )

    assert result["overall_status"] == "PASS"
    assert result["checks"][0]["status"] == "PASS"
