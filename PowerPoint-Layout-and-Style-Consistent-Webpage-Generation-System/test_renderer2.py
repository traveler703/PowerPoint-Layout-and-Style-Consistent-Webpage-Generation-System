import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from templates.template_loader import load_template
from templates.renderer import TemplateRenderer

tpl = load_template("dunhuang_xi")
renderer = TemplateRenderer(tpl)

cover = renderer.render_cover_page(title="敦煌艺术之旅", subtitle="穿越千年丝路", page_number=1, total_pages=8)
pages = [cover, cover]

doc = renderer.merge_pages_to_document(pages, document_title="Test", navigation=True)

# Show the slides-track area
start = doc.find('<div class="slides-track"')
if start == -1:
    start = doc.find('slides-track')
end = min(start + 1000, len(doc))
print("=== slides-track area ===")
print(doc[start:end])
print()

# Count slides
slides = re.findall(r'<div class="slide ', doc)
print(f"Total <div class=\"slide \" occurrences: {len(slides)}")
containers = re.findall(r'<div class="slide-container"', doc)
print(f"Total <div class=\"slide-container\" occurrences: {len(containers)}")
wrappers = re.findall(r'<div class="slide-wrapper"', doc)
print(f"Total <div class=\"slide-wrapper\" occurrences: {len(wrappers)}")
