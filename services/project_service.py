"""
项目服务层
提供项目的CRUD操作
"""
import json
from database import get_db_cursor
from datetime import datetime


class ProjectService:
    """项目服务类"""

    @staticmethod
    def create_project(name, description='', type='business', icon='📊'):
        """创建新项目"""
        with get_db_cursor() as cursor:
            sql = """
                INSERT INTO projects (name, description, type, icon)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (name, description, type, icon))
            return cursor.lastrowid

    @staticmethod
    def get_project(project_id):
        """获取单个项目"""
        with get_db_cursor() as cursor:
            sql = "SELECT * FROM projects WHERE id = %s AND deleted_at IS NULL"
            cursor.execute(sql, (project_id,))
            return cursor.fetchone()

    @staticmethod
    def get_all_projects(limit=100, offset=0):
        """获取所有项目"""
        with get_db_cursor() as cursor:
            sql = """
                SELECT * FROM projects
                WHERE deleted_at IS NULL
                ORDER BY updated_at DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (limit, offset))
            return cursor.fetchall()

    @staticmethod
    def update_project(project_id, **kwargs):
        """更新项目"""
        if not kwargs:
            return False

        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = %s")
            values.append(value)

        values.append(project_id)
        sql = f"UPDATE projects SET {', '.join(fields)} WHERE id = %s"

        with get_db_cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0

    @staticmethod
    def delete_project(project_id):
        """软删除项目"""
        with get_db_cursor() as cursor:
            sql = "UPDATE projects SET deleted_at = NOW() WHERE id = %s"
            cursor.execute(sql, (project_id,))
            return cursor.rowcount > 0

    @staticmethod
    def search_projects(keyword):
        """搜索项目"""
        with get_db_cursor() as cursor:
            sql = """
                SELECT * FROM projects
                WHERE deleted_at IS NULL
                AND (name LIKE %s OR description LIKE %s)
                ORDER BY updated_at DESC
            """
            pattern = f"%{keyword}%"
            cursor.execute(sql, (pattern, pattern))
            return cursor.fetchall()


class OutlineService:
    """大纲服务类"""

    @staticmethod
    def create_outline(project_id, title, scenario='general', audience='通用受众',
                       page_count=0, outline_data=None):
        """创建大纲"""
        with get_db_cursor() as cursor:
            sql = """
                INSERT INTO outlines (project_id, title, scenario, audience, page_count, outline_data)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            outline_json = json.dumps(outline_data, ensure_ascii=False) if outline_data else None
            cursor.execute(sql, (project_id, title, scenario, audience, page_count, outline_json))
            return cursor.lastrowid

    @staticmethod
    def get_outline(outline_id):
        """获取大纲"""
        with get_db_cursor() as cursor:
            sql = "SELECT * FROM outlines WHERE id = %s"
            cursor.execute(sql, (outline_id,))
            result = cursor.fetchone()
            if result and result.get('outline_data'):
                try:
                    result['outline_data'] = json.loads(result['outline_data'])
                except:
                    pass
            return result

    @staticmethod
    def get_outlines_by_project(project_id):
        """获取项目的所有大纲"""
        with get_db_cursor() as cursor:
            sql = """
                SELECT * FROM outlines
                WHERE project_id = %s
                ORDER BY created_at DESC
            """
            cursor.execute(sql, (project_id,))
            results = cursor.fetchall()
            for r in results:
                if r.get('outline_data'):
                    try:
                        r['outline_data'] = json.loads(r['outline_data'])
                    except:
                        pass
            return results

    @staticmethod
    def update_outline(outline_id, **kwargs):
        """更新大纲"""
        if not kwargs:
            return False

        fields = []
        values = []
        for key, value in kwargs.items():
            if key == 'outline_data':
                value = json.dumps(value, ensure_ascii=False) if value else None
            fields.append(f"{key} = %s")
            values.append(value)

        values.append(outline_id)
        sql = f"UPDATE outlines SET {', '.join(fields)} WHERE id = %s"

        with get_db_cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0


class SlideService:
    """幻灯片服务类"""

    @staticmethod
    def create_slide(outline_id, slide_order, title, subtitle='', layout='text',
                     bullets=None, image_url=None, background_color=None):
        """创建幻灯片"""
        with get_db_cursor() as cursor:
            sql = """
                INSERT INTO slides (outline_id, slide_order, title, subtitle, layout,
                                   bullets, image_url, background_color)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            bullets_json = json.dumps(bullets, ensure_ascii=False) if bullets else None
            cursor.execute(sql, (outline_id, slide_order, title, subtitle, layout,
                                 bullets_json, image_url, background_color))
            return cursor.lastrowid

    @staticmethod
    def get_slides_by_outline(outline_id):
        """获取大纲的所有幻灯片"""
        with get_db_cursor() as cursor:
            sql = """
                SELECT * FROM slides
                WHERE outline_id = %s
                ORDER BY slide_order ASC
            """
            cursor.execute(sql, (outline_id,))
            results = cursor.fetchall()
            for r in results:
                if r.get('bullets'):
                    try:
                        r['bullets'] = json.loads(r['bullets'])
                    except:
                        pass
            return results

    @staticmethod
    def update_slide(slide_id, **kwargs):
        """更新幻灯片"""
        if not kwargs:
            return False

        fields = []
        values = []
        for key, value in kwargs.items():
            if key == 'bullets':
                value = json.dumps(value, ensure_ascii=False) if value else None
            fields.append(f"{key} = %s")
            values.append(value)

        values.append(slide_id)
        sql = f"UPDATE slides SET {', '.join(fields)} WHERE id = %s"

        with get_db_cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0

    @staticmethod
    def delete_slide(slide_id):
        """删除幻灯片"""
        with get_db_cursor() as cursor:
            sql = "DELETE FROM slides WHERE id = %s"
            cursor.execute(sql, (slide_id,))
            return cursor.rowcount > 0


class GeneratedPptService:
    """生成的PPT服务类"""

    @staticmethod
    def create_ppt(project_id, outline_id=None, style='modern', title='',
                   html_content='', slide_count=0, status='completed'):
        """创建生成的PPT记录"""
        with get_db_cursor() as cursor:
            sql = """
                INSERT INTO generated_ppts (project_id, outline_id, style, title,
                                           html_content, slide_count, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (project_id, outline_id, style, title,
                                 html_content, slide_count, status))
            return cursor.lastrowid

    @staticmethod
    def get_ppt(ppt_id):
        """获取PPT"""
        with get_db_cursor() as cursor:
            sql = "SELECT * FROM generated_ppts WHERE id = %s"
            cursor.execute(sql, (ppt_id,))
            return cursor.fetchone()

    @staticmethod
    def get_ppts_by_project(project_id, limit=10):
        """获取项目的所有PPT"""
        with get_db_cursor() as cursor:
            sql = """
                SELECT * FROM generated_ppts
                WHERE project_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """
            cursor.execute(sql, (project_id, limit))
            return cursor.fetchall()

    @staticmethod
    def update_ppt(ppt_id, **kwargs):
        """更新PPT"""
        if not kwargs:
            return False

        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = %s")
            values.append(value)

        values.append(ppt_id)
        sql = f"UPDATE generated_ppts SET {', '.join(fields)} WHERE id = %s"

        with get_db_cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0

    @staticmethod
    def get_total_slides():
        """获取所有PPT的总页数"""
        with get_db_cursor() as cursor:
            sql = "SELECT COALESCE(SUM(slide_count), 0) as total FROM generated_ppts"
            cursor.execute(sql)
            result = cursor.fetchone()
            return result['total'] if result else 0
