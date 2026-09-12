import json
import json
import logging
import re
from datetime import datetime
from typing import Any

from google import genai

from backend.app.core.config import settings


logger = logging.getLogger(__name__)


# ============================================================
# SUPPORTED DOCUMENT TYPES
# ============================================================

SUPPORTED_DOCUMENT_TYPES = {
    "invoice",
    "balance_sheet",
    "profit_and_loss",
    "cash_flow_statement",
}


# ============================================================
# DOCUMENT TYPE NORMALIZATION
# ============================================================

DOCUMENT_TYPE_ALIASES = {
    "invoice": "invoice",
    "invoices": "invoice",

    "balance_sheet": "balance_sheet",
    "balance sheet": "balance_sheet",
    "balance-sheet": "balance_sheet",

    "profit_and_loss": "profit_and_loss",
    "profit and loss": "profit_and_loss",
    "profit & loss": "profit_and_loss",
    "profit/loss": "profit_and_loss",
    "profit loss": "profit_and_loss",
    "p&l": "profit_and_loss",
    "p & l": "profit_and_loss",

    "cash_flow_statement": "cash_flow_statement",
    "cash flow statement": "cash_flow_statement",
    "cash-flow statement": "cash_flow_statement",
    "cash flow": "cash_flow_statement",
}


def normalize_document_type(document_type: str) -> str:
    """
    Convert different representations of document types into
    the canonical values used by the application.
    """

    if not document_type:
        return ""

    normalized = document_type.strip().lower()

    return DOCUMENT_TYPE_ALIASES.get(
        normalized,
        normalized,
    )


# ============================================================
# JSON CLEANING
# ============================================================

def _clean_json_response(text: str) -> dict[str, Any]:
    """
    Convert Gemini's response into a Python dictionary.

    Handles responses wrapped in Markdown code fences.
    """

    if not text:
        raise ValueError("Gemini returned an empty response.")

    text = text.strip()

    # Remove Markdown code fences if Gemini adds them.
    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error(
            "Gemini returned invalid JSON: %s",
            exc,
        )
        raise ValueError(
            "Gemini returned an invalid JSON response."
        ) from exc

    if not isinstance(parsed, dict):
        raise ValueError(
            "Gemini response must be a JSON object."
        )

    return parsed


# ============================================================
# OCR PERIOD EXTRACTION
# ============================================================

