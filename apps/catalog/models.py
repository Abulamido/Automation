"""
Catalog models for menu categories and items.

The catalog is structured as Categories containing MenuItems. This hierarchical
structure maps well to conversational navigation: users first select a category,
then browse items within it.

All prices are stored in minor units (kobo for NGN) to avoid floating-point
precision issues common in financial calculations.
"""
from django.db import models
from django.conf import settings


class Category(models.Model):
    """
    Menu category grouping related items (e.g., "Main Dishes", "Drinks").
    
    Categories are the top-level navigation in the conversational menu.
    The ordering field controls display sequence in WhatsApp messages.
    
    Attributes:
        name: Display name shown to users
        description: Optional longer description (for admin reference)
        is_active: Whether this category appears in the menu
        ordering: Sort order for display (lower = first)
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive categories are hidden from the menu"
    )
    ordering = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear first"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['ordering', 'name']

    def __str__(self):
        return self.name

    @classmethod
    def get_active_categories(cls):
        """Return queryset of active categories in display order."""
        return cls.objects.filter(is_active=True).order_by('ordering', 'name')


class MenuItem(models.Model):
    """
    Individual menu item with pricing.
    
    Items belong to a category and have two availability flags:
    - is_active: Long-term visibility (menu management)
    - is_available: Runtime availability (out of stock)
    
    Price is stored in minor units (kobo) to avoid floating-point issues.
    For NGN, ₦1,500.00 is stored as 150000.
    
    Attributes:
        category: Parent category for navigation
        name: Item name shown to users
        description: Optional description
        price_minor: Price in minor units (kobo for NGN)
        is_available: Whether item can be ordered right now
        is_active: Whether item appears in menu at all
    """
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='items'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price_minor = models.PositiveIntegerField(
        help_text="Price in minor units (kobo for NGN)"
    )
    is_available = models.BooleanField(
        default=True,
        help_text="Toggle off when item is out of stock"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive items are hidden from the menu"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Menu Item'
        verbose_name_plural = 'Menu Items'
        ordering = ['category__ordering', 'name']

    def __str__(self):
        return f"{self.name} - {self.price_display}"

    @property
    def price_display(self) -> str:
        """
        Format price for display with currency symbol.
        Example: 150000 -> '₦1,500.00'
        """
        symbol = getattr(settings, 'CURRENCY_SYMBOL', '₦')
        amount = self.price_minor / 100
        return f"{symbol}{amount:,.2f}"

    @property
    def price_major(self) -> float:
        """Price in major units (naira instead of kobo)."""
        return self.price_minor / 100

    @classmethod
    def get_available_items(cls, category_id: int = None):
        """
        Return queryset of available items, optionally filtered by category.
        
        Args:
            category_id: Optional category ID to filter by
            
        Returns:
            QuerySet of available and active menu items
        """
        qs = cls.objects.filter(is_active=True, is_available=True)
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs.select_related('category').order_by('name')
