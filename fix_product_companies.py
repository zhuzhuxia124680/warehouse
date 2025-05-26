import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warehouse.settings')
django.setup()

from django.db import transaction
from inventory.models import Product
from companies.models import Company
from django.contrib.auth import get_user_model

User = get_user_model()

def fix_product_companies():
    # 获取所有没有关联企业的产品
    null_company_products = Product.objects.filter(company__isnull=True)
    
    if not null_company_products.exists():
        print("没有发现需要修复的产品数据")
        return
    
    print(f"发现 {null_company_products.count()} 个没有关联企业的产品")
    
    # 获取第一个超级用户
    admin_user = User.objects.filter(is_superuser=True).first()
    
    if not admin_user:
        print("错误：系统中没有超级用户")
        return
    
    # 获取或创建一个默认企业
    default_company_name = "默认企业"
    default_company, created = Company.objects.get_or_create(
        name=default_company_name,
        defaults={
            'owner': admin_user
        }
    )
    
    if created:
        print(f"创建了默认企业：{default_company_name}")
        # 将创建者添加为企业成员
        default_company.members.add(admin_user)
    
    # 开始处理产品数据
    with transaction.atomic():
        updated_count = 0
        for product in null_company_products:
            product.company = default_company
            product.save()
            updated_count += 1
            print(f"已更新产品：{product.name}")
        
        print(f"\n成功更新了 {updated_count} 个产品的企业关联")

if __name__ == '__main__':
    fix_product_companies() 