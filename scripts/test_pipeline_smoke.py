import asyncio

from pipeline import run_once


def test_run_once_returns_html_and_report() -> None:
    html, report = asyncio.run(run_once("test content"))
    assert "<!DOCTYPE html>" in html
    assert report.passed is True
