"""
LandPPT Demo - 配置文件
"""
import os
from dotenv import load_dotenv

load_dotenv()

# DeepSeek API配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "ppt1122")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# 应用配置
APP_HOST = "127.0.0.1"
APP_PORT = 5000
DEBUG = True

# PPT生成配置
DEFAULT_PAGE_COUNT = 10
MIN_PAGE_COUNT = 5
MAX_PAGE_COUNT = 20

# 画布尺寸 (16:9)
CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720

# Header/Footer固定高度
HEADER_HEIGHT = 80
FOOTER_HEIGHT = 60
MAIN_CONTENT_MIN_HEIGHT = CANVAS_HEIGHT - HEADER_HEIGHT - FOOTER_HEIGHT

# 超时配置
API_TIMEOUT = 120
MAX_RETRIES = 3

# 场景类型
SCENARIOS = [
    "technology",      # 科技
    "business",        # 商业
    "education",       # 教育
    "medical",         # 医疗
    "finance",         # 金融
    "marketing",       # 市场营销
    "report",          # 报告
    "general"          # 通用
]

# 风格类型
STYLES = [
    "modern",          # 现代
    "classic",         # 经典
    "minimal",         # 简约
    "professional",    # 专业
    "creative"         # 创意
]
