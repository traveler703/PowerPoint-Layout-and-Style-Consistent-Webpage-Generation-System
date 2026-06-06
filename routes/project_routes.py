"""Project, outline, generated presentation, and statistics routes."""

from __future__ import annotations

import logging
from typing import Any

from flask import Blueprint, jsonify, request

from database import test_connection
from services.project_service import (
    GeneratedPptService,
    OutlineService,
    ProjectService,
)

logger = logging.getLogger(__name__)
project_api = Blueprint("project_api", __name__)


def _serialize_datetimes(record: dict[str, Any]) -> dict[str, Any]:
    """Convert database datetime values into JSON-compatible strings."""

    for field in ("created_at", "updated_at"):
        value = record.get(field)
        if value:
            record[field] = value.isoformat() if hasattr(value, "isoformat") else str(value)
    return record


@project_api.get("/api/projects")
def get_projects():
    """Return projects ordered by their most recent update."""

    try:
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)
        projects = [
            _serialize_datetimes(project)
            for project in ProjectService.get_all_projects(limit=limit, offset=offset)
        ]
        return jsonify({"success": True, "projects": projects, "count": len(projects)})
    except Exception as exc:
        logger.error("获取项目列表失败: %s", exc)
        return jsonify({"error": str(exc)}), 500


@project_api.get("/api/projects/<int:project_id>")
def get_project(project_id: int):
    """Return one project."""

    try:
        project = ProjectService.get_project(project_id)
        if not project:
            return jsonify({"error": "项目不存在"}), 404
        return jsonify({"success": True, "project": _serialize_datetimes(project)})
    except Exception as exc:
        logger.error("获取项目失败: %s", exc)
        return jsonify({"error": str(exc)}), 500


@project_api.post("/api/projects")
def create_project():
    """Create a project."""

    try:
        data = request.get_json() or {}
        project_id = ProjectService.create_project(
            name=data.get("name", "未命名项目"),
            description=data.get("description", ""),
            type=data.get("type", "business"),
            icon=data.get("icon", "📊"),
        )
        return jsonify(
            {
                "success": True,
                "project_id": project_id,
                "message": "项目创建成功",
            }
        ), 201
    except Exception as exc:
        logger.error("创建项目失败: %s", exc)
        return jsonify({"error": str(exc)}), 500


@project_api.put("/api/projects/<int:project_id>")
def update_project(project_id: int):
    """Update editable project fields."""

    try:
        data = request.get_json() or {}
        allowed_fields = {"name", "description", "type", "icon", "page_count"}
        updates = {key: value for key, value in data.items() if key in allowed_fields}
        if not updates:
            return jsonify({"error": "没有有效的更新字段"}), 400

        if not ProjectService.update_project(project_id, **updates):
            return jsonify({"error": "项目不存在"}), 404
        return jsonify({"success": True, "message": "项目更新成功"})
    except Exception as exc:
        logger.error("更新项目失败: %s", exc)
        return jsonify({"error": str(exc)}), 500


@project_api.delete("/api/projects/<int:project_id>")
def delete_project(project_id: int):
    """Soft-delete a project."""

    try:
        if not ProjectService.delete_project(project_id):
            return jsonify({"error": "项目不存在"}), 404
        return jsonify({"success": True, "message": "项目删除成功"})
    except Exception as exc:
        logger.error("删除项目失败: %s", exc)
        return jsonify({"error": str(exc)}), 500


@project_api.get("/api/projects/search")
def search_projects():
    """Search project names and descriptions."""

    try:
        keyword = request.args.get("q", "")
        if not keyword:
            return jsonify({"success": True, "projects": [], "count": 0})
        projects = ProjectService.search_projects(keyword)
        return jsonify({"success": True, "projects": projects, "count": len(projects)})
    except Exception as exc:
        logger.error("搜索项目失败: %s", exc)
        return jsonify({"error": str(exc)}), 500


@project_api.get("/api/projects/<int:project_id>/outlines")
def get_project_outlines(project_id: int):
    """Return all outlines belonging to a project."""

    try:
        outlines = OutlineService.get_outlines_by_project(project_id)
        return jsonify({"success": True, "outlines": outlines, "count": len(outlines)})
    except Exception as exc:
        logger.error("获取大纲失败: %s", exc)
        return jsonify({"error": str(exc)}), 500


