"""
数据库初始化脚本
创建项目、页面、大纲等数据表
"""
import pymysql
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# SQL建表语句
SQL_STATEMENTS = [
    # 项目表
    """CREATE TABLE IF NOT EXISTS projects (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(255) NOT NULL DEFAULT '未命名项目',
        description TEXT,
        type VARCHAR(50) DEFAULT 'business',
        icon VARCHAR(10) DEFAULT '📊',
        page_count INT DEFAULT 0,
        parse_title VARCHAR(255) DEFAULT '',
        parse_summary TEXT,
        parse_sections JSON,
        parse_original_text LONGTEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        deleted_at DATETIME DEFAULT NULL,
        INDEX idx_updated (updated_at),
        INDEX idx_type (type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",

    # 大纲表
    """CREATE TABLE IF NOT EXISTS outlines (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        project_id BIGINT NOT NULL,
        title VARCHAR(255) NOT NULL,
        scenario VARCHAR(50) DEFAULT 'general',
        audience VARCHAR(100) DEFAULT '通用受众',
        page_count INT DEFAULT 0,
        outline_data JSON,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        INDEX idx_project (project_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",

    # 幻灯片表
    """CREATE TABLE IF NOT EXISTS slides (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        outline_id BIGINT NOT NULL,
        slide_order INT NOT NULL,
        title VARCHAR(255) NOT NULL,
        subtitle VARCHAR(255),
        layout VARCHAR(50) DEFAULT 'text',
        bullets JSON,
        image_url VARCHAR(500),
        background_color VARCHAR(20),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (outline_id) REFERENCES outlines(id) ON DELETE CASCADE,
        INDEX idx_outline (outline_id),
        INDEX idx_order (slide_order)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",

    # 生成的PPT表
    """CREATE TABLE IF NOT EXISTS generated_ppts (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        project_id BIGINT NOT NULL,
        outline_id BIGINT,
        style VARCHAR(50) DEFAULT 'modern',
        title VARCHAR(255),
        html_content LONGTEXT,
        slide_count INT DEFAULT 0,
        status VARCHAR(20) DEFAULT 'completed',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        FOREIGN KEY (outline_id) REFERENCES outlines(id) ON DELETE SET NULL,
        INDEX idx_project (project_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",

    # 用户会话表（用于存储前端状态）
    """CREATE TABLE IF NOT EXISTS user_sessions (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        session_id VARCHAR(100) UNIQUE NOT NULL,
        data JSON,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        expires_at DATETIME,
        INDEX idx_session (session_id),
        INDEX idx_expires (expires_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""
]


def init_database():
    """初始化数据库表"""
    conn = None
    cursor = None

    try:
        # 先连接到MySQL服务器（不指定数据库）
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            charset='utf8mb4',
            autocommit=True
        )
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 确保数据库存在
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE `{DB_NAME}`")
        print(f"Using database: {DB_NAME}")

        # 创建表
        for i, sql in enumerate(SQL_STATEMENTS):
            table_name = sql.split('CREATE TABLE IF NOT EXISTS ')[1].split(' ')[0]
            try:
                cursor.execute(sql)
                print(f"[OK] Table {table_name} created")
            except pymysql.err.OperationalError as e:
                if 'already exists' in str(e):
                    print(f"[SKIP] Table {table_name} already exists")
                else:
                    raise

        print("\nDatabase initialized!")
        print(f"Using database: {DB_NAME}")

    except pymysql.Error as e:
        print(f"Database error: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def migrate_parse_fields():
    """迁移脚本：添加解析结果字段到 projects 表"""
    conn = None
    cursor = None

    try:
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4',
            autocommit=True
        )
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 检查字段是否存在
        cursor.execute("DESCRIBE projects")
        columns = [row['Field'] for row in cursor.fetchall()]

        new_fields = [
            ('parse_title', 'VARCHAR(255) DEFAULT ""'),
            ('parse_summary', 'TEXT'),
            ('parse_sections', 'JSON'),
            ('parse_original_text', 'LONGTEXT')
        ]

        for field_name, field_type in new_fields:
            if field_name not in columns:
                cursor.execute(f"ALTER TABLE projects ADD COLUMN {field_name} {field_type}")
                print(f"[MIGRATE] Added column: {field_name}")
            else:
                print(f"[SKIP] Column {field_name} already exists")

        print("\nMigration completed!")

    except pymysql.Error as e:
        print(f"Migration error: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--migrate':
        print("=" * 50)
        print("Running migration...")
        print("=" * 50)
        migrate_parse_fields()
    else:
        print("=" * 50)
        print("Initializing database...")
        print("=" * 50)
        init_database()
