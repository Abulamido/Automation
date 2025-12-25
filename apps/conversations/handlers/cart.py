"""
Cart viewing and management handler.

Allows users to view cart contents, modify quantities, and proceed to checkout.
"""
from .base import BaseHandler, HandlerResult
from apps.conversations.states import ConversationState
from apps.orders.services import CartService
from apps.orders.models import OrderStatus


class CartHandler(BaseHandler):
    """
    Handler for VIEW_CART state.
    
    Shows cart contents and provides options to:
    - Continue shopping
    - Remove items
    - Proceed to checkout
    - Clear cart
    """

    def handle(self, message: str) -> HandlerResult:
        """Handle cart view actions."""
        global_result = self.check_global_keyword(message)
        if global_result:
            return global_result

        normalized = self.normalize_input(message)
        
        cart = self.session.current_order
        
        # Ensure cart exists
        if not cart or cart.status != OrderStatus.DRAFT:
            from apps.orders.models import Order
            cart = Order.get_or_create_cart(self.user)
            self.session.current_order = cart
            self.session.save(update_fields=['current_order'])

        cart_summary = CartService.get_cart_summary(cart)

        # Handle empty cart
        if cart_summary['is_empty']:
            return HandlerResult(
                messages=[
                    "🛒 Your cart is empty!\n\n"
                    "Type 'menu' to browse our menu and add items."
                ],
                next_state=ConversationState.SELECT_CATEGORY
            )

        # Handle checkout
        if normalized in ('checkout', 'pay', 'order', 'proceed', 'yes'):
            return HandlerResult(
                messages=[
                    f"Great! Let's complete your order.\n\n"
                    f"Please enter your delivery address:"
                ],
                next_state=ConversationState.COLLECT_ADDRESS
            )

        # Handle continue shopping
        if normalized in ('menu', 'more', 'shop', 'add', 'continue'):
            return HandlerResult(
                next_state=ConversationState.SELECT_CATEGORY
            )

        # Handle clear cart
        if normalized in ('clear', 'empty', 'remove all'):
            CartService.clear_cart(cart)
            return HandlerResult(
                messages=[
                    "🗑️ Cart cleared!\n\n"
                    "Type 'menu' to start shopping again."
                ],
                next_state=ConversationState.SELECT_CATEGORY
            )

        # Check for remove command (e.g., "remove 1")
        if normalized.startswith('remove '):
            return self._handle_remove(normalized, cart, cart_summary)

        # Default: show cart and options
        return HandlerResult(
            messages=[self._build_cart_message(cart_summary)],
            next_state=ConversationState.VIEW_CART
        )

    def _handle_remove(self, message: str, cart, cart_summary) -> HandlerResult:
        """Handle item removal from cart."""
        try:
            parts = message.split()
            if len(parts) >= 2:
                item_num = int(parts[1])
                
                items = list(cart.items.select_related('menu_item').all())
                if 1 <= item_num <= len(items):
                    order_item = items[item_num - 1]
                    CartService.remove_item(cart, order_item.menu_item)
                    
                    # Get updated summary
                    updated_summary = CartService.get_cart_summary(cart)
                    
                    if updated_summary['is_empty']:
                        return HandlerResult(
                            messages=[
                                f"✅ Removed {order_item.menu_item.name}.\n\n"
                                f"Your cart is now empty. Type 'menu' to shop."
                            ],
                            next_state=ConversationState.SELECT_CATEGORY
                        )
                    
                    return HandlerResult(
                        messages=[
                            f"✅ Removed {order_item.menu_item.name}.\n\n"
                            f"{self._build_cart_message(updated_summary)}"
                        ],
                        next_state=ConversationState.VIEW_CART
                    )
        except (ValueError, IndexError):
            pass
        
        return HandlerResult(
            messages=[
                "Invalid remove command. Use 'remove 1' to remove item #1.\n\n"
                f"{self._build_cart_message(cart_summary)}"
            ],
            next_state=ConversationState.VIEW_CART
        )

    def _build_cart_message(self, cart_summary: dict) -> str:
        """Build cart display message."""
        items_text = "\n".join(
            f"{i}. {item['quantity']}x {item['name']} - {item['subtotal']}"
            for i, item in enumerate(cart_summary['items'], 1)
        )
        
        return (
            f"🛒 Your Cart:\n\n"
            f"{items_text}\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Total: {cart_summary['total']}\n\n"
            f"Reply:\n"
            f"• 'checkout' - Proceed to payment\n"
            f"• 'menu' - Continue shopping\n"
            f"• 'remove 1' - Remove item #1\n"
            f"• 'clear' - Empty cart"
        )

    def get_intro_message(self) -> str:
        """Show cart when entering this state."""
        cart = self.session.current_order
        if not cart:
            return "🛒 Your cart is empty!"
        
        cart_summary = CartService.get_cart_summary(cart)
        if cart_summary['is_empty']:
            return "🛒 Your cart is empty! Type 'menu' to browse."
        
        return self._build_cart_message(cart_summary)
