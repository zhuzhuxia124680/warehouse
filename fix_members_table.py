#!/usr/bin/env python
"""
修复公司成员表结构脚本

使用方法:
1. 运行 python fix_members_table.py
2. 查看输出结果
"""
import psycopg2
import psycopg2.extras

# 数据库连接配置
DB_CONFIG = {
    'dbname': 'warehouse',
    'user': 'postgres',
    'password': '124680',
    'host': 'localhost',
    'port': '5432'
}

def connect_db():
    """连接到PostgreSQL数据库"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

def check_table_structure(conn):
    """检查公司成员表的结构"""
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    try:
        # 检查companies_company_members表是否存在
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'companies_company_members'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("表 companies_company_members 不存在，将创建它...")
            return False
        
        # 检查表的列结构
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'companies_company_members'
        """)
        
        columns = [row['column_name'] for row in cursor.fetchall()]
        print(f"表 companies_company_members 存在，列: {', '.join(columns)}")
        
        # 检查是否有customuser_id列
        has_customuser_id = 'customuser_id' in columns
        has_user_id = 'user_id' in columns
        
        return {
            'exists': True,
            'has_customuser_id': has_customuser_id,
            'has_user_id': has_user_id,
            'columns': columns
        }
        
    except Exception as e:
        print(f"检查表结构时出错: {e}")
        return False
    finally:
        cursor.close()

def fix_table_structure(conn, check_result):
    """修复表结构"""
    cursor = conn.cursor()
    
    try:
        if not check_result or not check_result['exists']:
            # 创建表
            cursor.execute("""
                CREATE TABLE companies_company_members (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL,
                    customuser_id INTEGER NOT NULL,
                    CONSTRAINT companies_company_members_company_id_fk 
                        FOREIGN KEY (company_id) REFERENCES companies_company(id) ON DELETE CASCADE,
                    CONSTRAINT companies_company_members_customuser_id_fk 
                        FOREIGN KEY (customuser_id) REFERENCES accounts_customuser(id) ON DELETE CASCADE,
                    CONSTRAINT companies_company_members_unique UNIQUE (company_id, customuser_id)
                )
            """)
            print("已创建 companies_company_members 表")
            return True
            
        elif check_result['has_user_id'] and not check_result['has_customuser_id']:
            # 如果有user_id但没有customuser_id，重命名列
            cursor.execute("""
                ALTER TABLE companies_company_members
                RENAME COLUMN user_id TO customuser_id
            """)
            print("已将 user_id 列重命名为 customuser_id")
            return True
            
        elif not check_result['has_customuser_id'] and not check_result['has_user_id']:
            # 如果既没有customuser_id也没有user_id，添加customuser_id列
            cursor.execute("""
                ALTER TABLE companies_company_members
                ADD COLUMN customuser_id INTEGER NOT NULL DEFAULT 1,
                ADD CONSTRAINT companies_company_members_customuser_id_fk 
                    FOREIGN KEY (customuser_id) REFERENCES accounts_customuser(id) ON DELETE CASCADE
            """)
            print("已添加 customuser_id 列")
            
            # 添加唯一约束（如果不存在）
            if 'companies_company_members_unique' not in check_result.get('constraints', []):
                try:
                    cursor.execute("""
                        ALTER TABLE companies_company_members
                        ADD CONSTRAINT companies_company_members_unique 
                        UNIQUE (company_id, customuser_id)
                    """)
                    print("已添加唯一约束")
                except Exception as e:
                    print(f"添加唯一约束时出错: {e}")
            
            return True
            
        else:
            print("表结构正常，不需要修复")
            return False
            
    except Exception as e:
        print(f"修复表结构时出错: {e}")
        return False
    finally:
        cursor.close()

def check_company_view_code():
    """打印应修改的公司视图代码建议"""
    print("\n=== 公司视图代码修改建议 ===")
    print("在CompanyCreateView类的post方法中修改以下代码:")
    print("""
    # 修改前:
    company.members.add(request.user)
    
    # 修改后:
    try:
        # 使用原生SQL直接插入记录
        with connection.cursor() as cursor:
            cursor.execute('''
                INSERT INTO companies_company_members (company_id, customuser_id)
                VALUES (%s, %s)
                ON CONFLICT (company_id, customuser_id) DO NOTHING
            ''', [company.id, request.user.id])
    except Exception as e:
        # 如果失败，尝试使用Django ORM
        try:
            company.members.add(request.user)
        except Exception as inner_e:
            print(f"添加成员时出错: {str(inner_e)}")
    """)

def main():
    print("开始修复公司成员表结构...\n")
    
    conn = connect_db()
    if not conn:
        return
    
    try:
        check_result = check_table_structure(conn)
        if fix_table_structure(conn, check_result):
            print("\n表结构修复完成")
        
        # 检查实际的表名
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name LIKE 'companies_company_%' AND table_name != 'companies_company'
        """)
        related_tables = [row['table_name'] for row in cursor.fetchall()]
        
        if related_tables:
            print(f"\n发现相关的表: {', '.join(related_tables)}")
            print("请确保在代码中正确使用这些表名")
        
        check_company_view_code()
        
    except Exception as e:
        print(f"执行过程中出错: {e}")
    finally:
        conn.close()
        print("\n脚本执行完成")

if __name__ == "__main__":
    main() 