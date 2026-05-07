from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedImage:
    path: str = ""
    caption: str = ""
    source: str = ""


@dataclass
class ParsedTable:
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    caption: str = ""


@dataclass
class ParsedNode:
    level: int
    title: str
    raw_text: str = ""
    bullets: list[dict] = field(default_factory=list)
    tables: list[ParsedTable] = field(default_factory=list)
    images: list[ParsedImage] = field(default_factory=list)
