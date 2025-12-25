from django.contrib import admin
from .models import Order, OrderItem, OrderStatus


class OrderItemInline(admin.TabularInline):
    """Inline display of order items."""
    model = OrderItem
    extra = 0
    readonly_fields = ['menu_item', 'quantity', 'unit_price_minor', 'subtotal_display']
    fields = ['menu_item', 'quantity', 'unit_price_minor', 'subtotal_display']
    
    def subtotal_display(self, obj):
        return obj.subtotal_display
    subtotal_display.short_description = 'Subtotal'
    
    def has_add_permission(self, request, obj=None):
        return False  # Don't allow adding items through admin
    
    def has_delete_permission(self, request, obj=None):
        return False  # Don't allow deleting items through admin


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for orders."""
    list_display = ['reference', 'user', 'status', 'total_display', 'item_count', 
                    'created_at', 'paid_at']
    list_filter = ['status', 'created_at', 'paid_at']
    search_fields = ['reference', 'user__phone_number', 'user__name', 
                     'paystack_reference']
    readonly_fields = ['reference', 'user', 'total_minor', 'paystack_reference',
                       'created_at', 'updated_at', 'paid_at']
    ordering = ['-created_at']
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Info', {
            'fields': ('reference', 'user', 'status', 'total_minor')
        }),
        ('Delivery', {
            'fields': ('delivery_address', 'delivery_instructions')
        }),
        ('Payment', {
            'fields': ('paystack_reference', 'paid_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_display(self, obj):
        return obj.total_display
    total_display.short_description = 'Total'
    
    def item_count(self, obj):
        return obj.item_count
    item_count.short_description = 'Items'
