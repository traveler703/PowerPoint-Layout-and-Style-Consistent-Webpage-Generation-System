"""Template persistence and preview routes."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from flask import Blueprint, Response, jsonify, request

from templates.template_loader import get_loader

logger = logging.getLogger(__name__)
template_api = Blueprint("template_api", __name__)

TEMPLATE_DATA_DIR = Path(__file__).resolve().parent.parent / "templates" / "data"
USER_TEMPLATE_DIR = TEMPLATE_DATA_DIR / "user_generated"
USER_PREVIEW_DIR = TEMPLATE_DATA_DIR / "user_generated_html"

PREVIEW_NAVIGATION_BRIDGE = """
<style id="landppt-preview-canvas-fix">
html,body{
  width:1280px!important;
  height:720px!important;
  min-width:1280px!important;
  min-height:720px!important;
  overflow:hidden!important;
}
#slidesWrapper,.slides-wrapper{
  width:1280px!important;
  height:720px!important;
  min-width:1280px!important;
  min-height:720px!important;
}
#slidesTrack,.slides-track{
  width:1280px!important;
  height:720px!important;
  min-width:1280px!important;
  min-height:720px!important;
}
#slidesTrack > .slide-container,
.slides-track > .slide-container,
#slidesTrack > .slide,
.slides-track > .slide{
  width:1280px!important;
  min-width:1280px!important;
  flex:0 0 1280px!important;
}
</style>
<script id="landppt-preview-navigation-bridge">
(function () {
  var correctingPosition = false;

  function currentSlideIndex() {
    var activeDot = document.querySelector('.nav-dot.active');
    if (activeDot && activeDot.parentElement) {
      var dots = Array.prototype.slice.call(
        activeDot.parentElement.querySelectorAll('.nav-dot')
      );
      var dotIndex = dots.indexOf(activeDot);
      if (dotIndex >= 0) return dotIndex;
    }

    var currentPage = document.getElementById('currentPage');
    var pageNumber = currentPage ? parseInt(currentPage.textContent, 10) : NaN;
    return Number.isFinite(pageNumber) ? Math.max(0, pageNumber - 1) : 0;
  }

  function forceExactPosition(index) {
    var track = document.getElementById('slidesTrack');
    if (!track) return;
    var wrapper = document.getElementById('slidesWrapper');
    if (wrapper) {
      wrapper.scrollLeft = 0;
      wrapper.scrollTop = 0;
    }
    var slides = track.querySelectorAll(':scope > .slide-container, :scope > .slide');
    var target = slides[index];
    var offset = target ? target.offsetLeft : index * 1280;
    var exactTransform = 'translateX(-' + offset + 'px)';
    if (track.style.transform !== exactTransform) {
      correctingPosition = true;
      track.style.transform = exactTransform;
      window.requestAnimationFrame(function () {
        correctingPosition = false;
      });
    }
  }

  function navigateTo(index) {
    var target = Math.max(0, Number(index) || 0);
    var dots = document.querySelectorAll('.nav-dot');
    if (dots[target] && typeof dots[target].click === 'function') {
      dots[target].click();
    } else if (typeof window.goToSlide === 'function') {
      window.goToSlide(target);
    }
    window.requestAnimationFrame(function () {
      forceExactPosition(target);
    });
  }

  window.addEventListener('message', function (event) {
    var data = event.data || {};
    if (data.type === 'landppt-preview-nav') {
      navigateTo(data.slide);
    }
  });

  function installTrackCorrection() {
    var track = document.getElementById('slidesTrack');
    if (!track || typeof MutationObserver === 'undefined') return;
    var observer = new MutationObserver(function () {
      if (correctingPosition) return;
      window.requestAnimationFrame(function () {
        forceExactPosition(currentSlideIndex());
      });
    });
    observer.observe(track, { attributes: true, attributeFilter: ['style'] });
    forceExactPosition(currentSlideIndex());
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', installTrackCorrection);
  } else {
    installTrackCorrection();
  }
})();
</script>
"""


def _template_summary(
    template_data: dict[str, Any],
    template_id: str,
    default_type: str,
) -> dict[str, Any]:
    """Build the compact template object returned to the gallery."""

    return {
        "template_id": template_id,
        "template_name": template_data.get("template_name"),
        "description": template_data.get("description"),
        "css_variables": template_data.get("css_variables"),
        "tags": template_data.get("tags", []),
        "is_default": template_data.get("is_default", False),
        "page_types": list(template_data.get("page_types", {}).keys()),
        "template_type": template_data.get("template_type", default_type),
    }


def _load_template_summaries(
    directory: Path,
    default_type: str,
    seen_template_ids: set[str],
) -> list[dict[str, Any]]:
    """Load template metadata from one directory."""

    templates: list[dict[str, Any]] = []
    if not directory.exists():
        return templates

    for path in directory.glob("*.json"):
        try:
            template_data = json.loads(path.read_text(encoding="utf-8"))
            template_id = template_data.get("template_id") or path.stem
            if template_id in seen_template_ids:
                continue
            seen_template_ids.add(template_id)
            templates.append(_template_summary(template_data, template_id, default_type))
        except Exception as exc:
            logger.error("加载模板文件 %s 失败: %s", path, exc)
    return templates


def _safe_template_id(template_id: str) -> str:
    """Return a filesystem-safe template identifier."""

    return re.sub(r"[^a-zA-Z0-9_-]", "_", template_id)


@template_api.get("/api/templates")
def get_templates():
    """Return preset and user-created templates."""

    try:
        seen_template_ids: set[str] = set()
        templates = _load_template_summaries(
            TEMPLATE_DATA_DIR,
            "preset",
            seen_template_ids,
        )
        templates.extend(
            _load_template_summaries(
                USER_TEMPLATE_DIR,
                "user",
                seen_template_ids,
            )
        )
        return jsonify({"success": True, "templates": templates})
    except Exception as exc:
        logger.error("获取模板列表失败: %s", exc)
        return jsonify({"error": str(exc)}), 500


@template_api.post("/api/templates")
def create_template():
    """Persist a user-created template."""

    try:
        data = request.get_json() or {}
        template_data = data.get("template_data") or data
        template_id = template_data.get("template_id")
        if not template_id:
            return jsonify({"error": "template_id 不能为空"}), 400

        USER_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
        output_path = USER_TEMPLATE_DIR / f"{template_id}.json"
        output_path.write_text(
            json.dumps(template_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        get_loader().reload()
        logger.info("模板已保存: %s", output_path)

        return jsonify(
            {
                "success": True,
                "message": "模板保存成功",
                "template": {
                    "template_id": template_id,
                    "template_name": template_data.get("template_name", ""),
                    "description": template_data.get("description", ""),
                    "css_variables": template_data.get("css_variables"),
                    "tags": template_data.get("tags", []),
                    "page_types": list(template_data.get("page_types", {}).keys()),
                    "template_type": template_data.get("template_type", "user"),
                    "is_default": False,
                },
            }
        ), 201
    except Exception as exc:
        logger.exception("创建模板失败")
        return jsonify({"error": str(exc)}), 500


@template_api.put("/api/templates/<template_id>")
def update_template(template_id: str):
    """Update user-editable template metadata."""

    try:
        path = USER_TEMPLATE_DIR / f"{template_id}.json"
        if not path.exists():
            return jsonify({"error": "模板不存在"}), 404

        template_data = json.loads(path.read_text(encoding="utf-8"))
        updates = request.get_json() or {}
        for field in ("template_name", "description", "tags"):
            if field in updates:
                template_data[field] = updates[field]

        path.write_text(
            json.dumps(template_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        get_loader().reload()
        return jsonify(
            {
                "success": True,
                "template": {
                    "template_id": template_id,
                    "template_name": template_data.get("template_name", ""),
                    "description": template_data.get("description", ""),
                    "tags": template_data.get("tags", []),
                },
            }
        )
    except Exception as exc:
        logger.error("更新模板失败: %s", exc)
        return jsonify({"error": str(exc)}), 500


@template_api.delete("/api/templates/<template_id>")
def remove_template(template_id: str):
    """Delete a user-created template."""

    try:
        path = USER_TEMPLATE_DIR / f"{template_id}.json"
        if not path.exists():
            return jsonify({"error": "模板不存在"}), 404
        path.unlink()
        get_loader().reload()
        return jsonify({"success": True, "message": "模板已删除"})
    except Exception as exc:
        logger.error("删除模板失败: %s", exc)
        return jsonify({"error": str(exc)}), 500


@template_api.post("/api/save-preview-html")
def save_preview_html():
    """Save or clear the generated HTML preview for a template."""

    try:
        data = request.get_json() or {}
        safe_id = _safe_template_id((data.get("template_id") or "unknown").strip())
        safe_id = safe_id or "unknown"
        html = data.get("html") or ""
        USER_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
        path = USER_PREVIEW_DIR / f"{safe_id}.html"

        if html:
            path.write_text(html, encoding="utf-8")
            return jsonify({"success": True, "path": str(path), "size": len(html)})

        if path.exists():
            path.unlink()
        return jsonify({"success": True, "cleared": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@template_api.get("/api/template-preview/<template_id>")
def serve_template_preview(template_id: str):
    """Return a complete generated template preview."""

    safe_id = _safe_template_id(template_id)
    if not safe_id or safe_id != template_id:
        return jsonify({"error": "template_id 无效"}), 400

    path = USER_PREVIEW_DIR / f"{safe_id}.html"
    if not path.is_file():
        return jsonify({"error": "模板预览不存在"}), 404

    html = path.read_text(encoding="utf-8")
    if "landppt-preview-navigation-bridge" not in html:
        if "</body>" in html:
            html = html.replace(
                "</body>",
                PREVIEW_NAVIGATION_BRIDGE + "\n</body>",
                1,
            )
        else:
            html += PREVIEW_NAVIGATION_BRIDGE

    response = Response(html, mimetype="text/html")
    response.headers["Cache-Control"] = "no-store"
    return response
