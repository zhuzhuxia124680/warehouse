from django import forms
from .models import Company

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name']
        labels = {'name': '公司名称'}

class JoinCompanyForm(forms.Form):
    company_name = forms.CharField(max_length=255, label='输入公司名称')