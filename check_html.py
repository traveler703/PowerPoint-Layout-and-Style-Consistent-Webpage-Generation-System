import pymysql
import re

conn = pymysql.connect(host='mysql6.sqlpub.com', port=3311, user='ggyy122', password='HvLtWNv7EFt8rmjh', database='ppt1122')
cur = conn.cursor()

cur.execute('SELECT id, html_content, LENGTH(html_content), slide_count, created_at FROM generated_ppts WHERE id = 13')
row = cur.fetchone()
print(f"ID: {row[0]}, 长度: {row[2]}, 页数: {row[3]}, 时间: {row[4]}")

html = row[1]
breaks = re.findall(r'<!--\s*SLIDE_BREAK\s*-->', html)
slides = html.split('<!-- SLIDE_BREAK -->')
print(f"SLIDE_BREAK数量: {len(breaks)}, 分割后页数: {len(slides)}")

if slides:
    first = slides[0]
    print(f"第一页长度: {len(first)}")
    has_slide = 'class="slide"' in first
    print(f"包含class=slide: {has_slide}")
    print(f"前150字符: {first[:150]}")

conn.close()
