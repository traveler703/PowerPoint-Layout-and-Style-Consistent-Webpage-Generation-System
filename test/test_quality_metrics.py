from evaluator.style_metrics import color_consistency_from_html, extract_colors_from_html
from generator.prompts.content_html import build_content_html_prompt
from engine.types import SemanticPageInput
from templates.renderer import TemplateRenderer
from templates.template_loader import load_template


def test_runtime_helper_color_is_not_counted_as_slide_deviation():
    html = """
    <style id="landppt-runtime-overrides">
      .scrollbar { background: rgba(148, 163, 184, .45); }
    </style>
    <div style="color:#333333;background:rgb(255, 255, 255)">content</div>
    """
    metrics = color_consistency_from_html(
        html,
        {"color-text": "#333333", "color-background": "#FFFFFF"},
    )

    assert metrics.global_color_deviation_percent == 0
    assert "#94A3B8" not in extract_colors_from_html(html)


def test_color_deviation_is_weighted_by_actual_color_usage():
    html = """
    <div style="color:#333333;background:#FFFFFF;border-color:#FFFFFF">
      <span style="color:#FF0000">accent</span>
    </div>
    """
    metrics = color_consistency_from_html(
        html,
        {"color-text": "#333333", "color-background": "#FFFFFF"},
    )

    assert metrics.global_color_deviation_percent == 25


def test_runtime_overrides_center_and_fit_the_canvas():
    renderer = TemplateRenderer(load_template("tech"))
    html = renderer._inject_runtime_overrides("<html><head></head><body></body></html>")

    assert "justify-content:center!important" in html
    assert "align-items:center!important" in html
    assert "window.innerWidth / 1280" in html
    assert "window.innerHeight / 720" in html


def test_content_prompt_uses_template_card_color():
    page = SemanticPageInput(
        page_index=0,
        title="Title",
        summary="Summary",
        page_type="content",
        bullet_points=["Point"],
    )
    system_prompt, user_prompt = build_content_html_prompt(
        page,
        css_variables={
            "color-primary": "#F5A0B5",
            "color-text": "#333333",
            "color-text-muted": "#666666",
            "color-card": "#FCE4EC",
        },
    )

    assert "background:#FCE4EC" in system_prompt
    assert "模板卡片色 #FCE4EC" in user_prompt
    assert "元素重叠率必须为0" in user_prompt
