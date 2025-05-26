from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm
from django.core.exceptions import ValidationError
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label='电子邮箱',
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        help_text='请输入有效的电子邮箱地址，用于账号验证'
    )
    password1 = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='密码至少包含8个字符'
    )
    password2 = forms.CharField(
        label='确认密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='请再次输入相同的密码进行确认'
    )
    
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('email', 'password1', 'password2')  # 移除username字段，只使用email
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            if CustomUser.objects.filter(email=email).exists():
                raise ValidationError('该邮箱已被注册')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']  # 使用邮箱作为用户名
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='电子邮箱',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

class EmailVerificationForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        label='验证码',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

class LoginByCodeForm(forms.Form):
    email = forms.EmailField(
        required=True,
        label='电子邮箱',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    code = forms.CharField(
        max_length=6,
        label='验证码',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )