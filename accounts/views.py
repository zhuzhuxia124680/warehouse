import string
import logging
import smtplib
import ssl
from datetime import timedelta

from django.shortcuts import render,redirect
from django.urls import reverse_lazy
from django.views import View
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import caches #使用已定义的缓存
from django.contrib import messages
from .forms import CustomUserCreationForm, LoginForm, EmailVerificationForm, LoginByCodeForm
from .models import CustomUser, EmailVerification
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.mixins import LoginRequiredMixin

# 配置日志记录
logger = logging.getLogger(__name__)

# 避免重复添加处理程序
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

email_code_cache = caches['email_codes'] #邮箱码的缓存

def send_verification_email(user, code):
    try:
        subject = '验证码'
        message = f'你的验证码是：{code}。\n该代码有效期为10分钟。'
        email_from = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]
        
        logger.info(f"准备发送邮件: 从 {email_from} 到 {user.email}, 主题: {subject}")
        logger.info(f"邮件服务器信息: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}, SSL: {settings.EMAIL_USE_SSL}")
        
        # 尝试直接连接到SMTP服务器进行测试
        try:
            logger.info("测试SMTP连接...")
            if settings.EMAIL_USE_SSL:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT, context=context) as server:
                    server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                    logger.info("SMTP连接测试成功 (SSL)")
            else:
                with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                    server.starttls()
                    server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                    logger.info("SMTP连接测试成功 (TLS)")
        except Exception as smtp_test_error:
            logger.error(f"SMTP连接测试失败: {str(smtp_test_error)}", exc_info=True)
            # 我们只记录错误，但继续尝试发送邮件
        
        # 实际发送邮件
        result = send_mail(subject, message, email_from, recipient_list, fail_silently=False)
        logger.info(f"邮件发送结果: {result} 封邮件已发送")
        return True
    except Exception as e:
        logger.error(f"发送验证码邮件失败: {str(e)}", exc_info=True)
        return False

def check_cache_availability():
    try:
        email_code_cache.set('test_key', 'test_value', timeout=1)
        email_code_cache.get('test_key')
        return True
    except Exception as e:
        logger.error(f"缓存服务不可用: {str(e)}")
        return False

def generate_and_save_verification_code(user):
    """生成验证码并保存到缓存和数据库"""
    try:
        # 生成验证码
        code = get_random_string(length=6, allowed_chars='0123456789')
        logger.info(f"为用户 {user.email} 生成新验证码: {code}")
        
        # 保存到缓存
        cache_key = f'email_verification_code:{user.email}'
        email_code_cache.set(cache_key, code, timeout=600)  # 10分钟有效期
        
        # 保存到数据库
        verification = EmailVerification.objects.create(
            user=user,
            code=code,
            expiry_at=timezone.now() + timedelta(minutes=10)
        )
        
        logger.info(f"验证码已保存, 缓存键: {cache_key}, 数据库ID: {verification.id}")
        return code
    except Exception as e:
        logger.error(f"生成或保存验证码失败: {str(e)}", exc_info=True)
        return None

