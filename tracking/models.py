from django.db import models
from django.conf import settings
from orders.models import Order


class OrderStatusEvent(models.Model):
    """
    Immutable audit log — every status change on an order creates a new
    record here instead of just overwriting Order.status. This is what
    powers the customer-facing timeline and gives us a verifiable history
    for dispute resolution.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_events',
    )
    status = models.CharField(max_length=20, choices=Order.Status.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_events',
        help_text="Who triggered this event (driver/dispatcher). Null if system-generated.",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    note = models.CharField(max_length=255, blank=True, help_text="e.g. 'customer not available'")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.order.order_number} → {self.status} @ {self.timestamp}"


class ProofOfDelivery(models.Model):
    """
    One-to-one with Order — captured when status becomes 'delivered'.
    """
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='proof_of_delivery',
    )
    photo = models.ImageField(upload_to='proof_of_delivery/photos/', null=True, blank=True)
    signature = models.ImageField(upload_to='proof_of_delivery/signatures/', null=True, blank=True)
    recipient_name = models.CharField(max_length=150, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    captured_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"POD for {self.order.order_number}"


class LocationPing(models.Model):
    """
    Raw location history from a driver's device. Used to reconstruct
    a driver's path and to broadcast live location over WebSockets.
    """
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='location_pings',
        limit_choices_to={'role': 'driver'},
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='location_pings',
        help_text="Order being actively delivered when this ping was sent, if any.",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.driver.username} @ {self.latitude}, {self.longitude}"