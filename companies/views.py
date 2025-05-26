from django.shortcuts import render,redirect,get_object_or_404
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import CreateView, DeleteView, DetailView
from django.db import connection

from .models import Company
from .forms import CompanyForm, JoinCompanyForm

class CompanyListView(LoginRequiredMixin, View):
    """公司列表视图，需要用户登录"""
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    
    def get(self, request):
        try:
            # 获取用户拥有的公司
            owned_companies = Company.objects.filter(owner=request.user)
            
            # 避开中间表查询，直接使用原始SQL
            # 创建空列表存储结果
            joined_companies = []
            
            with connection.cursor() as cursor:
                # 尝试使用不同的表名查询
                try:
                    # 查询用户参与的公司（非拥有者）
                    cursor.execute("""
                        SELECT c.id, c.name, c.created_at 
                        FROM companies_company c
                        INNER JOIN companies_company_members m ON c.id = m.company_id
                        WHERE m.customuser_id = %s AND c.owner_id != %s
                    """, [request.user.id, request.user.id])
                    
                    # 获取所有结果
                    rows = cursor.fetchall()
                    
                    # 创建Company对象
                    for row in rows:
                        company = Company(
                            id=row[0],
                            name=row[1],
                            created_at=row[2]
                        )
                        joined_companies.append(company)
                        
                except Exception as e:
                    # 如果第一次查询失败，尝试另一种表名
                    try:
                        cursor.execute("""
                            SELECT c.id, c.name, c.created_at 
                            FROM companies_company c
                            INNER JOIN companies_company_accounts_customuser m ON c.id = m.company_id
                            WHERE m.customuser_id = %s AND c.owner_id != %s
                        """, [request.user.id, request.user.id])
                        
                        # 获取所有结果
                        rows = cursor.fetchall()
                        
                        # 创建Company对象
                        for row in rows:
                            company = Company(
                                id=row[0],
                                name=row[1],
                                created_at=row[2]
                            )
                            joined_companies.append(company)
                    except Exception as inner_e:
                        # 如果两种查询都失败，我们使用空列表
                        pass
            
            # 创建加入公司的表单
            form = JoinCompanyForm()
            
            context = {
                'owned_companies': owned_companies,
                'joined_companies': joined_companies,
                'join_form': form,
                'page_title': '公司管理',
            }
            
            return render(request, 'companies/company_list.html', context)
        except Exception as e:
            messages.error(request, f'加载公司列表时出错: {str(e)}')
            return render(request, 'companies/company_list.html', {'error': True})
    
    def post(self, request):
        form = JoinCompanyForm(request.POST)
        if form.is_valid():
            company_name = form.cleaned_data['company_name']
            try:
                company = Company.objects.get(name=company_name)
                
                # 检查用户是否已经是成员或拥有者
                is_owner = company.owner == request.user
                
                # 使用SQL检查是否已经是成员
                is_member = False
                with connection.cursor() as cursor:
                    try:
                        # 尝试使用companies_company_members表
                        cursor.execute("""
                            SELECT COUNT(*) FROM companies_company_members 
                            WHERE company_id = %s AND customuser_id = %s
                        """, [company.id, request.user.id])
                        count = cursor.fetchone()[0]
                        is_member = count > 0
                    except Exception:
                        try:
                            # 尝试使用companies_company_accounts_customuser表
                            cursor.execute("""
                                SELECT COUNT(*) FROM companies_company_accounts_customuser 
                                WHERE company_id = %s AND customuser_id = %s
                            """, [company.id, request.user.id])
                            count = cursor.fetchone()[0]
                            is_member = count > 0
                        except Exception:
                            # 两种表都不存在，假定不是成员
                            is_member = False
                
                if is_owner or is_member:
                    messages.info(request, f'您已经是"{company_name}"公司的成员或拥有者')
                else:
                    # 使用SQL添加用户为成员
                    with connection.cursor() as cursor:
                        try:
                            # 先尝试使用companies_company_members表
                            cursor.execute("""
                                INSERT INTO companies_company_members (company_id, customuser_id)
                                VALUES (%s, %s)
                            """, [company.id, request.user.id])
                            messages.success(request, f'成功加入{company_name}公司')
                        except Exception:
                            try:
                                # 尝试使用companies_company_accounts_customuser表
                                cursor.execute("""
                                    INSERT INTO companies_company_accounts_customuser (company_id, customuser_id)
                                    VALUES (%s, %s)
                                """, [company.id, request.user.id])
                                messages.success(request, f'成功加入{company_name}公司')
                            except Exception as e:
                                # 如果两者都失败，报错
                                messages.error(request, f'加入公司时出错: {str(e)}')
            except Company.DoesNotExist:
                messages.error(request, f'找不到名为"{company_name}"的公司')
        else:
            messages.error(request, '表单验证失败，请检查输入内容')
            
        return redirect('companies:company_list')

