from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProductFacts(BaseModel):
    name: str
    brand: str | None = None
    category: str = "unknown"
    ingredients: list[str] = Field(default_factory=list)
    additives: list[str] = Field(default_factory=list)
    source_detail: str | None = None


class ProductAnalysis(BaseModel):
    product_id: str
    source: str
    confidence: float
    category: str
    name: str
    brand: str | None = None
    ingredients: list[str] = Field(default_factory=list)
    additives: list[str] = Field(default_factory=list)
    barcode: str | None = None
    lens_title: str | None = None
    debug: dict[str, Any] = Field(default_factory=dict)
