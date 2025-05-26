from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.middleware import get_user
from django.contrib.auth.models import User
from .models import Friendship

class AddFriendForm(forms.Form):
    target_user_identifier = forms.CharField(max_length=255, label='请输入用户名或邮箱')

    def clean_target_user_identifier(self):
        identifier = self.cleaned_data['target_user_identifier']
        User = get_user_model()  # 正确获取当前激活的用户模型

        try:
            user = User.objects.filter(username=identifier).first()
            if user:
                return user
            
            user = User.objects.filter(email=identifier).first()
            if user:
                return user
            
            raise forms.ValidationError('用户不存在')
        except Exception as e:
            raise forms.ValidationError(f'查找用户时出错: {str(e)}')

class AcceptFriendRequestForm(forms.Form):
    request_id = forms.IntegerField(widget=forms.HiddenInput)