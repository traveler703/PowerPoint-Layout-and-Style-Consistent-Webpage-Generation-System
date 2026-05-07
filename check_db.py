import sqlite3
import json
import sys

conn = sqlite3.connect('data.db')
cursor = conn.cursor()

# 查询项目和大纲
cursor.execute('''
    SELECT p.id, p.name, o.id, o.title, o.outline_data
    FROM projects p
    LEFT JOIN outlines o ON p.id = o.project_id
    ORDER BY p.id DESC
    LIMIT 1
''')
result = cursor.fetchone()
if result:
    print(f'Project ID: {result[0]}, Name: {result[1]}')
    print(f'Outline ID: {result[2]}, Title: {result[3]}')
    try:
        data = json.loads(result[4])
        print('\nPages:')
        for i, slide in enumerate(data.get('slides', [])[:10]):
            slide_type = slide.get('slide_type', 'N/A')
            title = slide.get('title', 'No title')
            if title:
                title = title[:40]
            print(f'  Page {i+1}: slide_type="{slide_type}", title="{title}"')
    except json.JSONDecodeError as e:
        print(f'JSON parse error: {e}')
else:
    print('No data found')
    
conn.close()
