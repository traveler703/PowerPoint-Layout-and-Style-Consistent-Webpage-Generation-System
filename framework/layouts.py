"""Layout atoms: reusable slide/page layout patterns (grid regions, slots)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LayoutSlot(BaseModel):
    """Named region where a component can be placed."""

    id: str
    role: str  # e.g. title, body, media, footer
    grid_area: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)


class LayoutAtom(BaseModel):
    """One layout pattern the reasoning engine can choose."""

    id: str
    name: str
    description: str = ""
    slots: list[LayoutSlot] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LayoutRegistry:
    """Register and query layout atoms. Team: load from YAML/JSON or DB."""

    def __init__(self, atoms: list[LayoutAtom] | None = None) -> None:
        self._atoms: dict[str, LayoutAtom] = {}
        for atom in atoms or []:
            self.register(atom)

    def register(self, atom: LayoutAtom) -> None:
        self._atoms[atom.id] = atom

    def get(self, layout_id: str) -> LayoutAtom | None:
        return self._atoms.get(layout_id)

    def all(self) -> list[LayoutAtom]:
        return list(self._atoms.values())

    @classmethod
    def with_minimal_defaults(cls) -> LayoutRegistry:
        reg = cls()
        reg.register(
            LayoutAtom(
                id="hero-title-body",
                name="Hero + body",
                description="Large title slot and main content column.",
                slots=[
                    LayoutSlot(id="title", role="title", grid_area="header"),
                    LayoutSlot(id="body", role="body", grid_area="main"),
                ],
            )
        )
        reg.register(
            LayoutAtom(
                id="two-column",
                name="Two columns",
                slots=[
                    LayoutSlot(id="left", role="body", grid_area="left"),
                    LayoutSlot(id="right", role="body", grid_area="right"),
                ],
            )
        )
        return reg
