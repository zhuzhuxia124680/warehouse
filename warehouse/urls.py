"""
URL configuration for warehouse project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
import logging

logger = logging.getLogger('django')

def home_view(request):
    """主页视图，确保会话正确保存"""
    # 检查用户是否已登录
    is_authenticated = request.user.is_authenticated
    logger.info(f"主页访问: 用户是否登录={is_authenticated}, 用户={request.user}")
    
    # 确保会话保存
    if is_authenticated:
        request.session.save()
        logger.info("保存用户会话")
    
    # 渲染模板
    return render(request, 'home.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    # 使用自定义视图函数替代TemplateView
    path('', home_view, name='home'),
    path('accounts/', include('accounts.urls')),
    path('social/', include('social.urls')),
    path('inventory/', include('inventory.urls')),
    path('companies/', include('companies.urls')),
    # path('accounts/', include('django.contrib.auth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

