# -*- coding: utf-8 -*-
import pymysql

conn = pymysql.connect(
    host='mysql6.sqlpub.com',
    port=3311,
    user='ggyy122',
    password='HvLtWNv7EFt8rmjh',
    database='ppt1122',
    charset='utf8mb4'
)

cursor = conn.cursor()

# 查看生成的PPT的HTML内容长度
print("=== 检查生成的PPT内容 ===")
cursor.execute('SELECT id, title, LENGTH(html_content) as html_length, slide_count FROM generated_ppts')
for row in cursor.fetchall():
    print(f"ID: {row[0]}, 标题: {row[1]}, HTML长度: {row[2]}, 页数: {row[3]}")

# 查看html_content的前200个字符
cursor.execute('SELECT html_content FROM generated_ppts WHERE id = 1')
result = cursor.fetchone()
if result and result[0]:
    print(f"\nHTML内容预览（前500字符）:\n{result[0][:500]}")
else:
    print("\nHTML内容为空！")

conn.close()
