from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for viewing and managing WhatsApp users."""
    list_display = ['name', 'phone_number', 'wa_id', 'email', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'phone_number', 'wa_id', 'email']
    readonly_fields = ['wa_id', 'created_at', 'updated_at']
    ordering = ['-created_at']