@project_api.post("/api/outlines")
def create_outline():
    """Create an outline and update the project page count."""

    try:
        data = request.get_json() or {}
        project_id = data.get("project_id")
        if not project_id:
            return jsonify({"error": "项目ID不能为空"}), 400

        outline_id = OutlineService.create_outline(
            project_id=project_id,
            title=data.get("title", "未命名大纲"),
            outline_data=data.get("outline_data"),
        )
        ProjectService.update_project(
            project_id,
            page_count=data.get("page_count", 0),
        )
        return jsonify(
            {
                "success": True,
                "outline_id": outline_id,
                "message": "大纲创建成功",
            }
        ), 201
    except Exception as exc:
        logger.error("创建大纲失败: %s", exc)
        return jsonify({"error": str(exc)}), 500


@project_api.get("/api/outlines/<int:outline_id>")
def get_outline(outline_id: int):
    """Return one outline."""

    try:
        outline = OutlineService.get_outline(outline_id)
        if not outline:
            return jsonify({"error": "大纲不存在"}), 404
        return jsonify({"success": True, "outline": outline})
    except Exception as exc:
        logger.error("获取大纲失败: %s", exc)
        return jsonify({"error": str(exc)}), 500


@project_api.put("/api/outlines/<int:outline_id>")
def update_outline(outline_id: int):
    """Update editable outline fields."""

    try:
        data = request.get_json() or {}
        allowed_fields = {"title", "page_count", "outline_data"}
        updates = {key: value for key, value in data.items() if key in allowed_fields}
        if not updates:
            return jsonify({"error": "没有有效的更新字段"}), 400

        if not OutlineService.update_outline(outline_id, **updates):
            return jsonify({"error": "大纲不存在"}), 404
        return jsonify({"success": True, "message": "大纲更新成功"})
    except Exception as exc:
        logger.error("更新大纲失败: %s", exc)
        return jsonify({"error": str(exc)}), 500


@project_api.post("/api/ppts")
def create_ppt():
    """Store a generated presentation."""

    try:
        data = request.get_json() or {}
        project_id = data.get("project_id")
        if not project_id:
            return jsonify({"error": "项目ID不能为空"}), 400

        ppt_id = GeneratedPptService.create_ppt(
            project_id=project_id,
            outline_id=data.get("outline_id"),
            style=data.get("style", "modern"),
            title=data.get("title", ""),
            html_content=data.get("html_content", ""),
            slide_count=data.get("slide_count", 0),
            status=data.get("status", "completed"),
        )
        return jsonify(
            {"success": True, "ppt_id": ppt_id, "message": "PPT保存成功"}
        ), 201
    except Exception as exc:
        logger.error("保存PPT失败: %s", exc)
        return jsonify({"error": str(exc)}), 500


@project_api.get("/api/projects/<int:project_id>/ppts")
def get_project_ppts(project_id: int):
    """Return generated presentations belonging to a project."""

    try:
        limit = request.args.get("limit", 10, type=int)
        ppts = GeneratedPptService.get_ppts_by_project(project_id, limit=limit)
        return jsonify({"success": True, "ppts": ppts, "count": len(ppts)})
    except Exception as exc:
        logger.error("获取PPT列表失败: %s", exc)
        return jsonify({"error": str(exc)}), 500


@project_api.get("/api/ppts/<int:ppt_id>")
def get_ppt(ppt_id: int):
    """Return one generated presentation."""

    try:
        ppt = GeneratedPptService.get_ppt(ppt_id)
        if not ppt:
            return jsonify({"error": "PPT不存在"}), 404
        return jsonify({"success": True, "ppt": ppt})
    except Exception as exc:
        logger.error("获取PPT失败: %s", exc)
        return jsonify({"error": str(exc)}), 500


@project_api.get("/api/db-test")
def db_test():
    """Return database connectivity information."""

    return jsonify(test_connection())


@project_api.get("/api/stats")
def get_stats():
    """Return project and generated-slide totals."""

    try:
        return jsonify(
            {
                "success": True,
                "total_slides": GeneratedPptService.get_total_slides(),
                "project_count": len(ProjectService.get_all_projects(limit=1000)),
            }
        )
    except Exception as exc:
        logger.error("获取统计数据失败: %s", exc)
        return jsonify({"error": str(exc)}), 500
