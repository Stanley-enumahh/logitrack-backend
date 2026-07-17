from django.contrib import admin
from .models import OrderStatusEvent, ProofOfDelivery, LocationPing


@admin.register(OrderStatusEvent)
class OrderStatusEventAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'actor', 'timestamp')
    list_filter = ('status', 'timestamp')
    search_fields = ('order__order_number',)
    readonly_fields = ('timestamp',)


@admin.register(ProofOfDelivery)
class ProofOfDeliveryAdmin(admin.ModelAdmin):
    list_display = ('order', 'recipient_name', 'captured_at')
    readonly_fields = ('captured_at',)


@admin.register(LocationPing)
class LocationPingAdmin(admin.ModelAdmin):
    list_display = ('driver', 'order', 'latitude', 'longitude', 'timestamp')
    list_filter = ('driver', 'timestamp')