def _extract_periods_from_ocr(
    ocr_pages: list[dict[str, Any]],
) -> list[str]:
    """
    Extract reporting periods from the statement header.

    The OCR may contain many dates that are NOT reporting periods
    (for example dates in notes, transactions, or other text).
    Therefore this function prioritizes dates close to statement
    header phrases and only falls back to the beginning of the
    document.

    No reporting year is hardcoded.
    """

    # Prefer dedicated header OCR because reporting periods are normally
    # printed near the statement title. Fall back to page OCR afterwards.
    ocr_sections = []

    for page in ocr_pages:
        header = str(page.get("header_text", "")).strip()
        text = str(page.get("text", "")).strip()

        if header:
            ocr_sections.append(header)
        if text:
            ocr_sections.append(text)

    ocr_text = "\n".join(ocr_sections)

    if not ocr_text.strip():
        return []

    month_names = (
        r"(?:January|February|March|April|May|June|July|"
        r"August|September|October|November|December)"
    )

    short_month_names = (
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|"
        r"Oct|Nov|Dec)"
    )

    date_patterns = [
        rf"\b{month_names}\s+\d{{1,2}},\s+\d{{4}}\b",
        rf"\b\d{{1,2}}\s+{month_names}\s+\d{{4}}\b",
        rf"\b{short_month_names}\.?\s+\d{{1,2}},\s+\d{{4}}\b",
        rf"\b\d{{1,2}}\s+{short_month_names}\.?\s+\d{{4}}\b",
    ]

    combined_date_pattern = "|".join(
        f"(?:{pattern})"
        for pattern in date_patterns
    )

    # Also support common numeric dates which OCR may preserve
    # more reliably than month names.
    numeric_date_pattern = (
        r"\b(?:"
        r"\d{1,2}[/-]\d{1,2}[/-]\d{4}"
        r"|"
        r"\d{4}[/-]\d{1,2}[/-]\d{1,2}"
        r")\b"
    )

    date_pattern = (
        f"(?:{combined_date_pattern}|{numeric_date_pattern})"
    )

    statement_header_pattern = re.compile(
        r"(?:"
        r"balance\s+sheet|"
        r"profit\s+and\s+loss|"
        r"profit\s*&\s*loss|"
        r"cash\s+flow\s+statement|"
        r"statement\s+of\s+cash\s+flows|"
        r"as\s+at|"
        r"as\s+of|"
        r"year\s+ended|"
        r"year\s+ending|"
        r"for\s+the\s+year\s+ended|"
        r"for\s+the\s+period\s+ended|"
        r"period\s+ended"
        r")",
        flags=re.IGNORECASE,
    )

    def normalize_date_text(date_text: str) -> str:
        text = " ".join(
            str(date_text).replace(".", "").split()
        ).strip()

        month_map = {
            "jan": "January",
            "feb": "February",
            "mar": "March",
            "apr": "April",
            "may": "May",
            "jun": "June",
            "jul": "July",
            "aug": "August",
            "sep": "September",
            "sept": "September",
            "oct": "October",
            "nov": "November",
            "dec": "December",
        }

        match = re.match(
            r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|"
            r"Oct|Nov|Dec)\s+(\d{1,2}),\s*(\d{4})$",
            text,
            flags=re.IGNORECASE,
        )

        if match:
            month = month_map[
                match.group(1).lower()
            ]
            return (
                f"{month} {match.group(2)}, "
                f"{match.group(3)}"
            )

        match = re.match(
            r"^(\d{1,2})\s+"
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|"
            r"Oct|Nov|Dec)\s+(\d{4})$",
            text,
            flags=re.IGNORECASE,
        )

        if match:
            month = month_map[
                match.group(2).lower()
            ]
            return (
                f"{match.group(1)} {month} "
                f"{match.group(3)}"
            )

        return text

    def add_unique(
        output: list[str],
        value: str,
    ) -> None:
        cleaned = normalize_date_text(value)

        if not cleaned:
            return

        if cleaned.lower() not in {
            item.lower()
            for item in output
        }:
            output.append(cleaned)

    # --------------------------------------------------------
    # 1. Search the beginning of the document/header.
    #
    # Financial statement period columns are normally declared
    # near the title/header. This prevents dates later in notes
    # from being mistaken for reporting periods.
    # --------------------------------------------------------

    header_text = ocr_text[:5000]

    header_candidates: list[str] = []

    for match in statement_header_pattern.finditer(
        header_text
    ):
        context_start = max(
            0,
            match.start() - 100,
        )
        context_end = min(
            len(header_text),
            match.end() + 700,
        )

        context = header_text[
            context_start:context_end
        ]

        for date_match in re.finditer(
            date_pattern,
            context,
            flags=re.IGNORECASE,
        ):
            add_unique(
                header_candidates,
                date_match.group(0),
            )

    # --------------------------------------------------------
    # 2. If the header phrase search found nothing, inspect only
    # the first 2500 characters. We deliberately do NOT scan the
    # whole document because later dates can be unrelated.
    # --------------------------------------------------------

    if not header_candidates:

        first_section = ocr_text[:2500]

        for date_match in re.finditer(
            date_pattern,
            first_section,
            flags=re.IGNORECASE,
        ):
            add_unique(
                header_candidates,
                date_match.group(0),
            )

    # --------------------------------------------------------
    # 3. Remove obviously unrelated duplicate dates and return
    # the first two statement-header periods.
    #
    # If the OCR genuinely exposes only one reliable period,
    # return one rather than inventing a second one.
    # --------------------------------------------------------

    return header_candidates[:2]


