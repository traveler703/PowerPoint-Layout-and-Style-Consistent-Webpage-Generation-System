import json, pathlib

path = r"c:\Users\g3056\Desktop\PPT_proj\PowerPoint-Layout-and-Style-Consistent-Webpage-Generation-System\templates\data\user_generated\dunhuang_feitian_v1.json"
with open(path, encoding="utf-8") as f:
    d = json.load(f)

raw = d["raw_html"]
print(f"raw_html len: {len(raw)}")
print(f"first 200: {repr(raw[:200])}")
print(f"has .cover-content: {'.cover-content' in raw}")
print(f"has {SLIDES_CONTENT}: {'{SLIDES_CONTENT}' in raw}")
