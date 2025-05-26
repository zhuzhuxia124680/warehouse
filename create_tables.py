"""
创建必要的数据库表脚本
"""
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warehouse.settings')
django.setup()

from django.db import connection

def create_tables():
    """创建必要的数据库表"""
    with connection.cursor() as cursor:
        # 创建companies_company_members表（如果不存在）
        if connection.vendor == 'sqlite':
            # SQLite版本
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies_company_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    customuser_id INTEGER NOT NULL,
                    FOREIGN KEY (company_id) REFERENCES companies_company (id),
                    FOREIGN KEY (customuser_id) REFERENCES accounts_customuser (id)
                );
            """)
            print("已创建companies_company_members表")
        elif connection.vendor == 'postgresql':
            # PostgreSQL版本
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies_company_members (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL,
                    customuser_id INTEGER NOT NULL,
                    FOREIGN KEY (company_id) REFERENCES companies_company (id),
                    FOREIGN KEY (customuser_id) REFERENCES accounts_customuser (id)
                );
            """)
            print("已创建companies_company_members表")
        else:
            print(f"不支持的数据库类型: {connection.vendor}")
            return
        
        # 确保没有重复项
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS companies_company_members_unique 
            ON companies_company_members (company_id, customuser_id);
        """)
        
        # 导入现有数据
        print("尝试将拥有者添加为成员...")
        try:
            cursor.execute("""
                INSERT INTO companies_company_members (company_id, customuser_id)
                SELECT id, owner_id FROM companies_company
                WHERE owner_id IS NOT NULL
                  AND NOT EXISTS (
                    SELECT 1 FROM companies_company_members 
                    WHERE company_id = companies_company.id 
                      AND customuser_id = companies_company.owner_id
                  );
            """)
            print("成功导入公司拥有者作为成员")
        except Exception as e:
            print(f"导入现有数据时出错: {e}")
        
        print("表创建完成")

if __name__ == "__main__":
    create_tables() 