#!/usr/bin/env python
"""
修复社交应用外键约束脚本

使用方法:
1. 确保已安装psycopg2-binary: pip install psycopg2-binary
2. 运行 python fix_social_foreignkeys.py
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

def fix_social_foreignkeys():
    """修复社交应用的外键约束"""
    print("开始修复社交应用的外键约束...")
    
    try:
        # 连接到PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # 1. 查找现有的外键约束
        print("\n1. 查找现有的外键约束...")
        cursor.execute("""
            SELECT tc.constraint_name, kcu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name = 'social_friendship'
              AND kcu.column_name IN ('from_user_id', 'to_user_id')
              AND tc.table_schema = 'public'
        """)
        
        constraints = cursor.fetchall()
        if constraints:
            print(f"找到 {len(constraints)} 个外键约束:")
            for constraint in constraints:
                print(f"- {constraint['constraint_name']} ({constraint['column_name']})")
        else:
            print("未找到任何外键约束")
        
        # 2. 删除现有的外键约束
        print("\n2. 删除现有的外键约束...")
        for constraint in constraints:
            constraint_name = constraint['constraint_name']
            try:
                cursor.execute(f"""
                    ALTER TABLE social_friendship
                    DROP CONSTRAINT IF EXISTS {constraint_name}
                """)
                print(f"已删除约束: {constraint_name}")
            except Exception as e:
                print(f"删除约束 {constraint_name} 时出错: {str(e)}")
        
        # 如果没有找到约束，尝试使用硬编码的约束名
        if not constraints:
            try:
                cursor.execute("""
                    ALTER TABLE social_friendship
                    DROP CONSTRAINT IF EXISTS social_friendship_from_user_id_2d2e1d03_fk_auth_user_id
                """)
                print("已尝试删除 from_user_id 约束")
                
                cursor.execute("""
                    ALTER TABLE social_friendship
                    DROP CONSTRAINT IF EXISTS social_friendship_to_user_id_f9cc5e4b_fk_auth_user_id
                """)
                print("已尝试删除 to_user_id 约束")
            except Exception as e:
                print(f"删除硬编码约束时出错: {str(e)}")
        
        # 3. 添加新的外键约束
        print("\n3. 添加新的外键约束到accounts_customuser表...")
        try:
            cursor.execute("""
                ALTER TABLE social_friendship
                ADD CONSTRAINT social_friendship_from_user_id_fk
                FOREIGN KEY (from_user_id) REFERENCES accounts_customuser(id) ON DELETE CASCADE
            """)
            print("已添加 from_user_id 约束")
            
            cursor.execute("""
                ALTER TABLE social_friendship
                ADD CONSTRAINT social_friendship_to_user_id_fk
                FOREIGN KEY (to_user_id) REFERENCES accounts_customuser(id) ON DELETE CASCADE
            """)
            print("已添加 to_user_id 约束")
        except Exception as e:
            print(f"添加新约束时出错: {str(e)}")
        
        # 4. 验证约束是否正确添加
        print("\n4. 验证约束是否正确添加...")
        cursor.execute("""
            SELECT tc.constraint_name, kcu.column_name, ccu.table_name AS referenced_table
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name = 'social_friendship'
              AND tc.table_schema = 'public'
        """)
        
        new_constraints = cursor.fetchall()
        if new_constraints:
            print(f"找到 {len(new_constraints)} 个新的外键约束:")
            for constraint in new_constraints:
                print(f"- {constraint['constraint_name']} ({constraint['column_name']}) -> {constraint['referenced_table']}")
        else:
            print("未找到任何新的外键约束，修复可能失败")
        
        cursor.close()
        conn.close()
        
        print("\n修复完成！请重新启动Django服务器。")
        
    except Exception as e:
        print(f"执行过程中出错: {str(e)}")

if __name__ == "__main__":
    fix_social_foreignkeys() 