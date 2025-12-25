from django.contrib import admin
from .models import ConversationSession


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    """Admin interface for viewing conversation sessions."""
    list_display = ['user', 'current_state', 'current_order', 'updated_at']
    list_filter = ['current_state', 'updated_at']
    search_fields = ['user__phone_number', 'user__name']
    readonly_fields = ['user', 'last_message_id', 'created_at', 'updated_at']
    ordering = ['-updated_at']
    
    fieldsets = (
        ('Session Info', {
            'fields': ('user', 'current_state', 'current_order')
        }),
        ('Context Data', {
            'fields': ('context',),
            'classes': ('collapse',)
        }),
        ('Idempotency', {
            'fields': ('last_message_id',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
