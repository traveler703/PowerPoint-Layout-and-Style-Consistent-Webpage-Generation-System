"""
数据库连接模块
提供数据库连接池和基础操作
"""
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
import logging

logger = logging.getLogger(__name__)


def get_connection():
    """获取数据库连接"""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4',
        cursorclass=DictCursor,
        autocommit=True
    )


@contextmanager
def get_db_cursor():
    """上下文管理器，自动管理连接和游标"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        yield cursor
    except pymysql.Error as e:
        logger.error(f"数据库操作失败: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def test_connection():
    """测试数据库连接"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 测试查询
        cursor.execute("SELECT VERSION() as version")
        result = cursor.fetchone()
        
        cursor.execute("SELECT DATABASE() as database_name")
        db_result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return {
            'success': True,
            'message': '数据库连接成功!',
            'version': result['version'],
            'database': db_result['database_name']
        }
    except pymysql.err.OperationalError as e:
        return {
            'success': False,
            'message': f'连接失败: {e}',
            'version': None,
            'database': None
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'未知错误: {e}',
            'version': None,
            'database': None
        }
