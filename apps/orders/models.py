"""
Order and OrderItem models for cart and order management.

Key design decisions:
1. Cart-as-Order pattern: A cart is simply an Order in DRAFT status. This unifies
   the data model and simplifies the transition from cart to paid order.

2. Price snapshot: OrderItem stores unit_price_minor at the time of addition,
   protecting against menu price changes affecting existing orders.

3. Order reference: Human-readable reference for customer communication and
   payment tracking, generated automatically.

4. Minor units: All amounts in kobo (NGN minor units) to prevent float issues.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class OrderStatus(models.TextChoices):
    """
    Order lifecycle states.
    
    DRAFT -> PENDING -> PAID -> PREPARING -> READY -> DELIVERED
                    \-> CANCELLED
    """
    DRAFT = 'draft', 'Draft (Cart)'
    PENDING = 'pending', 'Pending Payment'
    PAID = 'paid', 'Paid'
    PREPARING = 'preparing', 'Preparing'
    READY = 'ready', 'Ready for Pickup/Delivery'
    DELIVERED = 'delivered', 'Delivered'
    CANCELLED = 'cancelled', 'Cancelled'


class Order(models.Model):
    """
    Represents a customer order, starting as a cart (DRAFT) and progressing
    through payment to fulfillment.
    
    The same model handles both cart and completed order states, with status
    tracking the current lifecycle stage.
    
    Attributes:
        user: WhatsApp user who placed the order
        reference: Unique order reference for customer/payment (e.g., "ORD-A1B2C3")
        status: Current order state (see OrderStatus)
        total_minor: Order total in minor units, updated on cart changes
        delivery_address: Address collected during checkout
        delivery_instructions: Optional notes for delivery
        paystack_reference: Paystack transaction reference for payment tracking
        paid_at: Timestamp when payment was confirmed
    """
    user = models.ForeignKey(
        'users.UserProfile',
        on_delete=models.CASCADE,
        related_name='orders'
    )
    reference = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique order reference for customer communication"
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.DRAFT,
        db_index=True
    )
    total_minor = models.PositiveIntegerField(
        default=0,
        help_text="Order total in minor units (kobo)"
    )
    delivery_address = models.TextField(
        blank=True,
        help_text="Delivery address provided at checkout"
    )
    delivery_instructions = models.TextField(
        blank=True,
        help_text="Special instructions for delivery"
    )
    paystack_reference = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Paystack transaction reference"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment was confirmed"
    )

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        # Generate reference on first save
        if not self.reference:
            self.reference = self._generate_reference()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_reference() -> str:
        """Generate a unique, human-readable order reference."""
        # Format: ORD-XXXXXXXX (8 hex chars from UUID)
        return f"ORD-{uuid.uuid4().hex[:8].upper()}"

    @property
    def total_display(self) -> str:
        """Format total for display with currency symbol."""
        symbol = getattr(settings, 'CURRENCY_SYMBOL', '₦')
        amount = self.total_minor / 100
        return f"{symbol}{amount:,.2f}"

    @property
    def item_count(self) -> int:
        """Total number of items (sum of quantities)."""
        return sum(item.quantity for item in self.items.all())

    def recalculate_total(self) -> int:
        """
        Recalculate order total from items and update.
        
        Called after any cart modification to keep total in sync.
        Returns the new total for convenience.
        """
        total = sum(item.subtotal_minor for item in self.items.all())
        self.total_minor = total
        self.save(update_fields=['total_minor', 'updated_at'])
        return total

    def mark_as_paid(self, paystack_reference: str = None):
        """
        Mark order as paid and record payment timestamp.
        
        Args:
            paystack_reference: Transaction reference from Paystack webhook
        """
        self.status = OrderStatus.PAID
        self.paid_at = timezone.now()
        if paystack_reference:
            self.paystack_reference = paystack_reference
        self.save(update_fields=['status', 'paid_at', 'paystack_reference', 'updated_at'])

    @classmethod
    def get_or_create_cart(cls, user) -> 'Order':
        """
        Get user's current cart or create a new one.
        
        Only one DRAFT order per user at a time.
        
        Args:
            user: UserProfile instance
            
        Returns:
            Order in DRAFT status for the user
        """
        cart, created = cls.objects.get_or_create(
            user=user,
            status=OrderStatus.DRAFT,
        )
        return cart


class OrderItem(models.Model):
    """
    Line item in an order, linking MenuItem to Order with quantity.
    
    Stores a price snapshot (unit_price_minor) at the time of addition,
    ensuring the order total doesn't change if menu prices are updated.
    
    Attributes:
        order: Parent order
        menu_item: The menu item being ordered
        quantity: Number of this item
        unit_price_minor: Price per unit at time of addition (snapshot)
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    menu_item = models.ForeignKey(
        'catalog.MenuItem',
        on_delete=models.PROTECT,  # Prevent deletion of items in orders
        related_name='order_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price_minor = models.PositiveIntegerField(
        help_text="Price per unit at time of order (snapshot)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
        # Ensure same item isn't added twice to same order
        unique_together = ['order', 'menu_item']

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name}"

    @property
    def subtotal_minor(self) -> int:
        """Total price for this line item."""
        return self.quantity * self.unit_price_minor

    @property
    def subtotal_display(self) -> str:
        """Format subtotal for display with currency symbol."""
        symbol = getattr(settings, 'CURRENCY_SYMBOL', '₦')
        amount = self.subtotal_minor / 100
        return f"{symbol}{amount:,.2f}"

    @property
    def unit_price_display(self) -> str:
        """Format unit price for display."""
        symbol = getattr(settings, 'CURRENCY_SYMBOL', '₦')
        amount = self.unit_price_minor / 100
        return f"{symbol}{amount:,.2f}"
