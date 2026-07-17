from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, DriverProfile


class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Role Info', {'fields': ('role', 'phone_number')}),
    )
    list_display = ('username', 'email', 'role', 'is_staff')


admin.site.register(User, CustomUserAdmin)
admin.site.register(DriverProfile)