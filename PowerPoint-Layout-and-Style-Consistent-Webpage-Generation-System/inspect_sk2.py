import sys, os
sys.stdout.reconfigure(encoding="utf-8")

import re

with open("templates/data/user_generated/llm_step1_forest.html", encoding="utf-8") as f:
    html = f.read()

from bs4 import BeautifulSoup
soup = BeautifulSoup(html, "html.parser")

for ptype in ["cover", "toc", "section", "content", "ending"]:
    div = soup.find("div", class_=lambda c: c and ptype in c.split())
    if div:
        sk = str(div)
        # Check for title placeholder
        has_title = "{{title}}" in sk
        has_chapter = "{{chapter_tag}}" in sk
        has_content = "{{content}}" in sk
        print(f"=== {ptype} ===")
        print(f"  has {{title}}: {has_title}")
        print(f"  has {{chapter_tag}}: {has_chapter}")
        print(f"  has {{content}}: {has_content}")
        # Show first 300 chars
        preview = re.sub(r"\s+", " ", sk[:400])
        print(f"  preview: {preview}")
        print()
