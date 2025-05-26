-- 修复社交应用的外键约束脚本
-- 使用方法: 在PostgreSQL命令行中执行此脚本

-- 1. 先查找并删除原有的外键约束
SELECT tc.constraint_name, kcu.column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name = 'social_friendship'
  AND kcu.column_name IN ('from_user_id', 'to_user_id')
  AND tc.table_schema = 'public';

-- 删除 from_user_id 约束
ALTER TABLE social_friendship
DROP CONSTRAINT IF EXISTS social_friendship_from_user_id_2d2e1d03_fk_auth_user_id;

-- 删除 to_user_id 约束
ALTER TABLE social_friendship
DROP CONSTRAINT IF EXISTS social_friendship_to_user_id_f9cc5e4b_fk_auth_user_id;

-- 2. 添加新的外键约束到accounts_customuser表
ALTER TABLE social_friendship
ADD CONSTRAINT social_friendship_from_user_id_fk
FOREIGN KEY (from_user_id) REFERENCES accounts_customuser(id) ON DELETE CASCADE;

ALTER TABLE social_friendship
ADD CONSTRAINT social_friendship_to_user_id_fk
FOREIGN KEY (to_user_id) REFERENCES accounts_customuser(id) ON DELETE CASCADE;

-- 3. 验证约束是否正确添加
SELECT tc.constraint_name, kcu.column_name, ccu.table_name AS referenced_table
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON tc.constraint_name = ccu.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name = 'social_friendship'
  AND tc.table_schema = 'public'; 