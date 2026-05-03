import re
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from templates.template_loader import load_template
from templates.renderer import TemplateRenderer

tpl = load_template("dunhuang_xi")
print(f"Template: {tpl.name}")
print(f"raw_html length: {len(tpl.raw_html)}")

# Count slides-track occurrences
raw = tpl.raw_html
slides_track_count = raw.count("slides-track")
print(f"slides-track in raw_html: {slides_track_count}")

# Check if SLIDES_CONTENT appears in raw_html
has_placeholder = "{{SLIDES_CONTENT}}" in raw
print(f"Has {{SLIDES_CONTENT}}: {has_placeholder}")

# Render a cover page
renderer = TemplateRenderer(tpl)
cover = renderer.render_cover_page(
    title="敦煌艺术之旅",
    subtitle="穿越千年丝路 探寻壁画瑰宝",
    page_number=1,
    total_pages=8,
)
print("\n=== Cover rendered (first 200 chars) ===")
print(cover[:200])
print(f"\nHas slide-wrapper: {'slide-wrapper' in cover}")
print(f"Has slide-container: {'slide-container' in cover}")

# Merge 2 pages
pages = [cover, cover]
doc = renderer.merge_pages_to_document(pages, document_title="Test", navigation=True)
print(f"\n=== Doc length: {len(doc)} ===")
print(f"slide-container count: {doc.count('slide-container')}")
print(f"slide-wrapper count: {doc.count('slide-wrapper')}")
slide_div = '<div class="slide '
print(f"slide count: {doc.count(slide_div)}")

# Check SLIDES_CONTENT replacement
sc_matches = [m.start() for m in re.finditer(r'\{\{SLIDES_CONTENT\}\}', doc)]
print(f"{{{{SLIDES_CONTENT}}}} remaining: {len(sc_matches)}")
