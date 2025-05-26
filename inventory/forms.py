from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'quantity', 'company', 'purchaser']
        labels = {
            'name': '产品名称',
            'description': '产品描述',
            'price': '价格',
            'quantity': '数量',
            'company': '所属企业',
            'purchaser': '采购人',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'company': forms.Select(attrs={'class': 'form-control'}),
            'purchaser': forms.HiddenInput(),
        }
        error_messages = {
            'company': {
                'required': '请选择所属企业',
            }
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not self.instance.pk:  # 只在创建新产品时设置
            self.initial['purchaser'] = user.id