# ============================================================
# PERIOD CORRECTION
# ============================================================

def _is_valid_date_text(value: Any) -> bool:
    """Return True only for a real calendar date string."""

    if not isinstance(value, str):
        return False

    text = " ".join(value.split()).strip()

    formats = (
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%Y-%m-%d",
    )

    for fmt in formats:
        try:
            datetime.strptime(text, fmt)
            return True
        except ValueError:
            continue

    return False


def _unique_valid_periods(values: Any) -> list[str]:
    """Return unique, valid calendar dates while preserving order."""

    if not isinstance(values, list):
        return []

    result: list[str] = []

    for value in values:
        if not _is_valid_date_text(value):
            continue

        cleaned = " ".join(str(value).split()).strip()

        if cleaned.lower() not in {
            item.lower()
            for item in result
        }:
            result.append(cleaned)

    return result


def _get_ai_reporting_periods(
    extracted_data: dict[str, Any],
) -> list[str]:
    """Get valid reporting periods already produced by Gemini."""

    fields = extracted_data.get("fields")

    if isinstance(fields, dict):
        reporting_periods = fields.get("reporting_periods")

        if isinstance(reporting_periods, dict):
            values = reporting_periods.get("value")
            periods = _unique_valid_periods(values)
            if periods:
                return periods

        elif isinstance(reporting_periods, list):
            periods = _unique_valid_periods(reporting_periods)
            if periods:
                return periods

    top_level = extracted_data.get("reporting_periods")

    if isinstance(top_level, dict):
        return _unique_valid_periods(
            top_level.get("value")
        )

    if isinstance(top_level, list):
        return _unique_valid_periods(top_level)

    return []


