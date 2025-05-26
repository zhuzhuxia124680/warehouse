"""
检查数据库中所有表的脚本
"""
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warehouse.settings')
django.setup()

from django.db import connection

def list_all_tables():
    """列出数据库中的所有表"""
    with connection.cursor() as cursor:
        if connection.vendor == 'sqlite':
            # SQLite
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        elif connection.vendor == 'postgresql':
            # PostgreSQL
            cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema';")
        else:
            print(f"不支持的数据库类型: {connection.vendor}")
            return
        
        tables = cursor.fetchall()
        print(f"数据库类型: {connection.vendor}")
        print(f"找到 {len(tables)} 个表:")
        for table in tables:
            print(f"- {table[0]}")
        
        # 特别检查与公司成员相关的表
        company_tables = [t[0] for t in tables if 'company' in t[0].lower() and ('member' in t[0].lower() or 'customuser' in t[0].lower())]
        if company_tables:
            print("\n找到公司成员相关表:")
            for table in company_tables:
                print(f"- {table}")
                # 显示表结构
                if connection.vendor == 'sqlite':
                    cursor.execute(f"PRAGMA table_info({table});")
                    columns = cursor.fetchall()
                    for col in columns:
                        print(f"  - {col[1]} ({col[2]})")
        else:
            print("\n没有找到公司成员相关表")

if __name__ == "__main__":
    list_all_tables() 