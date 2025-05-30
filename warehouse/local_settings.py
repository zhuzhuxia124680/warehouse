"""
本地开发设置，不会被Git跟踪
当需要切换到SQLite时取消注释这部分
"""
from pathlib import Path

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 使用SQLite进行临时测试
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

#邮箱设置
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.163.com'
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_HOST_USER = 'xxx@163.com'
# 注意：这里应该使用163邮箱的授权码，不是登录密码
# 如果发送失败，请确保已在163邮箱设置中开启SMTP服务并获取正确的授权码
EMAIL_HOST_PASSWORD = 'xxx'
DEFAULT_FROM_EMAIL = 'xxx@163.com'
