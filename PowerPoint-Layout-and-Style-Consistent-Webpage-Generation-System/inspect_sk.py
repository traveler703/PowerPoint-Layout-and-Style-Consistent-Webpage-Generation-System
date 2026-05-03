import json, sys, os
sys.stdout.reconfigure(encoding="utf-8")

with open("templates/data/user_generated/llm_step2_extracted.json", encoding="utf-8") as f:
    t = json.load(f)

out = []
for ptype, config in t["page_types"].items():
    sk = config["skeleton"]
    out.append(f"=== {ptype} (len={len(sk)}) ===")
    out.append(sk[:800])
    out.append("")

with open("skeleton_inspect.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))

print("Written to skeleton_inspect.txt")
