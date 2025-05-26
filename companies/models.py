from django.db import models
from django.conf import settings


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.SET_NULL,
                              null=True,
                              related_name='owned_company')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                     related_name='companies_joined',
                                     blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name