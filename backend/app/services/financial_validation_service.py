import re
from typing import Any


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
    "p&l": "profit_and_loss",
    "p & l": "profit_and_loss",
    "cash_flow_statement": "cash_flow_statement",
    "cash flow statement": "cash_flow_statement",
    "cash-flow statement": "cash_flow_statement",
    "cash flow": "cash_flow_statement",
}


def _normalize_document_type(value: Any) -> str:
    text = str(value or "").strip().lower()
    return DOCUMENT_TYPE_ALIASES.get(text, text)


# Financial amounts in statements are commonly rounded to 2 decimals.
# The relative tolerance also allows small rounding differences in large values.
TOLERANCE = 0.01
RELATIVE_TOLERANCE = 0.0001


def _normalize_label(value: Any) -> str:
    """Normalize labels for safe, deterministic matching."""
    if value is None:
        return ""

    text = str(value).lower().strip()
    text = text.replace("&", " and ")
    text = text.replace("/", " ")
    text = text.replace("-", " ")
    text = text.replace(":", " ")
    text = text.replace("(", " ")
    text = text.replace(")", " ")
    text = text.replace(",", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _to_number(value: Any) -> float | None:
    """
    Convert an extracted financial value to float.

    Parentheses are treated as negative numbers, e.g. (500.00) -> -500.00.
    Missing/unreadable values return None.
    """
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None

        negative = text.startswith("(") and text.endswith(")")

        text = text.replace(",", "")
        text = re.sub(r"^[₹$€£¥]\s*", "", text)
        text = re.sub(r"\s*[₹$€£¥]\s*$", "", text)
        text = text.strip()

        if negative:
            text = text[1:-1].strip()

        # Allow ordinary decimal/scientific numeric strings only.
        try:
            number = float(text)
        except ValueError:
            return None

        return -number if negative else number

    return None


def _field_value(extracted_data: dict[str, Any], *names: str) -> Any:
    """
    Retrieve a scalar field from either:
      extracted_data["fields"][name]
    or
      extracted_data[name]

    Supports the common {"value": ...} structure.
    """
    fields = extracted_data.get("fields", {})
    sources = []

    if isinstance(fields, dict):
        sources.append(fields)

    sources.append(extracted_data)

    for source in sources:
        for name in names:
            if name not in source:
                continue

            value = source.get(name)

            if isinstance(value, dict) and "value" in value:
                return value.get("value")

            return value

    return None


def _extract_period_values(
    statement_item: dict[str, Any],
) -> dict[str, float]:
    """
    Convert a statement item's values array into:
        {"March 31, 2026": 123.45, "March 31, 2025": 100.00}
    """
    result: dict[str, float] = {}

    values = statement_item.get("values")
    if not isinstance(values, list):
        return result

    for entry in values:
        if not isinstance(entry, dict):
            continue

        period = entry.get("period")
        value = _to_number(entry.get("value"))

        if period is None or value is None:
            continue

        period_text = str(period).strip()
        if period_text:
            result[period_text] = value

    return result


def _get_statement_items(
    extracted_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Safely retrieve structured financial statement rows."""
    statement_items = extracted_data.get("statement_items", [])

    if not isinstance(statement_items, list):
        return []

    return [
        item
        for item in statement_items
        if isinstance(item, dict)
    ]


def _find_statement_item(
    statement_items: list[dict[str, Any]],
    candidates: list[str],
) -> dict[str, Any] | None:
    """
    Find the best matching statement row.

    Matching priority:
      1. Exact normalized label.
      2. Controlled phrase match where the candidate is a complete
         word/phrase inside the actual label.
      3. Controlled fuzzy token overlap.

    Exact matching is deliberately first so that:
        "Capital"
    can never win over:
        "Total Capital & Liabilities"
    when the latter is explicitly requested.

    Generic candidates such as "total" should not be used by callers.
    """
    normalized_candidates = [
        _normalize_label(candidate)
        for candidate in candidates
        if _normalize_label(candidate)
    ]

    if not normalized_candidates:
        return None

    normalized_items = []
    for item in statement_items:
        label = _normalize_label(item.get("line_item"))
        if label:
            normalized_items.append((item, label))

    # 1. Exact match.
    for candidate in normalized_candidates:
        for item, label in normalized_items:
            if label == candidate:
                return item

    # 2. Controlled containment.
    # Prefer the longest candidate and longest actual label so a specific
    # phrase beats a short phrase such as "profit".
    candidates_by_length = sorted(
        normalized_candidates,
        key=len,
        reverse=True,
    )

    best: tuple[int, int, dict[str, Any]] | None = None

    for candidate in candidates_by_length:
        candidate_tokens = set(candidate.split())

        for item, label in normalized_items:
            label_tokens = set(label.split())

            if candidate in label:
                # Penalize matches that are only a very short generic phrase.
                score = 1000 + len(candidate_tokens) * 10 + len(candidate)
                if len(candidate_tokens) <= 1 and len(candidate) < 8:
                    score -= 500

                current = (score, len(label), item)
                if best is None or current[:2] > best[:2]:
                    best = current

            elif label in candidate:
                # Do not allow a short/generic actual label such as
                # "capital" to match a more specific requested candidate
                # such as "total capital and liabilities".
                # Otherwise the validator can incorrectly select "Capital"
                # instead of "Total Capital & Liabilities".
                if len(label_tokens) <= 1:
                    continue

                score = 700 + len(label_tokens) * 10 + len(label)

                current = (score, len(label), item)
                if best is None or current[:2] > best[:2]:
                    best = current

    if best is not None:
        return best[2]

    # 3. Controlled token overlap.
    # This is intentionally conservative and requires at least two useful
    # candidate tokens so unrelated rows are not selected.
    for candidate in candidates_by_length:
        candidate_tokens = {
            token
            for token in candidate.split()
            if len(token) > 2
        }

        if len(candidate_tokens) < 2:
            continue

        best_overlap = 0
        best_item = None

        for item, label in normalized_items:
            label_tokens = set(label.split())
            overlap = len(candidate_tokens & label_tokens)

            if overlap > best_overlap:
                best_overlap = overlap
                best_item = item

        if best_item is not None and best_overlap >= max(
            2,
            len(candidate_tokens) - 1,
        ):
            return best_item

    return None


def _find_periods(extracted_data: dict[str, Any]) -> list[str]:
    """
    Get reporting periods from fields.reporting_periods first.

    If unavailable, collect periods from statement item values.
    """
    fields = extracted_data.get("fields", {})

    if isinstance(fields, dict):
        reporting_periods = fields.get("reporting_periods")

        if isinstance(reporting_periods, dict):
            values = reporting_periods.get("value")

            if isinstance(values, list):
                periods: list[str] = []

                for value in values:
                    if value is None:
                        continue

                    text = str(value).strip()

                    if text and text not in periods:
                        periods.append(text)

                if periods:
                    return periods

            elif isinstance(values, str) and values.strip():
                return [values.strip()]

    # Some extraction versions may put reporting_periods at the top level.
    top_level_periods = extracted_data.get("reporting_periods")

    if isinstance(top_level_periods, list):
        periods = []
        for value in top_level_periods:
            if value is not None and str(value).strip():
                text = str(value).strip()
                if text not in periods:
                    periods.append(text)

        if periods:
            return periods

    periods: list[str] = []

    for item in _get_statement_items(extracted_data):
        values = item.get("values")

        if not isinstance(values, list):
            continue

        for entry in values:
            if not isinstance(entry, dict):
                continue

            period = entry.get("period")
            if period is None:
                continue

            period_text = str(period).strip()

            if period_text and period_text not in periods:
                periods.append(period_text)

    return periods


def _values_for_period(
    item: dict[str, Any] | None,
    period: str,
) -> float | None:
    """Return one numeric statement value for a reporting period."""
    if item is None:
        return None

    values = _extract_period_values(item)
    return values.get(period)


def _approximately_equal(
    calculated: float,
    reported: float,
    tolerance: float = TOLERANCE,
) -> bool:
    """Compare financial amounts using absolute + relative tolerance."""
    variance = abs(calculated - reported)
    allowed = max(
        tolerance,
        abs(reported) * RELATIVE_TOLERANCE,
    )

    return variance <= allowed


def _build_check(
    *,
    check: str,
    formula: str,
    period: str | None,
    input_values: dict[str, Any],
    calculated: float | None,
    reported: float | None,
    not_applicable_reason: str = "One or more required values are missing.",
) -> dict[str, Any]:
    """
    Build the consistent validation object required by the case study.
    """
    if calculated is None or reported is None:
        return {
            "check": check,
            "formula": formula,
            "period": period,
            "input_values": input_values,
            "calculated": calculated,
            "reported": reported,
            "variance": None,
            "status": "NOT_APPLICABLE",
            "reason": not_applicable_reason,
        }

    variance = round(calculated - reported, 2)

    status = (
        "PASS"
        if _approximately_equal(calculated, reported)
        else "FAIL"
    )

    return {
        "check": check,
        "formula": formula,
        "period": period,
        "input_values": input_values,
        "calculated": round(calculated, 2),
        "reported": round(reported, 2),
        "variance": variance,
        "status": status,
    }


# ============================================================
# BALANCE SHEET
# ============================================================

def _validate_balance_sheet(
    extracted_data: dict[str, Any],
) -> dict[str, Any]:
    statement_items = _get_statement_items(extracted_data)
    periods = _find_periods(extracted_data)

    checks: list[dict[str, Any]] = []

    # Specific labels only. Do NOT use "capital" or "total" as fallbacks.
    total_assets_item = _find_statement_item(
        statement_items,
        [
            "total assets",
            "total assets total",
        ],
    )

    total_capital_liabilities_item = _find_statement_item(
        statement_items,
        [
            "total capital and liabilities",
            "total capital & liabilities",
            "total capital liabilities",
            "capital and liabilities total",
            "total capital and liability",
        ],
    )

    for period in periods:
        total_assets = _values_for_period(
            total_assets_item,
            period,
        )

        total_capital_liabilities = _values_for_period(
            total_capital_liabilities_item,
            period,
        )

        checks.append(
            _build_check(
                check="Total Capital & Liabilities ≈ Total Assets",
                formula="Total Capital & Liabilities ≈ Total Assets",
                period=period,
                input_values={
                    "total_capital_and_liabilities":
                        total_capital_liabilities,
                    "total_assets": total_assets,
                },
                calculated=total_capital_liabilities,
                reported=total_assets,
                not_applicable_reason=(
                    "Total Capital & Liabilities and/or Total Assets "
                    "is missing for this period."
                ),
            )
        )

    # Independently reconcile the visible liability/capital and asset
    # components. This is intentionally separate from the total-vs-total
    # check: if OCR/AI corrupts a reported total, comparing that total with
    # itself would incorrectly produce PASS.

    liability_candidates = [
        ["capital"],
        ["employees stock options units outstanding",
         "employees stock options / units outstanding"],
        ["reserves and surplus"],
        ["minority interest"],
        ["deposits"],
        ["borrowings"],
        ["other liabilities and provisions"],
        ["policyholders funds", "policyholders' funds"],
    ]

    asset_candidates = [
        ["cash and balances with reserve bank of india"],
        ["balances with banks and money at call and short notice"],
        ["investments"],
        ["advances"],
        ["fixed assets"],
        ["other assets"],
    ]

    liability_items = [
        _find_statement_item(statement_items, candidates)
        for candidates in liability_candidates
    ]
    asset_items = [
        _find_statement_item(statement_items, candidates)
        for candidates in asset_candidates
    ]

    for period in periods:
        liability_values = {
            f"item_{index + 1}": _values_for_period(item, period)
            for index, item in enumerate(liability_items)
        }
        asset_values = {
            f"item_{index + 1}": _values_for_period(item, period)
            for index, item in enumerate(asset_items)
        }

        liability_inputs = {}
        for index, item in enumerate(liability_items):
            label = item.get("line_item") if item else f"item_{index + 1}"
            liability_inputs[str(label)] = liability_values[f"item_{index + 1}"]

        asset_inputs = {}
        for index, item in enumerate(asset_items):
            label = item.get("line_item") if item else f"item_{index + 1}"
            asset_inputs[str(label)] = asset_values[f"item_{index + 1}"]

        liability_values_list = list(liability_values.values())
        asset_values_list = list(asset_values.values())

        liability_calculated = (
            sum(liability_values_list)
            if liability_values_list and all(v is not None for v in liability_values_list)
            else None
        )
        asset_calculated = (
            sum(asset_values_list)
            if asset_values_list and all(v is not None for v in asset_values_list)
            else None
        )

        reported_liabilities = _values_for_period(
            total_capital_liabilities_item, period
        )
        reported_assets = _values_for_period(
            total_assets_item, period
        )

        checks.append(
            _build_check(
                check="Capital & Liability Components ≈ Total Capital & Liabilities",
                formula="Sum of extracted capital/liability components ≈ Total Capital & Liabilities",
                period=period,
                input_values=liability_inputs | {
                    "reported_total_capital_and_liabilities": reported_liabilities,
                },
                calculated=liability_calculated,
                reported=reported_liabilities,
                not_applicable_reason=(
                    "One or more required capital/liability components or "
                    "the reported total is missing for this period."
                ),
            )
        )

        checks.append(
            _build_check(
                check="Asset Components ≈ Total Assets",
                formula="Sum of extracted asset components ≈ Total Assets",
                period=period,
                input_values=asset_inputs | {
                    "reported_total_assets": reported_assets,
                },
                calculated=asset_calculated,
                reported=reported_assets,
                not_applicable_reason=(
                    "One or more required asset components or the reported "
                    "total is missing for this period."
                ),
            )
        )

    return _finalize_validation(checks)


# ============================================================
# PROFIT & LOSS
# ============================================================

def _validate_profit_and_loss(
    extracted_data: dict[str, Any],
) -> dict[str, Any]:
    statement_items = _get_statement_items(extracted_data)
    periods = _find_periods(extracted_data)

    checks: list[dict[str, Any]] = []

    interest_earned_item = _find_statement_item(
        statement_items,
        ["interest earned"],
    )

    other_income_item = _find_statement_item(
        statement_items,
        ["other income"],
    )

    # IMPORTANT: never use a generic "total" candidate.
    total_income_item = _find_statement_item(
        statement_items,
        [
            "total income",
            "total income from operations",
        ],
    )

    interest_expended_item = _find_statement_item(
        statement_items,
        [
            "interest expended",
            "interest expenditure",
        ],
    )

    operating_expenses_item = _find_statement_item(
        statement_items,
        [
            "operating expenses",
            "operating expenditure",
        ],
    )

    provisions_item = _find_statement_item(
        statement_items,
        [
            "provisions and contingencies",
            "provisions & contingencies",
            "provisions contingencies",
        ],
    )

    total_expenditure_item = _find_statement_item(
        statement_items,
        ["total expenditure"],
    )

    profit_before_minority_item = _find_statement_item(
        statement_items,
        [
            "consolidated net profit for the year before minority interest",
            "net profit for the year before minority interest",
            "profit before minority interest",
        ],
    )

    minority_interest_item = _find_statement_item(
        statement_items,
        [
            "less minority interest",
            "minority interest",
        ],
    )

    net_profit_attributable_item = _find_statement_item(
        statement_items,
        [
            "consolidated net profit for the year attributable to the group",
            "net profit for the year attributable to the group",
            "consolidated net profit attributable to the group",
            "net profit attributable to the group",
        ],
    )

    brought_forward_item = _find_statement_item(
        statement_items,
        [
            "brought forward consolidated profit attributable to the group",
            "brought forward profit attributable to the group",
            "brought forward consolidated profit",
            "brought forward profit",
        ],
    )

    total_profit_item = _find_statement_item(
        statement_items,
        [
            "total profit",
            "total available for appropriation",
            "total available for appropriations",
        ],
    )

    # 1. Interest Earned + Other Income ≈ Total Income
    for period in periods:
        interest_earned = _values_for_period(
            interest_earned_item,
            period,
        )
        other_income = _values_for_period(
            other_income_item,
            period,
        )
        total_income = _values_for_period(
            total_income_item,
            period,
        )

        calculated = None

        if (
            interest_earned is not None
            and other_income is not None
        ):
            calculated = interest_earned + other_income

        checks.append(
            _build_check(
                check="Interest Earned + Other Income ≈ Total Income",
                formula="Interest Earned + Other Income ≈ Total Income",
                period=period,
                input_values={
                    "interest_earned": interest_earned,
                    "other_income": other_income,
                    "total_income": total_income,
                },
                calculated=calculated,
                reported=total_income,
            )
        )

    # 2. Interest Expended + Operating Expenses +
    #    Provisions & Contingencies ≈ Total Expenditure
    for period in periods:
        interest_expended = _values_for_period(
            interest_expended_item,
            period,
        )
        operating_expenses = _values_for_period(
            operating_expenses_item,
            period,
        )
        provisions = _values_for_period(
            provisions_item,
            period,
        )
        total_expenditure = _values_for_period(
            total_expenditure_item,
            period,
        )

        calculated = None

        if (
            interest_expended is not None
            and operating_expenses is not None
            and provisions is not None
        ):
            calculated = (
                interest_expended
                + operating_expenses
                + provisions
            )

        checks.append(
            _build_check(
                check=(
                    "Interest Expended + Operating Expenses + "
                    "Provisions & Contingencies ≈ Total Expenditure"
                ),
                formula=(
                    "Interest Expended + Operating Expenses + "
                    "Provisions & Contingencies ≈ Total Expenditure"
                ),
                period=period,
                input_values={
                    "interest_expended": interest_expended,
                    "operating_expenses": operating_expenses,
                    "provisions_and_contingencies": provisions,
                    "total_expenditure": total_expenditure,
                },
                calculated=calculated,
                reported=total_expenditure,
            )
        )

    # 3. Total Income - Total Expenditure ≈
    #    Consolidated Net Profit before Minority Interest
    for period in periods:
        total_income = _values_for_period(
            total_income_item,
            period,
        )
        total_expenditure = _values_for_period(
            total_expenditure_item,
            period,
        )
        profit_before_minority = _values_for_period(
            profit_before_minority_item,
            period,
        )

        calculated = None

        if (
            total_income is not None
            and total_expenditure is not None
        ):
            calculated = total_income - total_expenditure

        checks.append(
            _build_check(
                check=(
                    "Total Income - Total Expenditure ≈ "
                    "Consolidated Net Profit before Minority Interest"
                ),
                formula=(
                    "Total Income - Total Expenditure ≈ "
                    "Consolidated Net Profit before Minority Interest"
                ),
                period=period,
                input_values={
                    "total_income": total_income,
                    "total_expenditure": total_expenditure,
                    "consolidated_net_profit_before_minority_interest":
                        profit_before_minority,
                },
                calculated=calculated,
                reported=profit_before_minority,
            )
        )

    # 4. Profit before Minority Interest - Minority Interest ≈
    #    Consolidated Net Profit attributable to Group
    for period in periods:
        profit_before_minority = _values_for_period(
            profit_before_minority_item,
            period,
        )
        minority_interest = _values_for_period(
            minority_interest_item,
            period,
        )
        consolidated_net_profit = _values_for_period(
            net_profit_attributable_item,
            period,
        )

        calculated = None

        if (
            profit_before_minority is not None
            and minority_interest is not None
        ):
            calculated = (
                profit_before_minority
                - minority_interest
            )

        checks.append(
            _build_check(
                check=(
                    "Profit before Minority Interest - Minority Interest "
                    "≈ Consolidated Net Profit attributable to Group"
                ),
                formula=(
                    "Profit before Minority Interest - Minority Interest "
                    "≈ Consolidated Net Profit attributable to Group"
                ),
                period=period,
                input_values={
                    "profit_before_minority_interest":
                        profit_before_minority,
                    "minority_interest": minority_interest,
                    "consolidated_net_profit":
                        consolidated_net_profit,
                },
                calculated=calculated,
                reported=consolidated_net_profit,
            )
        )

    # 5. Current Profit + Brought Forward Profit ≈
    #    Total Available for Appropriation
    #
    # This check is only applicable when all three rows exist.
    for period in periods:
        current_profit = _values_for_period(
            net_profit_attributable_item,
            period,
        )
        brought_forward_profit = _values_for_period(
            brought_forward_item,
            period,
        )
        total_available_for_appropriation = _values_for_period(
            total_profit_item,
            period,
        )

        calculated = None

        if (
            current_profit is not None
            and brought_forward_profit is not None
        ):
            calculated = (
                current_profit
                + brought_forward_profit
            )

        checks.append(
            _build_check(
                check=(
                    "Current Profit + Brought Forward Profit "
                    "≈ Total Available for Appropriation"
                ),
                formula=(
                    "Current Profit + Brought Forward Profit "
                    "≈ Total Available for Appropriation"
                ),
                period=period,
                input_values={
                    "current_profit": current_profit,
                    "brought_forward_profit": brought_forward_profit,
                    "total_available_for_appropriation":
                        total_available_for_appropriation,
                },
                calculated=calculated,
                reported=total_available_for_appropriation,
            )
        )

    return _finalize_validation(checks)


# ============================================================
# CASH FLOW STATEMENT
# ============================================================

def _validate_cash_flow(
    extracted_data: dict[str, Any],
) -> dict[str, Any]:
    statement_items = _get_statement_items(extracted_data)
    periods = _find_periods(extracted_data)

    checks: list[dict[str, Any]] = []

    operating_item = _find_statement_item(
        statement_items,
        [
            "net cash from operating activities",
            "net cash flow from operating activities",
            "cash flow from operating activities",
            "operating cash flow",
        ],
    )

    investing_item = _find_statement_item(
        statement_items,
        [
            "net cash from investing activities",
            "net cash flow from investing activities",
            "cash flow from investing activities",
            "investing cash flow",
        ],
    )

    financing_item = _find_statement_item(
        statement_items,
        [
            "net cash from financing activities",
            "net cash flow from financing activities",
            "cash flow from financing activities",
            "financing cash flow",
        ],
    )

    fx_item = _find_statement_item(
        statement_items,
        [
            "effect of exchange rate changes",
            "effect of foreign exchange rate changes",
            "foreign exchange rate changes",
            "foreign exchange",
            "fx translation adjustment",
            "translation adjustment",
        ],
    )

    net_change_item = _find_statement_item(
        statement_items,
        [
            "net increase in cash and cash equivalents",
            "net decrease in cash and cash equivalents",
            "net increase in cash",
            "net decrease in cash",
            "net change in cash and cash equivalents",
            "net change in cash",
        ],
    )

    opening_cash_item = _find_statement_item(
        statement_items,
        [
            "cash and cash equivalents at the beginning of the year",
            "cash and cash equivalents at beginning of year",
            "cash and cash equivalents at beginning",
            "cash at beginning",
            "opening cash",
        ],
    )

    closing_cash_item = _find_statement_item(
        statement_items,
        [
            "cash and cash equivalents at the end of the year",
            "cash and cash equivalents at end of year",
            "cash and cash equivalents at end",
            "cash at end",
            "closing cash",
        ],
    )

    # Applicable only when the document actually contains the adjustment.
    adjustment_item = _find_statement_item(
        statement_items,
        [
            "cash acquired on amalgamation",
            "cash acquired on acquisition",
            "cash acquired",
            "amalgamation adjustment",
            "other applicable adjustments",
            "other adjustments to cash",
        ],
    )

    for period in periods:
        operating = _values_for_period(
            operating_item,
            period,
        )
        investing = _values_for_period(
            investing_item,
            period,
        )
        financing = _values_for_period(
            financing_item,
            period,
        )
        fx = _values_for_period(
            fx_item,
            period,
        )
        net_change = _values_for_period(
            net_change_item,
            period,
        )

        # FX/translation is an optional component. If the document does not
        # show it, zero is mathematically appropriate for the calculation
        # rather than inventing an extracted value.
        calculated = None

        if (
            operating is not None
            and investing is not None
            and financing is not None
        ):
            calculated = (
                operating
                + investing
                + financing
                + (fx if fx is not None else 0.0)
            )

        checks.append(
            _build_check(
                check=(
                    "Operating + Investing + Financing + "
                    "FX/Translation ≈ Net Change in Cash"
                ),
                formula=(
                    "Operating + Investing + Financing + "
                    "FX/Translation ≈ Net Change in Cash"
                ),
                period=period,
                input_values={
                    "operating_cash_flow": operating,
                    "investing_cash_flow": investing,
                    "financing_cash_flow": financing,
                    "fx_translation": fx,
                    "net_change_in_cash": net_change,
                },
                calculated=calculated,
                reported=net_change,
            )
        )

        opening_cash = _values_for_period(
            opening_cash_item,
            period,
        )
        closing_cash = _values_for_period(
            closing_cash_item,
            period,
        )
        adjustment = _values_for_period(
            adjustment_item,
            period,
        )

        calculated_closing = None

        if (
            opening_cash is not None
            and net_change is not None
        ):
            calculated_closing = (
                opening_cash
                + net_change
                + (adjustment if adjustment is not None else 0.0)
            )

        checks.append(
            _build_check(
                check=(
                    "Opening Cash + Net Change in Cash + "
                    "Applicable Adjustments ≈ Closing Cash"
                ),
                formula=(
                    "Opening Cash + Net Change in Cash + "
                    "Cash Acquired on Amalgamation/Other Applicable "
                    "Adjustments ≈ Closing Cash"
                ),
                period=period,
                input_values={
                    "opening_cash": opening_cash,
                    "net_change_in_cash": net_change,
                    "applicable_adjustment": adjustment,
                    "closing_cash": closing_cash,
                },
                calculated=calculated_closing,
                reported=closing_cash,
            )
        )

    return _finalize_validation(checks)


# ============================================================
# INVOICE
# ============================================================

def _get_line_items(
    extracted_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Retrieve invoice line items from the supported extraction layouts."""
    candidates = []

    direct = extracted_data.get("line_items")
    if isinstance(direct, list):
        candidates.append(direct)

    fields = extracted_data.get("fields")
    if isinstance(fields, dict):
        field_line_items = fields.get("line_items")
        if isinstance(field_line_items, list):
            candidates.append(field_line_items)

    for candidate in candidates:
        return [
            item
            for item in candidate
            if isinstance(item, dict)
        ]

    return []


def _line_item_value(
    item: dict[str, Any],
    *names: str,
) -> Any:
    """Retrieve a value from an invoice line item."""
    for name in names:
        if name not in item:
            continue

        value = item.get(name)

        if isinstance(value, dict) and "value" in value:
            return value.get("value")

        return value

    return None


def _validate_invoice(
    extracted_data: dict[str, Any],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    line_items = _get_line_items(extracted_data)

    subtotal = _to_number(
        _field_value(
            extracted_data,
            "subtotal",
            "sub_total",
        )
    )
    tax_amount = _to_number(
        _field_value(
            extracted_data,
            "tax_amount",
            "tax",
            "total_tax",
        )
    )
    discount = _to_number(
        _field_value(
            extracted_data,
            "discount",
            "discount_amount",
        )
    )
    total_amount = _to_number(
        _field_value(
            extracted_data,
            "total_amount",
            "total",
            "amount_due",
            "grand_total",
        )
    )
    amount_paid = _to_number(
        _field_value(
            extracted_data,
            "amount_paid",
            "cash_paid",
            "paid_amount",
        )
    )
    change = _to_number(
        _field_value(
            extracted_data,
            "change",
            "change_amount",
        )
    )

    # 1. Quantity × Unit Price ≈ Line Total for every usable line.
    usable_line_totals: list[float] = []

    if line_items:
        for index, item in enumerate(line_items, start=1):
            quantity = _to_number(
                _line_item_value(
                    item,
                    "quantity",
                    "qty",
                )
            )
            unit_price = _to_number(
                _line_item_value(
                    item,
                    "unit_price",
                    "unit price",
                    "price",
                )
            )
            line_total = _to_number(
                _line_item_value(
                    item,
                    "amount",
                    "line_total",
                    "line_total_amount",
                    "total",
                    "line_amount",
                )
            )

            if line_total is not None:
                usable_line_totals.append(line_total)

            calculated = None

            if (
                quantity is not None
                and unit_price is not None
            ):
                calculated = quantity * unit_price

            checks.append(
                _build_check(
                    check=f"Line Item {index}: Quantity × Unit Price ≈ Line Total",
                    formula="Quantity × Unit Price ≈ Line Total",
                    period=None,
                    input_values={
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "line_total": line_total,
                    },
                    calculated=calculated,
                    reported=line_total,
                    not_applicable_reason=(
                        "Quantity, Unit Price or Line Total is missing "
                        "for this line item."
                    ),
                )
            )

        # 2. Sum of line totals ≈ subtotal when subtotal is reported.
        if usable_line_totals and subtotal is not None:
            calculated_subtotal = sum(usable_line_totals)

            checks.append(
                _build_check(
                    check="Sum of Line Totals ≈ Subtotal",
                    formula="Σ Line Totals ≈ Subtotal",
                    period=None,
                    input_values={
                        "line_totals": usable_line_totals,
                        "subtotal": subtotal,
                    },
                    calculated=calculated_subtotal,
                    reported=subtotal,
                )
            )

        # 3. If subtotal is unavailable but total is available, line totals
        # may reconcile directly to a tax-included total.
        elif usable_line_totals and total_amount is not None:
            calculated_total = sum(usable_line_totals)

            checks.append(
                _build_check(
                    check="Sum of Line Totals ≈ Total Amount",
                    formula="Σ Line Totals ≈ Total Amount (tax included if applicable)",
                    period=None,
                    input_values={
                        "line_totals": usable_line_totals,
                        "total_amount": total_amount,
                    },
                    calculated=calculated_total,
                    reported=total_amount,
                )
            )

    # 4. Subtotal + tax - discount ≈ total.
    #
    # This is only checked when all required fields are present. If the
    # displayed total already includes tax, the line-total reconciliation
    # above can still pass and this check remains NOT_APPLICABLE rather than
    # falsely declaring a tax-included invoice invalid.
    if (
        subtotal is not None
        and tax_amount is not None
        and total_amount is not None
    ):
        calculated_total = (
            subtotal
            + tax_amount
            - (discount if discount is not None else 0.0)
        )

        checks.append(
            _build_check(
                check="Subtotal + Tax - Discount ≈ Total Amount",
                formula="Subtotal + Tax - Discount ≈ Total Amount",
                period=None,
                input_values={
                    "subtotal": subtotal,
                    "tax_amount": tax_amount,
                    "discount": discount,
                    "total_amount": total_amount,
                },
                calculated=calculated_total,
                reported=total_amount,
            )
        )

    # 5. Cash Paid - Total Amount ≈ Change.
    if (
        amount_paid is not None
        and total_amount is not None
        and change is not None
    ):
        calculated_change = amount_paid - total_amount

        checks.append(
            _build_check(
                check="Cash Paid - Total Amount ≈ Change",
                formula="Cash Paid - Total Amount ≈ Change",
                period=None,
                input_values={
                    "cash_paid": amount_paid,
                    "total_amount": total_amount,
                    "change": change,
                },
                calculated=calculated_change,
                reported=change,
            )
        )

    return _finalize_validation(checks)


# ============================================================
# FINAL RESULT
# ============================================================

def _finalize_validation(
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    failed_checks = [
        check
        for check in checks
        if check.get("status") == "FAIL"
    ]

    applicable_checks = [
        check
        for check in checks
        if check.get("status") in {"PASS", "FAIL"}
    ]

    issues: list[dict[str, Any]] = []

    for check in failed_checks:
        issues.append(
            {
                "message": (
                    f"Financial validation failed: "
                    f"{check.get('check')}"
                    + (
                        f" for {check.get('period')}."
                        if check.get("period")
                        else "."
                    )
                ),
                "check": check.get("check"),
                "period": check.get("period"),
                "variance": check.get("variance"),
            }
        )

    if failed_checks:
        overall_status = "FAIL"
    elif not applicable_checks:
        overall_status = "NOT_APPLICABLE"
    else:
        overall_status = "PASS"

    return {
        "checks": checks,
        "overall_status": overall_status,
        "issues": issues,
    }


# ============================================================
# PUBLIC FUNCTION
# ============================================================

def validate_financial_document(
    document_type: str,
    extracted_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Main financial validation entry point.

    Supported:
      - invoice
      - balance_sheet
      - profit_and_loss
      - cash_flow_statement
    """
    normalized_type = _normalize_document_type(document_type)

    if normalized_type == "balance_sheet":
        result = _validate_balance_sheet(extracted_data)

    elif normalized_type == "profit_and_loss":
        result = _validate_profit_and_loss(extracted_data)

    elif normalized_type == "cash_flow_statement":
        result = _validate_cash_flow(extracted_data)

    elif normalized_type == "invoice":
        result = _validate_invoice(extracted_data)

    else:
        result = {
            "checks": [],
            "overall_status": "NOT_APPLICABLE",
            "issues": [
                {
                    "message": (
                        f"Unsupported document type: "
                        f"{document_type}"
                    )
                }
            ],
        }

    return {
        "document_type": normalized_type,
        **result,
    }