class RegisterView(View):
    def get(self,request):
        form = CustomUserCreationForm()
        return render(request, 'registration/register.html', {'form':form})

    def post(self, request):
        logger.info(f"收到注册请求: {request.POST.get('email')}")
        form = CustomUserCreationForm(request.POST)
        
        # 打印表单验证错误以便调试
        if not form.is_valid():
            logger.warning(f"表单验证失败：{form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            return render(request, 'registration/register.html', {'form': form})
        
        try:
            email = form.cleaned_data['email']
            logger.info(f"注册邮箱: {email}")
            
            if CustomUser.objects.filter(email=email).exists():
                logger.warning(f"邮箱已被注册: {email}")
                messages.error(request, '该邮箱已被注册')
                return render(request, 'registration/register.html', {'form': form})
            
            # 检查Redis缓存是否可用
            if not check_cache_availability():
                logger.error("缓存服务不可用，无法发送验证码")
                messages.error(request, '系统缓存服务不可用，请联系管理员')
                return render(request, 'registration/register.html', {'form': form})
            
            # 保存用户
            try:
                user = form.save(commit=False)
                user.is_active = False  # 未验证前不激活
                user.save()
                logger.info(f"成功创建用户: {user.id}, {user.email}")
            except Exception as e:
                logger.error(f"保存用户失败: {str(e)}", exc_info=True)
                messages.error(request, f'创建用户失败: {str(e)}')
                return render(request, 'registration/register.html', {'form': form})
            
            # 生成并保存验证码
            code = generate_and_save_verification_code(user)
            if not code:
                messages.error(request, '生成验证码失败，请稍后重试')
                return render(request, 'registration/register.html', {'form': form})
            
            # 发送验证邮件
            if send_verification_email(user, code):
                logger.info(f"验证码邮件发送成功: {email}")
                messages.success(request, '验证码已发送到您的邮箱')
                # 将邮箱保存到session中以便在验证页面使用
                request.session['login_email'] = email
                return redirect('accounts:verify_email_with_email')
            else:
                logger.error(f"验证码邮件发送失败: {email}")
                messages.error(request, '验证码发送失败，请稍后重试')
                return render(request, 'registration/register.html', {'form': form})
        except Exception as e:
            logger.error(f"注册过程出错: {str(e)}", exc_info=True)
            messages.error(request, f'注册过程出现错误: {str(e)}')
            return render(request, 'registration/register.html', {'form': form})

class RegisterDoneView(View):
    def get(self,request):
        return render(request,'registration/register_done.html')

class VerifyEmailView(View):
    def get(self,request):
        form = EmailVerificationForm()
        return render(request,'registration/verify_email.html',{'form':form})
    def post(self,request):
        form = EmailVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            return redirect('accounts:verify_email_with_email') #转到需要邮箱和验证码的页面
        return render(request,'registration/verify_email.html',{'form':form})

class VerifyEmailWithEmailView(View):
    def get(self, request):
        initial_data = {}
        if 'login_email' in request.session:
            initial_data['email'] = request.session.get('login_email')
            logger.info(f"从session获取验证邮箱: {initial_data['email']}")
            
        form = LoginByCodeForm(initial=initial_data)
        return render(request, 'accounts/verify_email_with_email.html', {'form': form})
        
    def post(self, request):
        form = LoginByCodeForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            code = form.cleaned_data['code']
            logger.info(f"收到验证请求，邮箱: {email}, 验证码: {code}")
            
            try:
                user = CustomUser.objects.get(email=email, is_active=False)
                logger.info(f"找到未激活用户: {user.id}, {user.email}")
            except CustomUser.DoesNotExist:
                logger.warning(f"找不到未激活用户，邮箱: {email}")
                messages.error(request, '无效电子邮箱或用户已激活')
                return render(request, 'accounts/verify_email_with_email.html', {'form': form})

            # 首先从缓存中获取验证码
            cache_key = f'email_verification_code:{user.email}'
            cached_code = email_code_cache.get(cache_key)
            logger.info(f"从缓存获取验证码结果: {cached_code}")
            
            # 如果缓存中没有验证码，尝试从数据库获取
            if not cached_code:
                logger.info(f"缓存中没有验证码，尝试从数据库获取")
                verification_entry = EmailVerification.objects.filter(
                    user=user,
                    is_used=False,
                    expiry_at__gte=timezone.now()
                ).order_by('-expiry_at').first()
                
                if not verification_entry:
                    logger.warning(f"数据库中没有找到有效的验证码记录")
                    messages.error(request, '验证码已过期，请重新获取')
                    return render(request, 'accounts/verify_email_with_email.html', {'form': form})
                
                cached_code = verification_entry.code
                logger.info(f"从数据库获取到验证码: {cached_code}")
            
            if cached_code == code:
                logger.info(f"验证码匹配成功，激活用户: {user.email}")
                # 激活用户
                user.is_active = True
                user.save()
                
                # 更新验证记录
                verification_entry = EmailVerification.objects.filter(
                    user=user,
                    code=code,
                    is_used=False,
                    expiry_at__gte=timezone.now()
                ).order_by('-expiry_at').first()
                
                if verification_entry:
                    verification_entry.is_used = True
                    verification_entry.save()
                    logger.info(f"更新验证记录状态为已使用: {verification_entry.id}")
                
                # 清除缓存中的验证码
                email_code_cache.delete(cache_key)
                logger.info(f"从缓存中删除验证码: {cache_key}")
                
                # 自动登录用户
                login(request, user)
                logger.info(f"用户自动登录成功: {user.email}")
                
                # 清除session中的邮箱
                if 'login_email' in request.session:
                    del request.session['login_email']
                    logger.info("从session中删除login_email")
                
                messages.success(request, '邮箱验证成功，您已登录')
                return redirect(settings.LOGIN_REDIRECT_URL)
            else:
                logger.warning(f"验证码不匹配, 预期: {cached_code}, 实际输入: {code}")
                messages.error(request, '验证码不正确')
        else:
            logger.warning(f"表单验证失败: {form.errors}")
        return render(request, 'accounts/verify_email_with_email.html', {'form': form})

class LoginView(DjangoLoginView):
    template_name = 'registration/login.html'
    authentication_form = LoginForm
    redirect_field_name = 'next'
    
    def get_success_url(self):
        """获取登录成功后的跳转URL"""
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return settings.LOGIN_REDIRECT_URL
    
    def form_valid(self, form):
        """表单验证成功时的处理"""
        # 获取用户
        user = form.get_user()
        
        # 登录用户
        login(self.request, user)
        logger.info(f"用户登录成功: {user.email}")
        
        # 确保会话已保存
        self.request.session.save()
        
        # 添加登录成功消息
        messages.success(self.request, '登录成功！')
        
        # 跳转到成功页面
        return super().form_valid(form)
    
    def post(self, request, *args, **kwargs):
        """处理POST请求，包括表单验证和用户认证"""
        # 获取并验证表单
        form = self.get_form()
        logger.info("处理登录表单提交")
        
        if form.is_valid():
            logger.info("登录表单验证通过")
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # 获取用户并检查状态
            user = form.get_user()
            
            if user and user.is_active:
                logger.info(f"用户有效并已激活: {username}")
                # 使用authenticate进行再次验证
                authenticated_user = authenticate(request, username=username, password=password)
                
                if authenticated_user:
                    # 登录用户
                    login(request, authenticated_user)
                    logger.info(f"用户认证并登录成功: {username}")
                    
                    # 确保会话已保存
                    request.session.save()
                    
                    # 添加成功消息
                    messages.success(request, '登录成功！')
                    
                    # 重定向到成功页面
                    redirect_to = self.get_success_url()
                    logger.info(f"重定向到: {redirect_to}")
                    return redirect(redirect_to)
                else:
                    logger.warning(f"用户认证失败: {username}")
                    messages.error(request, '用户名或密码错误')
            elif user and not user.is_active:
                logger.warning(f"用户未激活: {username}")
                messages.error(request, '账号未激活，请检查您的邮箱')
                return redirect('accounts:verify_email_with_email')
            else:
                logger.warning(f"登录失败，用户无效: {username}")
                messages.error(request, '用户名或密码错误')
        else:
            logger.warning(f"登录表单验证失败: {form.errors}")
            messages.error(request, '请检查输入的信息')
        
        # 如果登录失败，返回表单页面
        return self.form_invalid(form)

class LoginByCodeView(View):
    def get(self, request):
        # 如果session中有email，使用它初始化表单
        initial_data = {}
        if 'login_email' in request.session:
            initial_data['email'] = request.session.get('login_email')
            logger.info(f"从session获取邮箱: {initial_data['email']}")
            
        form = LoginByCodeForm(initial=initial_data)
        return render(request, 'accounts/login_by_code.html', {'form': form})
    
    def post(self, request):
        form = LoginByCodeForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            code = form.cleaned_data['code']
            logger.info(f"验证码登录请求: 邮箱={email}, 验证码={code}")
            
            try:
                user = CustomUser.objects.get(email=email, is_active=True)
                logger.info(f"找到激活用户: {user.id}, {user.email}")
            except CustomUser.DoesNotExist:
                logger.warning(f"找不到激活用户，邮箱: {email}")
                messages.error(request, '邮箱非法或账号未激活')
                return render(request, 'accounts/login_by_code.html', {'form': form})
            
            # 首先从缓存中获取验证码
            cache_key = f'email_verification_code:{user.email}'
            cached_code = email_code_cache.get(cache_key)
            logger.info(f"从缓存中获取验证码: {cached_code}")
            
            # 如果缓存中没有验证码，尝试从数据库获取
            db_code_valid = False
            if not cached_code:
                logger.info(f"缓存中没有验证码，尝试从数据库获取")
                verification_entry = EmailVerification.objects.filter(
                    user=user,
                    is_used=False,
                    expiry_at__gte=timezone.now()
                ).order_by('-expiry_at').first()
                
                if verification_entry and verification_entry.code == code:
                    logger.info(f"从数据库验证码验证成功")
                    db_code_valid = True
                    verification_entry.is_used = True
                    verification_entry.save()
            
            # 验证码正确 - 缓存或数据库
            if (cached_code and cached_code == code) or db_code_valid:
                logger.info(f"验证码验证成功")
                
                # 清除缓存中的验证码
                if cached_code:
                    email_code_cache.delete(cache_key)
                    logger.info(f"从缓存中删除验证码: {cache_key}")
                
                # 清除session中的邮箱
                if 'login_email' in request.session:
                    del request.session['login_email']
                
                # 登录用户
                login(request, user)
                logger.info(f"用户登录成功: {user.email}")
                
                # 确保会话已保存
                request.session.save()
                
                # 添加用户信息到会话
                request.session['user_id'] = user.id
                request.session['email'] = user.email
                
                messages.success(request, '成功使用验证码登录。')
                redirect_to = settings.LOGIN_REDIRECT_URL
                logger.info(f"重定向到: {redirect_to}")
                return redirect(redirect_to)
            else:
                logger.warning(f"验证码不匹配, 邮箱: {email}")
                messages.error(request, '验证码非法或已过期')
        else:
            logger.warning(f"表单验证失败: {form.errors}")
            messages.error(request, '请检查输入的信息')
            
        return render(request, 'accounts/login_by_code.html', {'form': form})

class RequestLoginCodeView(View):
    def get(self,request):
        return render(request,'accounts/request_login_code.html')
    def post(self,request):
        email = request.POST.get('email')
        logger.info(f"接收到验证码请求，邮箱：{email}")
        
        if not email:
            logger.warning("用户未提供邮箱地址")
            messages.error(request, '请提供你的邮箱。')
            return render(request,'accounts/request_login_code.html')
        
        # 检查缓存服务是否可用
        if not check_cache_availability():
            logger.error("缓存服务不可用，无法存储验证码")
            messages.error(request, '系统缓存服务不可用，请联系管理员或使用密码登录')
            return render(request,'accounts/request_login_code.html')
            
        try:
            user = CustomUser.objects.get(email=email, is_active=True)
            logger.info(f"用户存在且已激活: {email}")
        except CustomUser.DoesNotExist:
            logger.warning(f"邮箱不存在或用户未激活: {email}")
            messages.error(request, '这个用户的邮箱不存在或未注册')
            return render(request,'accounts/request_login_code.html')
            
        # 生成验证码
        code = get_random_string(length=6, allowed_chars='0123456789')
        logger.info(f"为用户 {email} 生成验证码: {code}")
        cache_key = f'email_verification_code:{user.email}'
        
        try:
            # 存储到缓存
            email_code_cache.set(cache_key, code, timeout=300)
            logger.info(f"验证码已存储到缓存，键: {cache_key}")
            
            # 同时保存到数据库作为备份
            verification = EmailVerification.objects.create(
                user=user,
                code=code,
                expiry_at=timezone.now() + timedelta(minutes=5)
            )
            logger.info(f"验证码已存储到数据库，ID: {verification.id}")

            # 发送邮件
            if send_verification_email(user, code):
                logger.info(f"邮件发送成功，跳转到验证码登录页面")
                
                # 设置会话变量以在登录页面回显邮箱
                request.session['login_email'] = email
                
                messages.success(request, f'验证码已发送到 {email}')
                return redirect('accounts:login_by_code')
            else:
                logger.error("发送邮件失败")
                messages.error(request, '验证码发送失败，请稍后重试或使用密码登录')
                return render(request,'accounts/request_login_code.html')
        except Exception as e:
            logger.error(f"验证码流程出错: {str(e)}", exc_info=True)
            messages.error(request, f'验证码发送失败: {str(e)}，请稍后重试或使用密码登录')
            return render(request,'accounts/request_login_code.html')

class ProfileView(View):
    def get(self,request):
        return render(request, 'accounts/profile.html',{'user':request.user})

class ResendVerificationCodeView(View):
    def post(self, request):
        email = request.POST.get('email')
        logger.info(f"收到重新发送验证码请求，邮箱: {email}")
        
        if not email:
            logger.warning("未提供邮箱地址")
            messages.error(request, '请提供您的邮箱地址')
            return redirect('accounts:verify_email_with_email')
        
        try:
            # 检查用户是否存在
            user = CustomUser.objects.get(email=email)
            
            # 生成新验证码
            code = generate_and_save_verification_code(user)
            if not code:
                messages.error(request, '生成验证码失败，请稍后重试')
                return redirect('accounts:verify_email_with_email')
            
            # 发送邮件
            if send_verification_email(user, code):
                logger.info(f"重新发送验证码成功: {email}")
                messages.success(request, f'新的验证码已发送到 {email}，请查收')
            else:
                logger.error(f"重新发送验证码失败: {email}")
                messages.error(request, '验证码发送失败，请稍后重试')
            
            # 保存邮箱到session
            request.session['login_email'] = email
            
            return redirect('accounts:verify_email_with_email')
        except CustomUser.DoesNotExist:
            logger.warning(f"请求重发验证码的邮箱不存在: {email}")
            messages.error(request, '此邮箱未注册')
            return redirect('accounts:verify_email_with_email')
        except Exception as e:
            logger.error(f"重发验证码过程出错: {str(e)}", exc_info=True)
            messages.error(request, f'验证码发送失败: {str(e)}')
            return redirect('accounts:verify_email_with_email')

class LogoutView(LoginRequiredMixin, View):
    """自定义的登出视图"""
    login_url = '/accounts/login/'
    
    def get(self, request):
        logger.info(f"用户 {request.user.email} 请求登出")
        try:
            # 清除特定的会话数据
            if 'login_email' in request.session:
                del request.session['login_email']
            
            # 使用Django的logout函数
            logout(request)
            
            # 手动设置会话过期
            request.session.flush()
            
            # 添加成功消息
            messages.success(request, "您已成功退出登录")
            logger.info("用户登出成功，会话已清除")
            
            # 重定向到首页
            return redirect('home')
        except Exception as e:
            logger.error(f"登出时出错: {str(e)}", exc_info=True)
            messages.error(request, "登出过程中出现错误，请稍后再试")
            return redirect('home')
