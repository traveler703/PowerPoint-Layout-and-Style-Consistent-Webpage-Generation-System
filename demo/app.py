"""FastAPI: static demo UI + JSON API stubs for future upload / preview."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

load_dotenv(_REPO_ROOT / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pipeline import run_once

DEMO_DIR = Path(__file__).resolve().parent
STATIC = DEMO_DIR / "static"

app = FastAPI(title="PPT-Web-Gen Demo", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


class GenerateRequest(BaseModel):
    text: str = Field(default="", description="Raw slide notes or outline")


class GenerateResponse(BaseModel):
    html: str
    report: dict


@app.get("/", response_class=HTMLResponse)
async def index() -> FileResponse:
    index_path = STATIC / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=500, detail="index.html missing")
    return FileResponse(index_path)


@app.post("/api/generate", response_model=GenerateResponse)
async def api_generate(body: GenerateRequest) -> GenerateResponse:
    html, report = await run_once(body.text or "空内容")
    return GenerateResponse(html=html, report=report.model_dump())


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run("demo.app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
