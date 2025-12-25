"""
Email collection handler for checkout.
"""
from .base import BaseHandler, HandlerResult
from apps.conversations.states import ConversationState
import re

class EmailHandler(BaseHandler):
    """
    Handler for COLLECT_EMAIL state.
    
    Collects validation email for Paystack transactions.
    """

    def handle(self, message: str) -> HandlerResult:
        """Handle email input."""
        global_result = self.check_global_keyword(message)
        if global_result:
            return global_result

        normalized = self.normalize_input(message)
        
        if normalized in ('cancel', 'back'):
            return HandlerResult(
                messages=["Returning to address collection. Please enter your delivery address:"],
                next_state=ConversationState.COLLECT_ADDRESS
            )

        email = message.strip()
        
        # Basic email validation
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return HandlerResult(
                messages=[
                    "Please enter a valid email address (e.g., name@example.com).\n\n"
                    "We need this for your order receipt and payment."
                ],
                next_state=ConversationState.COLLECT_EMAIL
            )

        # Update user profile with email
        self.user.email = email
        self.user.save(update_fields=['email', 'updated_at'])

        # Store in context and proceed to confirmation
        from apps.orders.services import CartService
        cart_summary = CartService.get_cart_summary(self.session.current_order)
        address = self.session.get_context('delivery_address')

        return HandlerResult(
            messages=[
                f"✅ Email saved!\n\n"
                f"Lastly, please enter your contact phone number for the delivery rider:"
            ],
            next_state=ConversationState.COLLECT_PHONE,
            context_updates={'email': email}
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
