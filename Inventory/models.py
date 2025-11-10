from django.db import models
from django.contrib.auth.models import User


class Stock(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    unit_of_measure = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    min_threshold = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text="Minimum threshold for stock quantity. If quantity falls below this value, the stock is considered 'low stock'."
    )

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="stocks_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="stocks_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

