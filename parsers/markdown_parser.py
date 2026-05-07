from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path

from .base import ParsedNode


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
LIST_RE = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)")


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _fallback_find_image_file(raw_path: str, source_path: str | None) -> str:
    """
    上传场景下 markdown 会被保存到 output/uploads，导致相对图片路径失效。
    兜底按文件名在项目中定位图片（优先 reference/testcases）。
    """
    clean = (raw_path or "").strip().strip("<>").split("?", 1)[0].split("#", 1)[0]
    if not clean:
        return ""
    target_name = Path(clean).name
    if not target_name:
        return ""

    root = _project_root()
    preferred_roots: list[Path] = []
    if source_path:
        preferred_roots.append(Path(source_path).resolve().parent)
    preferred_roots.extend([root / "reference" / "testcases", root / "reference", root])

    for base in preferred_roots:
        if not base.exists():
            continue
        try:
            for p in base.rglob(target_name):
                if p.is_file():
                    return str(p.resolve())
        except Exception:
            continue
    return ""


def _resolve_image_path(raw_path: str, source_path: str | None) -> tuple[str, bool]:
    p = (raw_path or "").strip()
    if not p:
        return "", False
    if p.startswith(("data:image/", "http://", "https://")):
        return p, False
    clean = p.strip("<>").split("?", 1)[0].split("#", 1)[0]
    img_path = Path(clean)
    if img_path.is_absolute():
        return str(img_path), True
    if not source_path:
        fallback = _fallback_find_image_file(raw_path, source_path)
        return (fallback, True) if fallback else (str(img_path), True)

    candidate = (Path(source_path).parent / img_path).resolve()
    if candidate.exists() and candidate.is_file():
        return str(candidate), True
    fallback = _fallback_find_image_file(raw_path, source_path)
    return (fallback, True) if fallback else (str(candidate), True)


def _load_image_as_data_uri(raw_path: str, source_path: str | None) -> str:
    resolved, is_local = _resolve_image_path(raw_path, source_path)
    if not resolved:
        return ""
    if not is_local:
        return resolved
    file_path = Path(resolved)
    if not file_path.exists() or not file_path.is_file():
        return ""
    blob = file_path.read_bytes()
    mime, _ = mimetypes.guess_type(file_path.name)
    if not mime or not mime.startswith("image/"):
        mime = "image/png"
    b64 = base64.b64encode(blob).decode("ascii")
    return f"data:{mime};base64,{b64}"


def parse_markdown_text(text: str, source_path: str | None = None) -> list[ParsedNode]:
    nodes: list[ParsedNode] = []
    current: ParsedNode | None = None
    image_count = 0

    for line in text.splitlines():
        h = HEADING_RE.match(line)
        if h:
            level = len(h.group(1))
            title = h.group(2).strip()
            current = ParsedNode(level=level, title=title)
            nodes.append(current)
            continue

        if current is None:
            current = ParsedNode(level=1, title="文档内容")
            nodes.append(current)

        images = list(IMAGE_RE.finditer(line))
        if images:
            for m in images:
                alt = (m.group(1) or "").strip()
                raw_path = (m.group(2) or "").strip()
                title = (m.group(3) or "").strip()
                data_uri = _load_image_as_data_uri(raw_path, source_path)
                if not data_uri:
                    continue
                image_count += 1
                caption = title or alt or f"图片 {image_count}"
                current.images.append({"path": data_uri, "caption": caption, "source": "markdown"})
            line = IMAGE_RE.sub("", line).strip()

        li = LIST_RE.match(line)
        if li:
            bullet = li.group(1).strip()
            current.bullets.append({"title": bullet, "description": ""})
        elif line.strip():
            current.raw_text = (current.raw_text + "\n" + line.strip()).strip()

    return nodes
