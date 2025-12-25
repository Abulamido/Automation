"""
Payment state handlers.

Handles payment initiation and confirmation states.
"""
from .base import BaseHandler, HandlerResult
from apps.conversations.states import ConversationState
from apps.orders.models import Order, OrderStatus
from utils.payments import paystack_client
import logging

logger = logging.getLogger(__name__)


class PaymentHandler(BaseHandler):
    """
    Handler for AWAITING_PAYMENT state.
    
    In this state, we've sent a payment link and are waiting for Paystack webhook
    to confirm payment. User can check status or cancel.
    """

    def handle(self, message: str) -> HandlerResult:
        """Handle messages while awaiting payment."""
        global_result = self.check_global_keyword(message)
        if global_result:
            return global_result

        normalized = self.normalize_input(message)
        
        # Get pending order
        order_id = self.session.get_context('pending_order_id')
        order = None
        
        if order_id:
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                pass

        # Check if payment was already completed (webhook may have processed)
        if order and order.status == OrderStatus.PAID:
            return HandlerResult(
                messages=[
                    f"✅ Payment confirmed!\n\n"
                    f"Your order {order.reference} has been paid.\n"
                    f"We'll start preparing your food right away!\n\n"
                    f"Thank you for your order! 🙏"
                ],
                next_state=ConversationState.PAYMENT_CONFIRMED
            )

        # Handle status check
        if normalized in ('status', 'check', 'paid'):
            if order and order.status == OrderStatus.PAID:
                return HandlerResult(
                    messages=["✅ Payment confirmed! Your order is being prepared."],
                    next_state=ConversationState.PAYMENT_CONFIRMED
                )
            return HandlerResult(
                messages=[
                    "⏳ We haven't received your payment yet.\n\n"
                    "Please complete payment using the link sent earlier.\n"
                    "If you've already paid, please wait a moment."
                ],
                next_state=ConversationState.AWAITING_PAYMENT
            )

        # Handle cancellation
        if normalized in ('cancel', 'abort'):
            if order and order.status == OrderStatus.PENDING:
                from apps.orders.services import OrderService
                OrderService.cancel_order(order, "Cancelled by user")
                
                # Create new cart for user
                new_cart = Order.get_or_create_cart(self.user)
                self.session.current_order = new_cart
                self.session.save(update_fields=['current_order'])
                
            return HandlerResult(
                messages=[
                    "Order cancelled.\n\n"
                    "Type 'menu' to start a new order."
                ],
                next_state=ConversationState.SELECT_CATEGORY,
                context_updates={'pending_order_id': None, 'delivery_address': None}
            )

        # Handle resend link request
        if normalized in ('link', 'resend', 'payment link', 'pay again'):
            if order and order.status == OrderStatus.PENDING:
                # Re-generate link
                intro = self.get_intro_message()
                return HandlerResult(
                    messages=[intro],
                    next_state=ConversationState.AWAITING_PAYMENT
                )

        # Default response
        return HandlerResult(
            messages=[
                f"⏳ Awaiting payment for order {order.reference if order else 'N/A'}\n\n"
                f"Please complete payment using the link sent.\n\n"
                f"Reply:\n"
                f"• 'status' - Check payment status\n"
                f"• 'link' - Resend payment link\n"
                f"• 'cancel' - Cancel order"
            ],
            next_state=ConversationState.AWAITING_PAYMENT
        )

    def get_intro_message(self) -> str:
        """
        Generate and return the payment link message.
        
        This is called when entering AWAITING_PAYMENT state or on resend request.
        """
        order_id = self.session.get_context('pending_order_id')
        if not order_id:
            return "Something went wrong. Order not found."

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return "Order not found."

        # Initialize Paystack transaction
        try:
            # Paystack requires email. User email should be in user profile now.
            email = self.user.email or f"{self.user.wa_id}@whatsapp.bot"
            phone = self.session.get_context('delivery_phone')
            
            paystack_data = paystack_client.initialize_transaction(
                email=email,
                amount_minor=order.total_minor,
                reference=order.reference,
                metadata={
                    'order_id': order.id,
                    'phone': phone
                }
            )
            
            payment_url = paystack_data.get('authorization_url')
            
            # Store paystack reference for redundant tracking
            order.paystack_reference = paystack_data.get('reference')
            order.save(update_fields=['paystack_reference'])

            return (
                f"💳 *Payment Required*\n\n"
                f"Order: {order.reference}\n"
                f"Total: {order.total_display}\n\n"
                f"Please click the link below to pay securely via Paystack:\n"
                f"{payment_url}\n\n"
                f"Once paid, your order will be processed automatically."
            )
            
        except Exception as e:
            logger.error(f"Failed to generate Paystack link: {e}")
            return (
                f"⚠️ Sorry, we couldn't generate a payment link at the moment.\n\n"
                f"Error: {str(e)}\n\n"
                f"Please try again by typing 'link' or contact support."
            )


class PaymentConfirmedHandler(BaseHandler):
    """
    Handler for PAYMENT_CONFIRMED state.
    
    Order is paid - show confirmation and offer to start new order.
    """

    def handle(self, message: str) -> HandlerResult:
        """Handle post-payment messages."""
        global_result = self.check_global_keyword(message)
        if global_result:
            return global_result

        normalized = self.normalize_input(message)
        
        # Handle new order request
        if normalized in ('menu', 'new order', 'order', 'again', 'yes'):
            # Create new cart
            cart = Order.get_or_create_cart(self.user)
            self.session.current_order = cart
            self.session.clear_context()
            self.session.save(update_fields=['current_order', 'context'])
            
            return HandlerResult(
                next_state=ConversationState.START
            )

        # Default - offer to start new order
        return HandlerResult(
            messages=[
                "Thank you for your order! 🎉\n\n"
                "Would you like to place another order?\n"
                "Reply 'menu' to browse our menu."
            ],
            next_state=ConversationState.PAYMENT_CONFIRMED
        )
