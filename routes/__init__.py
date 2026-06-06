"""HTTP route blueprints."""

from .project_routes import project_api
from .template_routes import template_api

__all__ = ["project_api", "template_api"]
