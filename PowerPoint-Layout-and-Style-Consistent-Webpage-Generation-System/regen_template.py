"""重新生成 dunhuang_feitian_v1 模板（使用修复后的 prompt）。"""
import asyncio, json, pathlib, sys

proj = pathlib.Path(__file__).parent
sys.path.insert(0, str(proj))

from scripts.template_generator import TemplateGenerator


async def main():
    tg = TemplateGenerator()
    result = await tg.generate(
        "设计一个敦煌飞天风格的PPT模板，主题是敦煌文化与丝路艺术，"
        "配色以朱砂红、敦煌金、墨褐色为主，字体使用 ZCOOL XiaoWei 和 Noto Serif SC，"
        "风格古典华丽、飘逸灵动，体现东方美学。只需要5种页面：封面、目录、章节、内容、结束。"
    )

    if result["success"]:
        parsed = result["parsed"]
        out_path = proj / "templates" / "data" / "user_generated" / "dunhuang_feitian_v1.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
        print(f"模板已保存: {out_path}")
        print(f"page_types: {list(parsed.get('page_types', {}).keys())}")
        print(f"raw_html 长度: {len(parsed.get('raw_html', ''))}")
    else:
        print("生成失败!")
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
