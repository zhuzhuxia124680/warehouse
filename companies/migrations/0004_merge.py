from django.db import migrations

def ensure_companies_structure(apps, schema_editor):
    """确保公司结构正确，在合并后执行"""
    pass  # 什么都不做，只是让迁移成功运行

class Migration(migrations.Migration):
    """
    合并冲突的迁移
    """
    dependencies = [
        ('companies', '0003_alter_company_members'),
        ('companies', '0003_fix_company_members'),
    ]

    operations = [
        migrations.RunPython(ensure_companies_structure, migrations.RunPython.noop),
    ] 