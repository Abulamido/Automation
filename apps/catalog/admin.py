from django.contrib import admin
from .models import Category, MenuItem


class MenuItemInline(admin.TabularInline):
    """Inline editor for menu items within category view."""
    model = MenuItem
    extra = 1
    fields = ['name', 'price_minor', 'is_available', 'is_active']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin interface for menu categories."""
    list_display = ['name', 'ordering', 'is_active', 'item_count']
    list_filter = ['is_active']
    list_editable = ['ordering', 'is_active']
    search_fields = ['name']
    ordering = ['ordering', 'name']
    inlines = [MenuItemInline]

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """Admin interface for individual menu items."""
    list_display = ['name', 'category', 'price_display', 'is_available', 'is_active']
    list_filter = ['category', 'is_available', 'is_active']
    list_editable = ['is_available', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['category__ordering', 'name']

    def price_display(self, obj):
        return obj.price_display
    price_display.short_description = 'Price'
