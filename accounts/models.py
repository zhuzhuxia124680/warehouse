from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    phone = models.CharField(max_length=11, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures', blank=True, null=True)
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='CustomUser_groups',  # 唯一名称
        blank=True,
        verbose_name='groups',
        help_text='用户所属的组',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='CustomUser_permissions',  # 唯一名称
        blank=True,
        verbose_name='用户权限',
        help_text='用户的特定权限',
    )
    pass

class EmailVerification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    code = models.CharField(max_length=6, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() >= self.expiry_at

    def __str__(self):
        return f'{self.user.email}的验证码的状态为{self.is_used}'

