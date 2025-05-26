from django.db import models
from django.conf import settings
from django.utils import timezone

class Friendship(models.Model):
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL,
                                  on_delete=models.CASCADE,
                                  related_name='sent_friend_requests')
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE,
                                related_name='received_friend_requests')
    created_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('from_user', 'to_user')]

    def __str__(self):
        status = '已接受' if self.accepted_at else '待处理'
        return f'好友关系:{self.from_user.username} -> {self.to_user.username} ({status})'

    def accept(self):
        self.accepted_at = timezone.now()
        self.save()

class Blacklist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                           on_delete=models.CASCADE,
                           related_name='user_blacklist')
    blocked_user = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   related_name='blocked_by')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [('user', 'blocked_user')]

    def __str__(self):
        return f'{self.user.username} 已拉黑 {self.blocked_user.username}'