"""FastAPI：静态演示 UI + JSON API（生成 / 主题列表 / 健康检查）。"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

load_dotenv(_REPO_ROOT / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from framework.tokens import load_theme_catalog
from pipeline import run_pipeline

DEMO_DIR = Path(__file__).resolve().parent
STATIC = DEMO_DIR / "static"

app = FastAPI(title="PPT-Web-Gen", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

_THEMES_PATH = _REPO_ROOT / "framework" / "data" / "themes.json"


class GenerateRequest(BaseModel):
    text: str = Field(default="", description="大纲或多页（用 --- 分隔）")
    theme_id: str = Field(default="business_blue", description="主题 ID")
    output_format: str = Field(default="html", description="html | markdown")
    prefer_langchain: bool = Field(
        default=False,
        description="为 True 时优先走 LangChain 调用链（需 API Key）",
    )


class GenerateResponse(BaseModel):
    content: str
    format: str
    report: dict


@app.get("/", response_class=HTMLResponse)
async def index() -> FileResponse:
    index_path = STATIC / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=500, detail="index.html missing")
    return FileResponse(index_path)


@app.get("/api/themes")
async def api_themes() -> dict:
    cat = load_theme_catalog(_THEMES_PATH)
    return {
        "themes": [
            {
                "id": tid,
                "preview": {
                    "primary": t.colors.get("primary", ""),
                    "surface": t.colors.get("surface", ""),
                },
            }
            for tid, t in cat.items()
        ]
    }


@app.post("/api/generate", response_model=GenerateResponse)
async def api_generate(body: GenerateRequest) -> GenerateResponse:
    fmt = body.output_format.lower().strip()
    if fmt not in ("html", "markdown"):
        raise HTTPException(status_code=400, detail="output_format 须为 html 或 markdown")
    content, report = await run_pipeline(
        body.text or "空内容",
        theme_id=body.theme_id,
        output_format=fmt,
        prefer_langchain=body.prefer_langchain,
    )
    return GenerateResponse(
        content=content,
        format=fmt,
        report=report.model_dump(),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run("demo.app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
