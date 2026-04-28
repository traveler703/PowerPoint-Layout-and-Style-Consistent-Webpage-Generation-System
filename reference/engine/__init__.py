"""
Semantic layout matching and constraint solving.
Wire `ReasoningEngine` into the pipeline after content understanding.
"""

from engine.constraints import ConstraintSolver, SolverResult
from engine.reasoning import PagePlan, ReasoningEngine, StubReasoningEngine
from engine.types import SemanticPageInput

__all__ = [
    "ConstraintSolver",
    "PagePlan",
    "ReasoningEngine",
    "SemanticPageInput",
    "SolverResult",
    "StubReasoningEngine",
]