def _fix_statement_periods(
    extracted_data: dict[str, Any],
    ocr_pages: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Safely normalize reporting periods.

    OCR is preferred only when it contains enough VALID calendar
    dates to represent the statement periods. This is important for
    scanned financial statements because OCR can produce impossible
    dates such as ``March 91, 2088``. Such OCR output must never
    overwrite a valid period returned by Gemini.

    No year or date is hardcoded here.
    """

    ocr_periods = _unique_valid_periods(
        _extract_periods_from_ocr(ocr_pages)
    )

    ai_periods = _get_ai_reporting_periods(
        extracted_data
    )

    # If OCR produced no valid dates, keep Gemini's valid dates.
    if not ocr_periods:
        periods = ai_periods
    # If OCR found fewer periods than Gemini already supplied, it is
    # incomplete, so do not replace the complete AI result.
    elif ai_periods and len(ocr_periods) < len(ai_periods):
        periods = ai_periods
    else:
        periods = ocr_periods

    if not periods:
        return extracted_data

    fields = extracted_data.get("fields")

    if not isinstance(fields, dict):
        fields = {}
        extracted_data["fields"] = fields

    reporting_periods = fields.get("reporting_periods")

    if isinstance(reporting_periods, dict):
        reporting_periods["value"] = periods
    else:
        fields["reporting_periods"] = {
            "value": periods,
            "evidence": None,
        }

    top_level_reporting_periods = extracted_data.get(
        "reporting_periods"
    )

    if isinstance(top_level_reporting_periods, dict):
        top_level_reporting_periods["value"] = periods

    # Correct statement item periods only when we have a complete
    # reliable period list. This preserves comparative periods.
    statement_items = extracted_data.get(
        "statement_items",
        [],
    )

    if not isinstance(statement_items, list):
        return extracted_data

    for item in statement_items:

        if not isinstance(item, dict):
            continue

        values = item.get("values", [])

        if not isinstance(values, list):
            continue

        if len(values) != len(periods):
            continue

        for index, value_entry in enumerate(values):

            if not isinstance(value_entry, dict):
                continue

            value_entry["period"] = periods[index]

    return extracted_data


# ============================================================
# NUMBER CLEANING
# ============================================================

def _clean_numeric_values(
    extracted_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Normalize numeric values without changing the meaning
    of the extracted data.

    Examples:

        "1,539.34" -> 1539.34
        "(500.00)" -> -500.00
        "500"      -> 500

    This also preserves null values.
    """

    def convert(value: Any) -> Any:

        if value is None:
            return None

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return value

        if not isinstance(value, str):
            return value

        text = value.strip()

        if not text:
            return None

        negative = (
            text.startswith("(")
            and text.endswith(")")
        )

        cleaned = text.replace(",", "")

        cleaned = cleaned.strip(
            "() "
        )

        # Remove common currency symbols.
        cleaned = re.sub(
            r"^[₹$€£¥]\s*",
            "",
            cleaned,
        )

        # Remove trailing currency symbols.
        cleaned = re.sub(
            r"\s*[₹$€£¥]$",
            "",
            cleaned,
        )

        try:

            number = float(cleaned)

            if negative:
                number = -number

            return number

        except ValueError:
            return value

    # --------------------------------------------------------
    # Fields
    # --------------------------------------------------------

    fields = extracted_data.get(
        "fields",
        {},
    )

    if isinstance(fields, dict):

        for field_data in fields.values():

            if not isinstance(
                field_data,
                dict,
            ):
                continue

            if "value" in field_data:

                field_data["value"] = convert(
                    field_data["value"]
                )

    # --------------------------------------------------------
    # Invoice line items
    # --------------------------------------------------------

    line_items = extracted_data.get(
        "line_items",
        [],
    )

    if isinstance(line_items, list):

        for item in line_items:

            if not isinstance(item, dict):
                continue

            for key in (
                "quantity",
                "unit_price",
                "amount",
                "line_total",
            ):

                if key in item:

                    item[key] = convert(
                        item[key]
                    )

    # --------------------------------------------------------
    # Statement items
    # --------------------------------------------------------

    statement_items = extracted_data.get(
        "statement_items",
        [],
    )

    if isinstance(statement_items, list):

        for item in statement_items:

            if not isinstance(item, dict):
                continue

            values = item.get(
                "values",
                [],
            )

            if isinstance(values, list):

                for value_entry in values:

                    if not isinstance(
                        value_entry,
                        dict,
                    ):
                        continue

                    if "value" in value_entry:

                        value_entry["value"] = convert(
                            value_entry["value"]
                        )

    return extracted_data


# ============================================================
# EVIDENCE CLEANING
# ============================================================

def _ensure_evidence_structure(
    extracted_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Make sure evidence objects have the expected structure.

    Evidence is important because the case study asks for
    source text and preferably page numbers.
    """

    def clean_evidence(
        evidence: Any,
    ) -> Any:

        if not isinstance(
            evidence,
            dict,
        ):
            return None

        source_text = evidence.get(
            "source_text"
        )

        page_number = evidence.get(
            "page_number"
        )

        if source_text is not None:
            source_text = str(
                source_text
            ).strip()

        if page_number is not None:

            try:
                page_number = int(
                    page_number
                )
            except (
                TypeError,
                ValueError,
            ):
                page_number = None

        return {
            "source_text": source_text,
            "page_number": page_number,
        }

    # --------------------------------------------------------
    # Fields
    # --------------------------------------------------------

    fields = extracted_data.get(
        "fields",
        {},
    )

    if isinstance(fields, dict):

        for field_data in fields.values():

            if isinstance(
                field_data,
                dict,
            ):

                field_data["evidence"] = clean_evidence(
                    field_data.get(
                        "evidence"
                    )
                )

    # --------------------------------------------------------
    # Invoice line items
    # --------------------------------------------------------

    line_items = extracted_data.get(
        "line_items",
        [],
    )

    if isinstance(line_items, list):

        for item in line_items:

            if isinstance(
                item,
                dict,
            ):

                item["evidence"] = clean_evidence(
                    item.get(
                        "evidence"
                    )
                )

    # --------------------------------------------------------
    # Financial statement items
    # --------------------------------------------------------

    statement_items = extracted_data.get(
        "statement_items",
        [],
    )

    if isinstance(statement_items, list):

        for item in statement_items:

            if isinstance(
                item,
                dict,
            ):

                item["evidence"] = clean_evidence(
                    item.get(
                        "evidence"
                    )
                )

    return extracted_data


# ============================================================
# EXTRACTION NORMALIZATION
# ============================================================

def _field_scalar(field: Any) -> Any:
    """Return the value from either a scalar or {value: ...} field."""
    if isinstance(field, dict) and "value" in field:
        return field.get("value")
    return field


def _set_field_scalar(fields: dict[str, Any], key: str, value: Any) -> None:
    """Update a field while preserving the application's field structure."""
    current = fields.get(key)
    if isinstance(current, dict):
        current["value"] = value
    else:
        fields[key] = {"value": value, "evidence": None}


def _normalize_currency_and_units(
    extracted_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Keep currency and scale/unit semantically separate.

    Examples:
        "INR" / "crore" -> currency=INR, units=crore
        "₹ in crore"    -> currency=INR, units=crore
        "in crore"      -> currency=None, units=crore

    The last case is intentional: crore is a scale, not a currency, and
    INR is not invented unless the source-supported extraction contains
    an INR/rupee symbol or wording.
    """
    fields = extracted_data.get("fields")
    if not isinstance(fields, dict):
        return extracted_data

    currency_key = next(
        (key for key in ("currency", "currency_code", "currency_type") if key in fields),
        None,
    )
    units_key = next(
        (key for key in ("units", "unit", "scale", "amount_unit") if key in fields),
        None,
    )

    currency_value = _field_scalar(fields.get(currency_key)) if currency_key else None
    units_value = _field_scalar(fields.get(units_key)) if units_key else None

    currency_text = str(currency_value).strip() if currency_value is not None else ""
    units_text = str(units_value).strip() if units_value is not None else ""

    combined = f"{currency_text} {units_text}".strip()
    lowered = combined.lower()

    scale_patterns = (
        (r"\bcrores?\b", "crore"),
        (r"\blakhs?\b", "lakh"),
        (r"\bmillions?\b", "million"),
        (r"\bbillions?\b", "billion"),
        (r"\bthousands?\b", "thousand"),
    )

    detected_scale = None
    for pattern, canonical in scale_patterns:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            detected_scale = canonical
            break

    source_supports_inr = bool(
        re.search(
            r"(?:₹|\bINR\b|\bRs\.?\b|\bRupees?\b|\bIndian\s+Rupees?\b)",
            combined,
            flags=re.IGNORECASE,
        )
    )

    if detected_scale:
        if units_key:
            _set_field_scalar(fields, units_key, detected_scale)
        else:
            _set_field_scalar(fields, "units", detected_scale)

    # If the extracted currency field contains only a scale phrase such as
    # "in crore", it is not a currency. Preserve the scale and clear currency.
    if currency_key:
        if detected_scale and not source_supports_inr:
            _set_field_scalar(fields, currency_key, None)
        elif source_supports_inr:
            _set_field_scalar(fields, currency_key, "INR")

    return extracted_data


def _normalize_statement_labels(
    extracted_data: dict[str, Any],
) -> dict[str, Any]:
    """Clean a small set of deterministic OCR label artifacts without inventing rows."""
    replacements = {
        "contingentliabilities": "Contingent Liabilities",
        "contingentliabilites": "Contingent Liabilities",
        "contingentliabilties": "Contingent Liabilities",
        "otherliabilities": "Other Liabilities",
        "otherassets": "Other Assets",
        "totalequity": "Total Equity",
        "totalassets": "Total Assets",
        "totalliabilities": "Total Liabilities",
        "totalincome": "Total Income",
        "totalexpenditure": "Total Expenditure",
    }

    statement_items = extracted_data.get("statement_items")
    if not isinstance(statement_items, list):
        return extracted_data

    cleaned_items = []
    for item in statement_items:
        if not isinstance(item, dict):
            continue

        label = item.get("line_item")
        if isinstance(label, str):
            normalized = re.sub(r"\s+", " ", label).strip()
            compact = re.sub(r"[^a-z]", "", normalized.lower())
            if compact in replacements:
                normalized = replacements[compact]
            # Very short OCR fragments such as "Trl" are not meaningful
            # financial labels when no values/evidence support them.
            values = item.get("values")
            evidence = item.get("evidence")
            has_values = isinstance(values, list) and any(
                isinstance(v, dict) and v.get("value") is not None
                for v in values
            )
            has_evidence = isinstance(evidence, dict) and bool(
                str(evidence.get("source_text") or "").strip()
            )
            if len(normalized) <= 3 and not has_values and not has_evidence:
                continue
            item["line_item"] = normalized

        cleaned_items.append(item)

    extracted_data["statement_items"] = cleaned_items
    return extracted_data


# ============================================================
# EXTRACTION PROMPT
# ============================================================

def build_extraction_prompt(
    document_type: str,
    ocr_pages: list[dict[str, Any]],
) -> str:

    document_type = normalize_document_type(
        document_type
    )

    pages_text = []

    for page in ocr_pages:

        page_number = page.get(
            "page_number",
            1,
        )

        text = str(
            page.get(
                "text",
                "",
            )
        )

        pages_text.append(
            f"\n===== PAGE {page_number} =====\n"
            f"{text}\n"
        )

    ocr_text = "\n".join(
        pages_text
    )

    return f"""
You are a financial document extraction system.

The document type selected by the application is:

{document_type}

Extract information ONLY from the OCR text supplied below.

IMPORTANT RULES
===============

1. Extract ALL meaningful visible information.

2. Do NOT extract only the minimum required fields.

3. Include:
   - headers
   - company names
   - dates
   - reporting periods
   - currencies
   - units
   - addresses
   - invoice information
   - parties
   - totals
   - subtotals
   - taxes
   - discounts
   - table rows
   - financial statement rows
   - schedules
   - comparative-period values
   - other meaningful visible information.

4. NEVER invent a value.

5. NEVER guess a value.

6. NEVER infer a value that is not supported by the OCR.

7. If a value cannot be read reliably, return null.

8. Preserve the meaning of negative numbers.

9. Numbers shown in parentheses are negative.

10. Preserve comparative periods separately.

11. Evidence must contain the actual supporting OCR text whenever
    practical.

12. Evidence should include the page number.

13. DO NOT create dates that are not present in the OCR.

14. DO NOT correct dates using your own assumptions.

15. For financial statements, the `values` field MUST always be
    an array.

16. Each financial statement value MUST have exactly this form:

    {{
      "period": "exact period from OCR",
      "value": 123.45
    }}

17. Do NOT use structures such as:

    "current_period_amount"
    "previous_period_amount"

18. Do NOT use dynamic keys such as:

    "march_31_2026"
    "march_31_2025"

19. If a statement has two reporting periods, return both periods
    separately.

20. If a value is unreadable, use null rather than inventing it.

21. Return ONLY valid JSON.
    Do not include explanations.
    Do not include Markdown.
    Do not include ```json fences.

DOCUMENT-SPECIFIC REQUIREMENTS
==============================

INVOICE
-------

Extract:

- invoice number
- invoice date
- due date
- vendor/seller/supplier
- customer/buyer
- billing address
- shipping address
- currency
- payment terms
- purchase/order/reference numbers
- tax information
- subtotal
- tax amount
- discount
- total amount
- amount paid
- balance due
- change/cash information if visible
- every invoice line item.

For each line item extract:

- description
- quantity
- unit price
- tax if visible
- discount if visible
- line total/amount
- any other visible columns.

BALANCE SHEET
-------------

Extract:

- company
- statement title
- reporting periods
- currency
- units
- every visible capital item
- every liability item
- every asset item
- totals
- schedules
- comparative values.

P&L
---

Extract:

- company
- statement title
- reporting periods
- currency
- units
- interest earned
- other income
- total income
- interest expended
- operating expenses
- provisions and contingencies
- total expenditure
- profit before minority interest
- minority interest
- consolidated net profit
- profit attributable to group
- appropriations
- every other visible income/expense line
- comparative values.

CASH FLOW STATEMENT
-------------------

Extract:

- company
- statement title
- reporting periods
- currency
- units
- operating cash flows
- investing cash flows
- financing cash flows
- foreign exchange/translation effects
- net increase/decrease
- opening cash
- closing cash
- adjustments
- every visible cash-flow line item
- comparative values.

REQUIRED JSON STRUCTURE
=======================

Return this structure:

{{
  "document_type": "{document_type}",
  "fields": {{}},
  "line_items": [],
  "statement_items": []
}}

For ordinary fields use:

"field_name": {{
  "value": "actual value or null",
  "evidence": {{
    "source_text": "supporting OCR text",
    "page_number": 1
  }}
}}

For financial statement rows use:

{{
  "line_item": "Capital",
  "schedule": "1",
  "values": [
    {{
      "period": "March 31, 2026",
      "value": 1539.34
    }},
    {{
      "period": "March 31, 2025",
      "value": 765.22
    }}
  ],
  "evidence": {{
    "source_text": "Capital 1 1,539.34 765.22",
    "page_number": 1
  }}
}}

The period text must come from the OCR.

OCR TEXT
========

{ocr_text}
"""


# ============================================================
# GEMINI ERROR CLASSIFICATION
# ============================================================

def _classify_gemini_error(
    exc: Exception,
) -> tuple[str, str]:
    """
    Convert Gemini SDK errors into controlled application
    error codes/messages.

    This prevents a Gemini failure from crashing the API.
    """

    error_text = str(exc).lower()

    # 429 / quota
    if (
        "429" in error_text
        or "resource_exhausted" in error_text
        or "quota exceeded" in error_text
        or "quota" in error_text
    ):

        return (
            "GEMINI_QUOTA_EXCEEDED",
            (
                "Gemini API quota has been exceeded. "
                "Please wait for the Gemini free-tier quota "
                "to reset before processing another document."
            ),
        )

    # Authentication
    if (
        "401" in error_text
        or "403" in error_text
        or "permission denied" in error_text
        or "api key" in error_text
    ):

        return (
            "GEMINI_AUTHENTICATION_FAILED",
            (
                "Gemini API authentication failed. "
                "Check the GEMINI_API_KEY configuration."
            ),
        )

    # Model not found
    if (
        "404" in error_text
        or "not found" in error_text
    ):

        return (
            "GEMINI_MODEL_NOT_FOUND",
            (
                "The configured Gemini model was not found "
                "or is not available for this API."
            ),
        )

    # Invalid request
    if (
        "400" in error_text
        or "invalid argument" in error_text
        or "invalid_argument" in error_text
    ):

        return (
            "GEMINI_INVALID_REQUEST",
            (
                "Gemini rejected the extraction request."
            ),
        )

    # Timeout
    if (
        "timeout" in error_text
        or "timed out" in error_text
    ):

        return (
            "GEMINI_TIMEOUT",
            (
                "Gemini extraction timed out."
            ),
        )

    # Generic failure
    return (
        "GEMINI_EXTRACTION_FAILED",
        (
            "AI extraction failed. "
            "Please try the document again."
        ),
    )


# ============================================================
# MAIN EXTRACTION FUNCTION
# ============================================================

def extract_structured_data(
    document_type: str,
    ocr_pages: list[dict[str, Any]],
) -> dict[str, Any]:

    normalized_type = normalize_document_type(
        document_type
    )

    # --------------------------------------------------------
    # Validate document type
    # --------------------------------------------------------

    if normalized_type not in SUPPORTED_DOCUMENT_TYPES:

        return {
            "success": False,
            "error_code": "UNSUPPORTED_DOCUMENT_TYPE",
            "message": (
                f"Unsupported document type: "
                f"{document_type}"
            ),
        }

    # --------------------------------------------------------
    # Validate OCR
    # --------------------------------------------------------

    if not ocr_pages:

        return {
            "success": False,
            "error_code": "OCR_TEXT_MISSING",
            "message": (
                "No OCR pages were available for extraction."
            ),
        }

    has_text = any(
        str(page.get("text", "")).strip()
        for page in ocr_pages
    )

    if not has_text:

        return {
            "success": False,
            "error_code": "OCR_TEXT_EMPTY",
            "message": (
                "OCR completed but no readable text "
                "was found."
            ),
        }

    # --------------------------------------------------------
    # Check Gemini key
    # --------------------------------------------------------

    if not settings.gemini_api_key:

        logger.error(
            "Gemini API key is not configured."
        )

        return {
            "success": False,
            "error_code": "GEMINI_API_KEY_MISSING",
            "message": (
                "Gemini API key is not configured."
            ),
        }

    # --------------------------------------------------------
    # Build prompt
    # --------------------------------------------------------

    prompt = build_extraction_prompt(
        document_type=normalized_type,
        ocr_pages=ocr_pages,
    )

    try:

        logger.info(
            "Starting Gemini extraction. "
            "document_type=%s pages=%s",
            normalized_type,
            len(ocr_pages),
        )

        # ----------------------------------------------------
        # Native Google Gemini SDK
        # ----------------------------------------------------

        client = genai.Client(
            api_key=settings.gemini_api_key
        )

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config={
                "temperature": 0,
                "response_mime_type": "application/json",
            },
        )

        extracted_text = getattr(
            response,
            "text",
            None,
        )

        if not extracted_text:

            logger.error(
                "Gemini returned an empty response."
            )

            return {
                "success": False,
                "error_code": "GEMINI_EMPTY_RESPONSE",
                "message": (
                    "Gemini returned an empty extraction response."
                ),
            }

        # ----------------------------------------------------
        # Parse JSON
        # ----------------------------------------------------

        extracted_data = _clean_json_response(
            extracted_text
        )

        # ----------------------------------------------------
        # Ensure expected top-level structure
        # ----------------------------------------------------

        extracted_data.setdefault(
            "document_type",
            normalized_type,
        )

        extracted_data.setdefault(
            "fields",
            {},
        )

        extracted_data.setdefault(
            "line_items",
            [],
        )

        extracted_data.setdefault(
            "statement_items",
            [],
        )

        # ----------------------------------------------------
        # Deterministic corrections
        # ----------------------------------------------------

        # 1. Fix statement periods using OCR.
        extracted_data = _fix_statement_periods(
            extracted_data,
            ocr_pages,
        )

        # 2. Normalize numeric values.
        extracted_data = _clean_numeric_values(
            extracted_data
        )

        # 3. Normalize evidence.
        extracted_data = _ensure_evidence_structure(
            extracted_data
        )

        # 4. Keep currency separate from statement scale/unit.
        extracted_data = _normalize_currency_and_units(
            extracted_data
        )

        # 5. Remove only deterministic OCR label artifacts.
        extracted_data = _normalize_statement_labels(
            extracted_data
        )

        logger.info(
            "Gemini extraction completed successfully. "
            "document_type=%s",
            normalized_type,
        )

        return {
            "success": True,
            "provider": "Google Gemini",
            "model": "gemini-3.6-flash",
            "data": extracted_data,
        }

    # ========================================================
    # GEMINI SDK/API ERROR
    # ========================================================

    except Exception as exc:

        error_code, message = _classify_gemini_error(
            exc
        )

        # Log the actual error in the terminal for debugging,
        # but DO NOT expose the complete API error to the user.
        logger.exception(
            "Gemini extraction failed. "
            "error_code=%s",
            error_code,
        )

        return {
            "success": False,
            "error_code": error_code,
            "message": message,
        }