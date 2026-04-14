"""Layout atoms: reusable slide/page layout patterns (grid regions, slots)."""

from __future__ import annotations

import json
from pathlib import Path
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
    def from_json_file(cls, path: str | Path) -> LayoutRegistry:
        """Load atoms from ``layouts.json`` (see ``framework/data/layouts.json``)."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        layouts = raw.get("layouts", raw) if isinstance(raw, dict) else raw
        atoms: list[LayoutAtom] = []
        for item in layouts:
            slots = [
                LayoutSlot(
                    id=s["id"],
                    role=s["role"],
                    grid_area=s.get("grid_area"),
                    constraints=s.get("constraints") or {},
                )
                for s in item.get("slots", [])
            ]
            atoms.append(
                LayoutAtom(
                    id=item["id"],
                    name=item.get("name", item["id"]),
                    description=item.get("description", ""),
                    slots=slots,
                    metadata=item.get("metadata") or {},
                )
            )
        return cls(atoms)

    @classmethod
    def with_minimal_defaults(cls) -> LayoutRegistry:
        """Fallback when JSON 缺失：与 ``hero-title-body`` / ``two-column`` 兼容。"""
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

    @classmethod
    def default_from_package_data(cls, base: Path | None = None) -> LayoutRegistry:
        """优先加载 ``framework/data/layouts.json``，失败则 ``with_minimal_defaults``。"""
        root = base or Path(__file__).resolve().parent
        path = root / "data" / "layouts.json"
        if path.is_file():
            try:
                return cls.from_json_file(path)
            except OSError:
                pass
        return cls.with_minimal_defaults()
