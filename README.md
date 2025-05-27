# 仓库管理平台

一个现代化的仓库管理系统，帮助企业高效管理库存、连接上下游企业，提升业务效率。

## 功能特性

### 1. 库存管理
- 产品信息管理（名称、描述、价格、数量等）
- 实时库存监控
- 高级筛选功能（价格范围、库存范围、采购人等）
- 多维度排序（创建时间、名称、价格、库存等）
- 库存数据导出（Excel格式）

### 2. 企业协作
- 企业信息管理
- 多企业支持
- 企业成员管理
- 权限控制系统

### 3. 用户系统
- 用户认证与授权
- 个人资料管理
- 好友系统
- 采购人管理

### 4. 数据分析
- 库存统计
- 价值计算
- 数据可视化
- 智能报表

## 技术栈

### 后端
- Python
- Django
- PostgreSQL

### 前端
- HTML5
- CSS3
- JavaScript
- Bootstrap 4.6.2
- jQuery 3.6.0
- Font Awesome 5.15.4

## 安装说明

1. 克隆项目
```bash
git clone https://github.com/zhuzhuxia124680/warehouse.git
cd warehouse
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 数据库迁移
```bash
python manage.py makemigrations
python manage.py migrate
```

5. 创建超级用户
```bash
python manage.py createsuperuser
```

6. 运行开发服务器
```bash
python manage.py runserver
```

## 使用说明

### 1. 基本操作
- 访问 http://localhost:8000 进入系统
- 使用超级用户账号登录
- 在"企业管理"中创建企业
- 在"库存管理"中添加产品

### 2. 产品管理
- 添加新产品：填写产品信息（名称、价格、数量等）
- 编辑产品：修改产品信息
- 删除产品：从库存中移除产品
- 导出数据：将产品列表导出为Excel文件

### 3. 高级功能
- 使用高级筛选：按价格范围、库存范围、采购人等筛选产品
- 排序功能：按不同维度对产品进行排序
- 数据统计：查看库存总价值等统计信息

## 注意事项

1. 首次使用需要创建企业并设置相应权限
2. 建议定期备份数据
3. 请妥善保管管理员账号信息

## 许可证

© 2025 仓库管理平台. 保留所有权利。 