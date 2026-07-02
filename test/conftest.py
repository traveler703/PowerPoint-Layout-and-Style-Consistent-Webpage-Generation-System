"""测试默认使用 LLM 桩，避免误连外网。"""

from __future__ import annotations

import os

os.environ.setdefault("PPT_USE_STUB", "1")
