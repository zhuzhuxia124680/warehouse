from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    company = models.ForeignKey('companies.Company',
                            on_delete=models.CASCADE,
                            related_name='products',
                            null=True,
                            blank=True
                            )
    purchaser = models.ForeignKey(settings.AUTH_USER_MODEL,
                               on_delete=models.SET_NULL,
                               null=True,
                               blank=True,
                               related_name='purchased_products',
                               verbose_name='采购人')
    created_by = models.DateTimeField(auto_now_add=True)
    updated_by = models.DateTimeField(auto_now=True)

    def clean(self):
        if not self.company:
            raise ValidationError({'company': '必须选择所属企业'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def total_price(self):
        """计算产品总价"""
        return self.price * self.quantity

    @staticmethod
    def calculate_total_price(products):
        """计算多个产品的总价"""
        return sum(product.total_price for product in products)

    def __str__(self):
        return self.name

