import pymysql
import re
import os

conn = pymysql.connect(host='mysql6.sqlpub.com', port=3311, user='ggyy122', password='HvLtWNv7EFt8rmjh', database='ppt1122')
cur = conn.cursor()

cur.execute('SELECT title, html_content, slide_count FROM generated_ppts WHERE id = 13')
row = cur.fetchone()
title, html_content, slide_count = row
print(f"标题: {title}, 页数: {slide_count}")

# 按 SLIDE_BREAK 分割
slides = html_content.split('<!-- SLIDE_BREAK -->')
print(f"分割后页数: {len(slides)}")

# 保存每一页为独立 HTML 文件
output_dir = r"c:\Users\g3056\Desktop\PPT_proj\exported_slides"
os.makedirs(output_dir, exist_ok=True)

for i, slide_html in enumerate(slides):
    filename = os.path.join(output_dir, f"slide_{i+1:02d}.html")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(slide_html)
    print(f"保存: {filename} ({len(slide_html)} 字节)")

print(f"\n已保存到: {output_dir}")

# 也保存完整合并版本（可浏览器直接打开翻页）
full_filename = os.path.join(output_dir, "full_ppt.html")
with open(full_filename, 'w', encoding='utf-8') as f:
    # 创建带翻页功能的完整HTML
    slides_json = []
    for i, slide in enumerate(slides):
        slides_json.append(f"'{i+1}': `<div class='slide-page'>{slide}</div>`")
    
    wrapper = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ margin: 0; font-family: sans-serif; background: #1a1a2e; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
        .slide-container {{ width: 1280px; height: 720px; background: white; box-shadow: 0 4px 20px rgba(0,0,0,0.3); position: relative; }}
        .slide-page {{ display: none; width: 100%; height: 100%; }}
        .slide-page.active {{ display: block; }}
        .controls {{ position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); }}
        button {{ padding: 10px 30px; font-size: 18px; cursor: pointer; }}
        #counter {{ color: white; font-size: 24px; margin: 0 20px; }}
    </style>
</head>
<body>
    <div class="slide-container">
        {''.join(f'<div class="slide-page" data-page="{i+1}">{s}</div>' for i, s in enumerate(slides))}
    </div>
    <div class="controls">
        <button onclick="prev()">上一页</button>
        <span id="counter">1 / {len(slides)}</span>
        <button onclick="next()">下一页</button>
    </div>
    <script>
        let current = 1;
        const total = {len(slides)};
        function show(n) {{
            document.querySelectorAll('.slide-page').forEach((el, i) => {{
                el.classList.toggle('active', i+1 === n);
            }});
            document.getElementById('counter').textContent = n + ' / ' + total;
            current = n;
        }}
        function prev() {{ show(Math.max(1, current-1)); }}
        function next() {{ show(Math.min(total, current+1)); }}
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowLeft') prev();
            if (e.key === 'ArrowRight') next();
        }});
    </script>
</body>
</html>'''
    f.write(wrapper)
print(f"\n完整可翻页版本: {full_filename}")

conn.close()
