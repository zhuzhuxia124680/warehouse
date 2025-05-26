from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from .models import Product
from .forms import ProductForm
from companies.models import Company
from django.db import models
from django.db.models import Q, Sum, F
from django.contrib.auth import get_user_model
import pandas as pd
from django.http import HttpResponse, JsonResponse
from datetime import datetime

class OwnerRequiredMixin(LoginRequiredMixin):
    """确保用户已登录，并且只能访问自己的资源"""
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    
    def get_queryset(self):
        """根据当前用户过滤查询集"""
        return super().get_queryset()  # 在实际场景中应该基于用户过滤

class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'
    login_url = '/accounts/login/'
    paginate_by = 10  # 每页显示10条记录
    
    def get_queryset(self):
        """获取筛选和排序后的产品列表"""
        user = self.request.user
        queryset = Product.objects.select_related('company', 'purchaser').filter(
            Q(company__owner=user) | Q(company__members=user)
        ).distinct()
        
        # 搜索过滤
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
            
        # 价格范围过滤
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
            
        # 库存数量过滤
        min_quantity = self.request.GET.get('min_quantity')
        max_quantity = self.request.GET.get('max_quantity')
        if min_quantity:
            queryset = queryset.filter(quantity__gte=min_quantity)
        if max_quantity:
            queryset = queryset.filter(quantity__lte=max_quantity)
            
        # 采购人筛选
        purchaser_id = self.request.GET.get('purchaser')
        if purchaser_id:
            queryset = queryset.filter(purchaser_id=purchaser_id)
            
        # 排序
        sort_by = self.request.GET.get('sort_by', '-created_by')  # 默认按创建时间倒序
        if sort_by in ['name', '-name', 'price', '-price', 'quantity', '-quantity', 'created_by', '-created_by']:
            queryset = queryset.order_by(sort_by)
            
        return queryset
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 添加筛选和排序的当前值到上下文
        context['current_sort'] = self.request.GET.get('sort_by', '-created_by')
        context['search_query'] = self.request.GET.get('search', '')
        context['min_price'] = self.request.GET.get('min_price', '')
        context['max_price'] = self.request.GET.get('max_price', '')
        context['min_quantity'] = self.request.GET.get('min_quantity', '')
        context['max_quantity'] = self.request.GET.get('max_quantity', '')
        
        # 添加采购人列表到上下文
        User = get_user_model()
        context['purchasers'] = User.objects.filter(
            Q(purchased_products__company__owner=self.request.user) |
            Q(purchased_products__company__members=self.request.user)
        ).distinct()
        context['current_purchaser'] = self.request.GET.get('purchaser', '')
        
        # 计算当前筛选结果的总价
        products = self.get_queryset()
        context['total_value'] = Product.calculate_total_price(products)
        
        # 添加筛选条件描述
        filter_descriptions = []
        if context['search_query']:
            filter_descriptions.append(f"搜索：{context['search_query']}")
        if context['min_price'] or context['max_price']:
            price_range = f"价格：{context['min_price'] or '0'} - {context['max_price'] or '不限'}"
            filter_descriptions.append(price_range)
        if context['min_quantity'] or context['max_quantity']:
            quantity_range = f"库存：{context['min_quantity'] or '0'} - {context['max_quantity'] or '不限'}"
            filter_descriptions.append(quantity_range)
        if context['current_purchaser']:
            purchaser = next((p for p in context['purchasers'] if str(p.id) == context['current_purchaser']), None)
            if purchaser:
                filter_descriptions.append(f"采购人：{purchaser.username}")
        
        context['filter_descriptions'] = filter_descriptions
        
        return context
        
    def export_to_excel(self):
        """导出产品列表到Excel"""
        queryset = self.get_queryset()
        data = []
        for index, product in enumerate(queryset, 1):
            data.append({
                '序号': index,
                '产品名称': product.name,
                '描述': product.description,
                '单价': float(product.price),
                '数量': product.quantity,
                '总价': float(product.total_price),
                '所属企业': product.company.name,
                '采购人': product.purchaser.username if product.purchaser else '',
                '创建时间': product.created_by.strftime('%Y-%m-%d %H:%M:%S'),
                '更新时间': product.updated_by.strftime('%Y-%m-%d %H:%M:%S'),
            })
            
        df = pd.DataFrame(data)
        
        # 创建一个Excel响应
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = f'attachment; filename=产品库存清单_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        # 将DataFrame写入Excel
        df.to_excel(response, index=False, engine='openpyxl')
        return response
        
    def get(self, request, *args, **kwargs):
        if request.GET.get('export') == 'excel':
            return self.export_to_excel()
        elif request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # 处理AJAX请求，返回选中产品的总价
            product_ids = request.GET.getlist('product_ids[]')
            if product_ids:
                selected_products = Product.objects.filter(id__in=product_ids)
                total_price = Product.calculate_total_price(selected_products)
                return JsonResponse({'total_price': float(total_price)})
        return super().get(request, *args, **kwargs)

class ProductDetailView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = 'inventory/product_detail.html'
    context_object_name = 'product'
    login_url = '/accounts/login/'

    def get_queryset(self):
        """确保用户只能查看有权限的产品"""
        user = self.request.user
        return Product.objects.filter(
            models.Q(company__owner=user) | models.Q(company__members=user)
        ).distinct()

class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('inventory:product_list')
    login_url = '/accounts/login/'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        # 获取用户可以访问的所有企业（去重）
        companies = Company.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        
        form.fields['company'].queryset = companies
        form.fields['company'].required = True
        form.fields['company'].empty_label = None
        return form

    def form_valid(self, form):
        try:
            # 验证用户是否有权限在选择的企业中创建产品
            company = form.cleaned_data.get('company')
            if not company:
                form.add_error('company', '必须选择所属企业')
                return self.form_invalid(form)
                
            user = self.request.user
            if not (company.owner == user or user in company.members.all()):
                form.add_error('company', '您没有权限在该企业中创建产品')
                return self.form_invalid(form)
            
            # 设置采购人为当前用户
            form.instance.purchaser = user
            
            response = super().form_valid(form)
            messages.success(self.request, '产品创建成功！')
            return response
        except Exception as e:
            messages.error(self.request, f'创建产品时出错：{str(e)}')
            return self.form_invalid(form)

class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    login_url = '/accounts/login/'
    
    def get_queryset(self):
        """确保用户只能编辑有权限的产品"""
        user = self.request.user
        return Product.objects.filter(
            models.Q(company__owner=user) | models.Q(company__members=user)
        ).distinct()

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        # 获取用户可以访问的所有企业（去重）
        companies = Company.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        
        form.fields['company'].queryset = companies
        form.fields['company'].required = True
        form.fields['company'].empty_label = None
        return form
    
    def get_success_url(self):
        messages.success(self.request, '产品更新成功！')
        return reverse_lazy('inventory:product_detail', kwargs={'pk': self.object.pk})

class ProductDeleteView(LoginRequiredMixin, DeleteView):
    model = Product
    template_name = 'inventory/product_confirm_delete.html'
    success_url = reverse_lazy('inventory:product_list')
    login_url = '/accounts/login/'
    
    def get_queryset(self):
        """确保用户只能删除有权限的产品"""
        user = self.request.user
        owned_companies = Company.objects.filter(owner=user)
        joined_companies = user.companies_joined.all()
        return Product.objects.filter(company__in=list(owned_companies) + list(joined_companies))
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, '产品已删除！')
        return super().delete(request, *args, **kwargs)