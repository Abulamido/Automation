"""
Checkout flow handlers.

Handles address collection and order confirmation before payment.
"""
from .base import BaseHandler, HandlerResult
from apps.conversations.states import ConversationState
from apps.orders.services import CartService, OrderService
from apps.orders.models import OrderStatus


class AddressHandler(BaseHandler):
    """
    Handler for COLLECT_ADDRESS state.
    
    Collects delivery address from user.
    """

    def handle(self, message: str) -> HandlerResult:
        """Handle address input."""
        global_result = self.check_global_keyword(message)
        if global_result:
            return global_result

        normalized = self.normalize_input(message)
        
        # Allow cancellation
        if normalized in ('cancel', 'back'):
            return HandlerResult(
                messages=["Checkout cancelled. Here's your cart:"],
                next_state=ConversationState.VIEW_CART
            )

        # Validate address (basic check - not empty and has some length)
        address = message.strip()
        
        if len(address) < 10:
            return HandlerResult(
                messages=[
                    "Please provide a more detailed delivery address.\n\n"
                    "Example: 123 Main Street, Lekki Phase 1, Lagos\n\n"
                    "Or type 'cancel' to go back."
                ],
                next_state=ConversationState.COLLECT_ADDRESS
            )

        # Store address in context and proceed to confirmation
        cart = self.session.current_order
        cart_summary = CartService.get_cart_summary(cart)
        
        return HandlerResult(
            messages=[
                f"📍 Delivery Address saved!\n\n"
                f"Lastly, please enter your email address (for payment & receipt):"
            ],
            next_state=ConversationState.COLLECT_EMAIL,
            context_updates={'delivery_address': address}
        )

    def _build_order_summary(self, cart_summary: dict) -> str:
        """Build order summary for confirmation."""
        items_text = "\n".join(
            f"  • {item['quantity']}x {item['name']}"
            for item in cart_summary['items']
        )
        
        return (
            f"📋 Order Summary:\n"
            f"{items_text}\n\n"
            f"Total: {cart_summary['total']}"
        )


class ConfirmHandler(BaseHandler):
    """
    Handler for CONFIRM_ORDER state.
    
    Shows order summary and waits for confirmation before initiating payment.
    """

    def handle(self, message: str) -> HandlerResult:
        """Handle order confirmation."""
        global_result = self.check_global_keyword(message)
        if global_result:
            return global_result

        normalized = self.normalize_input(message)
        
        # Handle cancellation
        if normalized in ('cancel', 'back', 'no', 'edit'):
            return HandlerResult(
                messages=["Order cancelled. Returning to phone collection. Please enter your phone number:"],
                next_state=ConversationState.COLLECT_PHONE
            )

        # Handle confirmation
        if normalized in ('confirm', 'yes', 'proceed', 'pay', 'ok'):
            return self._process_confirmation()

        # Invalid input
        return HandlerResult(
            messages=[
                "Please reply 'confirm' to proceed to payment, or 'cancel' to go back."
            ],
            next_state=ConversationState.CONFIRM_ORDER
        )

    def _process_confirmation(self) -> HandlerResult:
        """Process order confirmation and initiate payment."""
        cart = self.session.current_order
        delivery_address = self.session.get_context('delivery_address')
        
        if not cart or cart.status != OrderStatus.DRAFT:
            return HandlerResult(
                messages=["Something went wrong. Please start your order again."],
                next_state=ConversationState.START
            )

        if not delivery_address:
            return HandlerResult(
                messages=["Please provide a delivery address first."],
                next_state=ConversationState.COLLECT_ADDRESS
            )

        try:
            # Finalize order for payment
            order = OrderService.finalize_for_payment(cart, delivery_address)
            
            # Store order reference for payment processing
            self.session.set_context('pending_order_id', order.id)
            
            # Generate payment link (handled by payment handler)
            return HandlerResult(
                messages=[
                    f"✅ Order {order.reference} confirmed!\n\n"
                    f"Total: {order.total_display}\n\n"
                    f"Generating your payment link..."
                ],
                next_state=ConversationState.AWAITING_PAYMENT
            )
            
        except ValueError as e:
            return HandlerResult(
                messages=[f"Cannot process order: {str(e)}"],
                next_state=ConversationState.VIEW_CART
            )
