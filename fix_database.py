"""
数据库修复脚本 - 解决公司成员关系问题

使用方法:
1. 停止Django服务器
2. 运行 python fix_database.py
3. 重新启动Django服务器
"""
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warehouse.settings')
django.setup()

from django.db import connection

def fix_database():
    """修复数据库问题"""
    print("开始修复数据库...")
    
    with connection.cursor() as cursor:
        # 检查数据库类型
        db_type = connection.vendor
        print(f"数据库类型: {db_type}")
        
        # 1. 检查django_migrations表中的迁移记录
        print("\n1. 检查迁移记录...")
        cursor.execute("SELECT app, name FROM django_migrations WHERE app = 'companies' ORDER BY id")
        migrations = cursor.fetchall()
        print(f"找到 {len(migrations)} 条公司应用迁移记录:")
        for migration in migrations:
            print(f"- {migration[0]}.{migration[1]}")
        
        # 2. 检查数据库表
        print("\n2. 检查相关表...")
        if db_type == 'sqlite':
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%company%'")
        elif db_type == 'postgresql':
            cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE tablename LIKE '%company%'")
        else:
            print(f"不支持的数据库类型: {db_type}")
            return
        
        tables = cursor.fetchall()
        print(f"找到 {len(tables)} 个公司相关表:")
        for table in tables:
            print(f"- {table[0]}")
        
        # 3. 创建或修复公司成员表
        print("\n3. 创建/修复公司成员关系表...")
        try:
            if db_type == 'sqlite':
                # 为SQLite创建表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS companies_company_members (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company_id INTEGER NOT NULL,
                        customuser_id INTEGER NOT NULL,
                        FOREIGN KEY (company_id) REFERENCES companies_company (id),
                        FOREIGN KEY (customuser_id) REFERENCES accounts_customuser (id)
                    );
                """)
            elif db_type == 'postgresql':
                # 为PostgreSQL创建表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS companies_company_members (
                        id SERIAL PRIMARY KEY,
                        company_id INTEGER NOT NULL,
                        customuser_id INTEGER NOT NULL,
                        FOREIGN KEY (company_id) REFERENCES companies_company (id),
                        FOREIGN KEY (customuser_id) REFERENCES accounts_customuser (id)
                    );
                """)
            
            # 创建唯一索引
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS companies_company_members_unique 
                ON companies_company_members (company_id, customuser_id);
            """)
            print("公司成员表创建/修复成功")
            
            # 4. 导入数据
            print("\n4. 导入公司拥有者为成员...")
            cursor.execute("""
                INSERT OR IGNORE INTO companies_company_members (company_id, customuser_id)
                SELECT id, owner_id FROM companies_company
                WHERE owner_id IS NOT NULL;
            """)
            print("数据导入成功")
            
        except Exception as e:
            print(f"错误: {e}")
            print("尝试替代方法...")
            
            # 替代方法
            try:
                # 创建一个不同名称的表
                if db_type == 'sqlite':
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS company_member_backup (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            company_id INTEGER NOT NULL,
                            customuser_id INTEGER NOT NULL
                        );
                    """)
                elif db_type == 'postgresql':
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS company_member_backup (
                            id SERIAL PRIMARY KEY,
                            company_id INTEGER NOT NULL,
                            customuser_id INTEGER NOT NULL
                        );
                    """)
                
                # 导入数据
                cursor.execute("""
                    INSERT INTO company_member_backup (company_id, customuser_id)
                    SELECT id, owner_id FROM companies_company
                    WHERE owner_id IS NOT NULL;
                """)
                print("创建了备份表并导入数据")
            except Exception as backup_error:
                print(f"备份方法也失败: {backup_error}")
    
    print("\n修复完成！请重新启动Django服务器。")

# 修复company表的外键关系
def fix_company_foreign_keys():
    print("开始修复companies_company表的外键关系...")
    
    # 获取当前外键约束名称
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT tc.constraint_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name = 'companies_company'
              AND kcu.column_name = 'owner_id'
              AND tc.table_schema = 'public'
        """)
        
        constraint_rows = cursor.fetchall()
        if constraint_rows:
            for row in constraint_rows:
                constraint_name = row[0]
                print(f"发现外键约束: {constraint_name}")
                
                # 删除现有约束
                try:
                    cursor.execute(f"""
                        ALTER TABLE companies_company 
                        DROP CONSTRAINT {constraint_name}
                    """)
                    print(f"成功删除约束: {constraint_name}")
                except Exception as e:
                    print(f"删除约束 {constraint_name} 时出错: {str(e)}")
        else:
            print("未找到owner_id列的外键约束")
            
        # 添加正确的外键约束到accounts_customuser表
        try:
            cursor.execute("""
                ALTER TABLE companies_company 
                ADD CONSTRAINT companies_company_owner_id_fk 
                FOREIGN KEY (owner_id) REFERENCES accounts_customuser(id) ON DELETE SET NULL
            """)
            print("成功添加新的外键约束到accounts_customuser表")
        except Exception as e:
            print(f"添加新约束时出错: {str(e)}")

    print("companies_company表的外键关系修复完成")

# 修复company_members表的外键关系
def fix_company_members_foreign_keys():
    print("开始修复公司成员表的外键关系...")
    
    # 检查表名
    with connection.cursor() as cursor:
        # 确定正确的中间表名称
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name LIKE 'companies_company%' AND table_name LIKE '%member%'
        """)
        tables = cursor.fetchall()
        
        if not tables:
            print("未找到公司成员中间表")
            return
            
        for table in tables:
            table_name = table[0]
            print(f"发现表: {table_name}")
            
            # 查找外键约束
            cursor.execute(f"""
                SELECT tc.constraint_name, kcu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_name = '{table_name}'
                  AND kcu.column_name LIKE '%user%'
                  AND tc.table_schema = 'public'
            """)
            
            constraint_rows = cursor.fetchall()
            if constraint_rows:
                for row in constraint_rows:
                    constraint_name = row[0]
                    column_name = row[1]
                    print(f"表 {table_name} 发现外键约束: {constraint_name}，列: {column_name}")
                    
                    # 删除现有约束
                    try:
                        cursor.execute(f"""
                            ALTER TABLE {table_name} 
                            DROP CONSTRAINT {constraint_name}
                        """)
                        print(f"成功删除约束: {constraint_name}")
                        
                        # 添加正确的外键约束到accounts_customuser表
                        try:
                            cursor.execute(f"""
                                ALTER TABLE {table_name} 
                                ADD CONSTRAINT {table_name}_{column_name}_fk 
                                FOREIGN KEY ({column_name}) REFERENCES accounts_customuser(id) ON DELETE CASCADE
                            """)
                            print(f"成功为表 {table_name} 添加新的外键约束到accounts_customuser表")
                        except Exception as e:
                            print(f"为表 {table_name} 添加新约束时出错: {str(e)}")
                    except Exception as e:
                        print(f"删除约束 {constraint_name} 时出错: {str(e)}")
            else:
                print(f"表 {table_name} 未找到用户相关的外键约束")

    print("公司成员表的外键关系修复完成")

if __name__ == "__main__":
    fix_company_foreign_keys()
    fix_company_members_foreign_keys()
    print("数据库修复脚本执行完成") 