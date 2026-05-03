import json

path = r"C:\Users\g3056\Desktop\PPT_proj\PowerPoint-Layout-and-Style-Consistent-Webpage-Generation-System\templates\data\user_generated\dunhuang_feitian_v1.json"
with open(path, encoding="utf-8") as f:
    d = json.load(f)

raw = d["raw_html"]
# Find "ending-deco.circle-bg" CSS
idx = raw.find("ending-deco.circle-bg")
print("ending-deco.circle-bg at:", idx)
if idx > 0:
    print(raw[idx-10:idx+500])
    print("---")
# Also find .ending-title
idx2 = raw.find(".ending-title")
print(".ending-title at:", idx2)
if idx2 > 0:
    print(raw[idx2-10:idx2+300])
