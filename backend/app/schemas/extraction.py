from typing import Any, Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    source_text: Optional[str] = None
    page_number: Optional[int] = None


class ExtractedField(BaseModel):
    value: Any = None
    evidence: Optional[Evidence] = None


class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    evidence: Optional[Evidence] = None


class StatementLineItem(BaseModel):
    label: Optional[str] = None
    values: dict[str, Any] = Field(default_factory=dict)
    evidence: Optional[Evidence] = None


class ExtractionResult(BaseModel):
    document_type: str
    fields: dict[str, ExtractedField] = Field(default_factory=dict)
    line_items: list[LineItem] = Field(default_factory=list)
    statement_items: list[StatementLineItem] = Field(default_factory=list)