class CompanyCreateView(LoginRequiredMixin, View):
    """创建新公司视图，需要用户登录"""
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    
    def get(self, request):
        form = CompanyForm()
        return render(request, 'companies/company_create.html', {
            'form': form,
            'page_title': '创建新公司',
        })
    
    def post(self, request):
        form = CompanyForm(request.POST)
        if form.is_valid():
            try:
                company = form.save(commit=False)
                company.owner = request.user
                company.save()
                
                # 创建者自动成为公司成员 - 修改使用原生SQL
                try:
                    # 使用原生SQL直接插入记录
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO companies_company_members (company_id, customuser_id)
                            VALUES (%s, %s)
                        """, [company.id, request.user.id])
                except Exception as e:
                    # 如果失败，尝试使用Django ORM
                    try:
                        company.members.add(request.user)
                    except Exception as inner_e:
                        messages.warning(request, f"将您添加为公司成员时出错，但公司创建成功。您可以稍后再试。")
                
                messages.success(request, f'公司"{company.name}"创建成功')
                return redirect('companies:company_list')
            except Exception as e:
                messages.error(request, f'创建公司时出错: {str(e)}')
        
        return render(request, 'companies/company_create.html', {'form': form})

class CompanyDeleteView(LoginRequiredMixin, View):
    """删除公司视图，需要用户登录，且只有拥有者可以删除"""
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    
    def get(self, request, pk):
        company = get_object_or_404(Company, pk=pk)
        
        # 验证用户是否是公司拥有者
        if company.owner != request.user:
            messages.error(request, "您不是公司拥有者，无权删除此公司")
            return redirect('companies:company_list')
            
        return render(request, 'companies/company_confirm_delete.html', {
            'company': company,
            'page_title': '确认删除公司',
        })
    
    def post(self, request, pk):
        company = get_object_or_404(Company, pk=pk)
        
        # 验证用户是否是公司拥有者
        if company.owner != request.user:
            messages.error(request, "您不是公司拥有者，无权删除此公司")
            return redirect('companies:company_list')
            
        company_name = company.name
        
        try:
            # 先尝试使用原生SQL删除公司成员关系
            with connection.cursor() as cursor:
                try:
                    cursor.execute("""
                        DELETE FROM companies_company_members
                        WHERE company_id = %s
                    """, [company.id])
                except Exception as e:
                    # 忽略错误，继续尝试删除公司
                    pass
            
            # 删除公司
            company.delete()
            messages.success(request, f'公司"{company_name}"已成功删除')
        except Exception as e:
            messages.error(request, f'删除公司时出错: {str(e)}')
        
        return redirect('companies:company_list')

class CompanyDetailView(LoginRequiredMixin, View):
    """企业详情视图，显示企业信息和库存列表"""
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    
    def get(self, request, pk):
        company = get_object_or_404(Company, pk=pk)
        
        # 检查用户是否有权限查看（是企业所有者或成员）
        if company.owner != request.user and request.user not in company.members.all():
            messages.error(request, "您没有权限查看此企业信息")
            return redirect('companies:company_list')
        
        # 获取企业的库存产品
        products = company.products.all()
        
        context = {
            'company': company,
            'products': products,
            'page_title': f'{company.name} - 企业详情',
        }
        
        return render(request, 'companies/company_detail.html', context)