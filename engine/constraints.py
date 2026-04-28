"""Constraint solving hooks (overlap avoidance, slot capacity). Team: plug OR-Tools / Z3 / custom."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SolverResult(BaseModel):
    feasible: bool
    message: str = ""
    assignments: dict[str, Any] = Field(default_factory=dict)


class ConstraintSolver:
    """Placeholder solver returning trivial feasible result."""

    def solve(self, problem: dict[str, Any]) -> SolverResult:
        return SolverResult(
            feasible=True,
            message="stub: no constraints evaluated",
            assignments={},
        )
