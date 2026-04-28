# -*- coding: utf-8 -*-
from services.outline_generator import OutlineGenerator

og = OutlineGenerator()

outline_text = """第1页 封面

上海：东方明珠，未来之城

第2页 目录

内容导览
• 城市概况
• 历史与现代
• 文化与生活
• 经济与创新
• 总结展望

第3页 城市概况

基本信息与定位
• 中国国际经济、金融、贸易、航运中心
• 位于长江入海口，面积6340.5平方公里，人口约2500万
• 别称"魔都"，兼具东方神韵与国际风貌

第4页 历史与现代

从十里洋场到世界都会
• 历史脉络：从小渔村到通商口岸，中西合璧的海派文化起源
• 现代飞跃：1990年浦东开发开放，从农田到世界级金融中心
• 城市地标：外滩万国建筑群与陆家嘴摩天大楼隔江相望

第5页 文化与生活

海纳百川的多元体验
• 海派文化：传统江南文化与西方文明交融的独特气质
• 美食天堂：本帮菜、小笼包、生煎馒头，中西美食汇聚
• 艺术生活：博物馆、美术馆、话剧演出，24小时不夜城活力

第6页 经济与创新

全球城市的竞争力
• 经济规模：中国GDP最高城市，跨国公司地区总部聚集地
• 创新引擎：张江科学城、临港新片区，聚焦人工智能、生物医药
• 交通枢纽：世界最大集装箱港口，全球最长地铁网络之一

第7页 总结展望

上海：机遇与魅力之城
• 总结：传统与现代、东方与西方完美融合的国际化大都市
• 展望：建设卓越的全球城市，引领长三角一体化发展
• 邀请：欢迎亲身体验这座城市的无限可能与独特魅力"""

outline = og.parse_manual_outline('上海城市介绍PPT大纲', outline_text)

print("=== Outline Parse Test ===")
print(f"Title: {outline['title']}")
print(f"Slide Count: {len(outline['slides'])}")
print()
for s in outline['slides']:
    print(f"Page {s['page_number']} [{s['slide_type']}]")
    print(f"  Title: {s['title']}")
    if s.get('content_points'):
        print(f"  Points: {len(s['content_points'])} items")
        for p in s['content_points'][:3]:
            if len(p) > 40:
                print(f"    - {p[:40]}...")
            else:
                print(f"    - {p}")
        if len(s['content_points']) > 3:
            print(f"    ... and {len(s['content_points']) - 3} more")
    print()
