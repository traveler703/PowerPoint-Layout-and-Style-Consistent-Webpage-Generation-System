"""Aggregate evaluation for pipeline / API responses."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from evaluator.layout_metrics import LayoutMetrics
from evaluator.style_metrics import StyleMetrics


class Severity(str, Enum):
    INFO = "info"
    WARN = "warn"
    FAIL = "fail"


class EvaluationReport(BaseModel):
    passed: bool
    severity: Severity = Severity.INFO
    layout: LayoutMetrics
    style: StyleMetrics
    notes: list[str] = Field(default_factory=list)
