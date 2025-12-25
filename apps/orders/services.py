"""
Cart and order management services.

This module provides the business logic layer for cart operations,
separating it from the model layer for testability and clarity.
"""
import logging
from typing import Tuple, Optional
from django.db import transaction

from .models import Order, OrderItem, OrderStatus
from apps.catalog.models import MenuItem

logger = logging.getLogger(__name__)


class CartService:
    """
    Service class for cart operations.
    
    Encapsulates all cart manipulation logic including validation,
    quantity management, and total calculation.
    """

    @staticmethod
    @transaction.atomic
    def add_item(order: Order, menu_item: MenuItem, quantity: int = 1) -> Tuple[OrderItem, bool]:
        """
        Add item to cart or update quantity if already present.
        
        Uses database transaction to ensure atomic updates.
        
        Args:
            order: The cart (Order in DRAFT status)
            menu_item: MenuItem to add
            quantity: Number to add (positive integer)
            
        Returns:
            Tuple of (OrderItem, created) where created is True if new item
            
        Raises:
            ValueError: If quantity is invalid or item unavailable
        """
        if quantity < 1:
            raise ValueError("Quantity must be at least 1")
            
        if not menu_item.is_available or not menu_item.is_active:
            raise ValueError(f"{menu_item.name} is currently unavailable")
        
        # Try to get existing item or create new
        item, created = OrderItem.objects.get_or_create(
            order=order,
            menu_item=menu_item,
            defaults={
                'quantity': quantity,
                'unit_price_minor': menu_item.price_minor,
            }
        )
        
        if not created:
            # Item exists, add to quantity
            item.quantity += quantity
            item.save(update_fields=['quantity', 'updated_at'])
            
        # Recalculate order total
        order.recalculate_total()
        
        logger.info(
            f"Added {quantity}x {menu_item.name} to order {order.reference}. "
            f"New total: {order.total_display}"
        )
        
        return item, created

    @staticmethod
    @transaction.atomic
    def update_item_quantity(order: Order, menu_item: MenuItem, quantity: int) -> Optional[OrderItem]:
        """
        Set item quantity directly (not additive).
        
        If quantity is 0, removes the item from cart.
        
        Args:
            order: The cart
            menu_item: MenuItem to update
            quantity: New quantity (0 to remove)
            
        Returns:
            Updated OrderItem, or None if removed
            
        Raises:
            ValueError: If item not in cart
        """
        try:
            item = OrderItem.objects.get(order=order, menu_item=menu_item)
        except OrderItem.DoesNotExist:
            raise ValueError(f"{menu_item.name} is not in your cart")
        
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")
            
        if quantity == 0:
            item.delete()
            logger.info(f"Removed {menu_item.name} from order {order.reference}")
            order.recalculate_total()
            return None
            
        item.quantity = quantity
        item.save(update_fields=['quantity', 'updated_at'])
        order.recalculate_total()
        
        logger.info(
            f"Updated {menu_item.name} quantity to {quantity} in order {order.reference}"
        )
        
        return item

    @staticmethod
    @transaction.atomic
    def remove_item(order: Order, menu_item: MenuItem) -> bool:
        """
        Remove item from cart entirely.
        
        Args:
            order: The cart
            menu_item: MenuItem to remove
            
        Returns:
            True if removed, False if item wasn't in cart
        """
        deleted, _ = OrderItem.objects.filter(
            order=order,
            menu_item=menu_item
        ).delete()
        
        if deleted:
            order.recalculate_total()
            logger.info(f"Removed {menu_item.name} from order {order.reference}")
            
        return bool(deleted)

    @staticmethod
    def clear_cart(order: Order) -> int:
        """
        Remove all items from cart.
        
        Args:
            order: The cart to clear
            
        Returns:
            Number of items removed
        """
        deleted, _ = order.items.all().delete()
        order.total_minor = 0
        order.save(update_fields=['total_minor', 'updated_at'])
        
        logger.info(f"Cleared {deleted} items from order {order.reference}")
        
        return deleted

    @staticmethod
    def get_cart_summary(order: Order) -> dict:
        """
        Generate a summary of cart contents for display.
        
        Returns:
            Dict with items list, total, and item count
        """
        items = []
        for order_item in order.items.select_related('menu_item').all():
            items.append({
                'name': order_item.menu_item.name,
                'quantity': order_item.quantity,
                'unit_price': order_item.unit_price_display,
                'subtotal': order_item.subtotal_display,
            })
            
        return {
            'items': items,
            'total': order.total_display,
            'total_minor': order.total_minor,
            'item_count': order.item_count,
            'is_empty': len(items) == 0,
        }


class OrderService:
    """
    Service class for order operations beyond cart management.
    """

    @staticmethod
    @transaction.atomic
    def finalize_for_payment(order: Order, delivery_address: str, 
                             instructions: str = '') -> Order:
        """
        Transition cart to pending payment status.
        
        This locks in the order details and prepares for Paystack initiation.
        
        Args:
            order: Cart to finalize
            delivery_address: Delivery address
            instructions: Optional delivery instructions
            
        Returns:
            Updated order in PENDING status
            
        Raises:
            ValueError: If cart is empty or already finalized
        """
        if order.status != OrderStatus.DRAFT:
            raise ValueError("Order has already been submitted")
            
        if order.items.count() == 0:
            raise ValueError("Cannot checkout with empty cart")
        
        order.delivery_address = delivery_address
        order.delivery_instructions = instructions
        order.status = OrderStatus.PENDING
        order.save()
        
        logger.info(
            f"Order {order.reference} finalized for payment. "
            f"Total: {order.total_display}"
        )
        
        return order

    @staticmethod
    def cancel_order(order: Order, reason: str = '') -> Order:
        """
        Cancel an order that hasn't been paid.
        
        Args:
            order: Order to cancel
            reason: Optional cancellation reason
            
        Returns:
            Cancelled order
            
        Raises:
            ValueError: If order cannot be cancelled
        """
        if order.status in [OrderStatus.PAID, OrderStatus.PREPARING, 
                            OrderStatus.READY, OrderStatus.DELIVERED]:
            raise ValueError("Cannot cancel order that is already being processed")
        
        order.status = OrderStatus.CANCELLED
        order.save(update_fields=['status', 'updated_at'])
        
        logger.info(f"Order {order.reference} cancelled. Reason: {reason or 'Not specified'}")
        
        return order
