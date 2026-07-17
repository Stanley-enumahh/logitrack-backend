from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'customer_name', 'status', 'priority',
        'assigned_driver', 'created_at',
    )
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('order_number', 'customer_name', 'customer_phone', 'tracking_token')
    readonly_fields = ('tracking_token', 'order_number', 'created_at', 'updated_at')