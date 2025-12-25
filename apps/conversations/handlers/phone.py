"""
Phone number collection handler for checkout.
"""
from .base import BaseHandler, HandlerResult
from apps.conversations.states import ConversationState
import re

class PhoneHandler(BaseHandler):
    """
    Handler for COLLECT_PHONE state.
    
    Collects a contact phone number for the order.
    Although we have the WhatsApp ID, the customer might want to provide
     a different number for the person receiving the delivery.
    """

    def handle(self, message: str) -> HandlerResult:
        """Handle phone number input."""
        global_result = self.check_global_keyword(message)
        if global_result:
            return global_result

        normalized = self.normalize_input(message)
        
        if normalized in ('cancel', 'back'):
            return HandlerResult(
                messages=["Returning to email collection. Please enter your email address:"],
                next_state=ConversationState.COLLECT_EMAIL
            )

        phone = message.strip()
        
        # Simple phone validation (digits, +, spaces, dashes, min 7 chars)
        clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
        if not re.match(r"^\+?\d{7,15}$", clean_phone):
            return HandlerResult(
                messages=[
                    "Please enter a valid phone number (e.g., 08012345678).\n\n"
                    "We need this so the delivery rider can contact you."
                ],
                next_state=ConversationState.COLLECT_PHONE
            )

        # Update user profile if they don't have a phone number yet or if different
        # In a real app, we might store this on the order specifically
        
        from apps.orders.services import CartService
        cart = self.session.current_order
        cart_summary = CartService.get_cart_summary(cart)
        address = self.session.get_context('delivery_address')
        email = self.session.get_context('email')

        return HandlerResult(
            messages=[
                f"✅ Phone saved: {phone}\n\n"
                f"📍 Delivery Address: {address}\n"
                f"📧 Email: {email}\n"
                f"📞 Phone: {phone}\n\n"
                f"{self._build_order_summary(cart_summary)}\n\n"
                f"Reply 'confirm' to place your order and get the payment link, or 'cancel' to go back."
            ],
            next_state=ConversationState.CONFIRM_ORDER,
            context_updates={'delivery_phone': phone}
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
