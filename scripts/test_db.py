"""
数据库连接测试脚本
"""
import sys
from database import test_connection

if __name__ == '__main__':
    print("=" * 50)
    print("测试数据库连接...")
    print("=" * 50)
    
    result = test_connection()
    
    print(f"\n结果: {result['message']}")
    if result['success']:
        print(f"MySQL版本: {result['version']}")
        print(f"当前数据库: {result['database']}")
        sys.exit(0)
    else:
        sys.exit(1)
