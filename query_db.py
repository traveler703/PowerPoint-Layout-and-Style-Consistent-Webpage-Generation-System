# -*- coding: utf-8 -*-
import pymysql
import json

conn = pymysql.connect(
    host='mysql6.sqlpub.com',
    port=3311,
    user='ggyy122',
    password='HvLtWNv7EFt8rmjh',
    database='ppt1122',
    charset='utf8mb4'
)

cursor = conn.cursor()

# 查看项目表的完整数据
print("=== 项目表 (projects) 完整数据 ===")
cursor.execute('SELECT id, name, parse_title, parse_summary, page_count, created_at FROM projects LIMIT 10')
for row in cursor.fetchall():
    print(f"项目ID: {row[0]}")
    print(f"名称: {row[1]}")
    print(f"解析标题: {row[2]}")
    print(f"页数: {row[4]}")
    print(f"创建时间: {row[5]}")
    print("-" * 50)

# 查看项目5的完整sections
print("\n=== 项目5的大纲章节 ===")
cursor.execute('SELECT parse_sections FROM projects WHERE id = 5')
result = cursor.fetchone()
if result and result[0]:
    sections = json.loads(result[0])
    for i, s in enumerate(sections):
        print(f"{i+1}. {s}")
else:
    print("无章节数据")

# 查看已生成PPT
print("\n=== 已生成的PPT (generated_ppts) ===")
cursor.execute('SELECT id, project_id, title, slide_count, status, created_at FROM generated_ppts')
for row in cursor.fetchall():
    print(row)

conn.close()
