from django.db import migrations

def update_company_members(apps, schema_editor):
    Company = apps.get_model('companies', 'Company')
    User = apps.get_model('accounts', 'CustomUser')
    
    # 手动创建多对多关系
    for company in Company.objects.all():
        # 使用正确的字段名（根据模型实际关系）
        company.members.clear()  # 清除现有关系
        
        # 添加拥有者为成员（如果需要）
        if company.owner:
            company.members.add(company.owner)

class Migration(migrations.Migration):
    dependencies = [
        ('companies', '0004_merge'),
    ]

    operations = [
        migrations.RunPython(update_company_members, migrations.RunPython.noop),
    ] 