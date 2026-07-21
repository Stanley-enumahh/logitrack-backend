from django.db import models

# Create your models here.

from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
    class Role(models.TextChoices):
        DISPATCHER = 'dispatcher', 'Dispatcher'
        DRIVER = 'driver', 'Driver'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.DISPATCHER,
    )
    phone_number = models.CharField(max_length=20, blank=True)

    is_verified = models.BooleanField(default=False)
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False)
    verification_sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

class DriverProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='driver_profile',
        limit_choices_to={'role': User.Role.DRIVER},
    )
    vehicle_type = models.CharField(max_length=50, blank=True)
    vehicle_plate_number = models.CharField(max_length=20, blank=True)
    is_available = models.BooleanField(default=True)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Driver: {self.user.username}"
    
import uuid
from django.utils import timezone
from datetime import timedelta


class DispatcherInvite(models.Model):
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_invites',
    )
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(days=7)

    def __str__(self):
        return f"Invite for {self.email} by {self.invited_by.username}"    