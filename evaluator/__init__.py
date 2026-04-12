"""
Quantitative checks: layout overlap, style deviation vs tokens.
Use `EvaluationReport` as the unified output for CI or feedback loops.
"""

from evaluator.layout_metrics import LayoutMetrics, overlap_ratio_stub
from evaluator.report import EvaluationReport, Severity
from evaluator.style_metrics import StyleMetrics, color_delta_stub

__all__ = [
    "EvaluationReport",
    "Severity",
    "LayoutMetrics",
    "StyleMetrics",
    "overlap_ratio_stub",
    "color_delta_stub",
]
