-- 修复公司成员表结构脚本
-- 使用方法: 在PostgreSQL命令行中执行此脚本

-- 检查并删除错误的表（如果存在）
DROP TABLE IF EXISTS companies_company_members;

-- 创建新的公司成员表
CREATE TABLE companies_company_members (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    customuser_id INTEGER NOT NULL,
    CONSTRAINT companies_company_members_company_id_fk 
        FOREIGN KEY (company_id) REFERENCES companies_company(id) ON DELETE CASCADE,
    CONSTRAINT companies_company_members_customuser_id_fk 
        FOREIGN KEY (customuser_id) REFERENCES accounts_customuser(id) ON DELETE CASCADE,
    CONSTRAINT companies_company_members_unique UNIQUE (company_id, customuser_id)
);

-- 添加所有公司创建者作为其公司的成员
INSERT INTO companies_company_members (company_id, customuser_id)
SELECT id, owner_id FROM companies_company
WHERE owner_id IS NOT NULL
ON CONFLICT (company_id, customuser_id) DO NOTHING;

-- 打印表结构
\d+ companies_company_members 