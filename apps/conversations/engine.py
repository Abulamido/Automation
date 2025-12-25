"""
Conversation Engine - FSM Router.

This is the central router that receives messages, determines the current state,
dispatches to the appropriate handler, and manages state transitions.

The engine provides:
1. State-to-handler mapping
2. State transition management
3. Message processing coordination
4. Intro message handling for state entries
"""
import logging
from typing import List, Optional, Type

from .states import ConversationState
from .models import ConversationSession
from .handlers.base import BaseHandler, HandlerResult
from .handlers.start import StartHandler
from .handlers.menu import MenuHandler, CategoryHandler, ItemsHandler, QuantityHandler
from .handlers.cart import CartHandler
from .handlers.checkout import AddressHandler, ConfirmHandler
from .handlers.email import EmailHandler
from .handlers.phone import PhoneHandler
from .handlers.payment import PaymentHandler, PaymentConfirmedHandler

from apps.users.models import UserProfile

logger = logging.getLogger(__name__)


# Maps each state to its handler class
STATE_HANDLERS: dict[ConversationState, Type[BaseHandler]] = {
    ConversationState.START: StartHandler,
    ConversationState.SHOW_MENU: MenuHandler,
    ConversationState.SELECT_CATEGORY: CategoryHandler,
    ConversationState.SHOW_ITEMS: ItemsHandler,
    ConversationState.SELECT_QUANTITY: QuantityHandler,
    ConversationState.VIEW_CART: CartHandler,
    ConversationState.COLLECT_ADDRESS: AddressHandler,
    ConversationState.COLLECT_EMAIL: EmailHandler,
    ConversationState.COLLECT_PHONE: PhoneHandler,
    ConversationState.CONFIRM_ORDER: ConfirmHandler,
    ConversationState.AWAITING_PAYMENT: PaymentHandler,
    ConversationState.PAYMENT_CONFIRMED: PaymentConfirmedHandler,
}


class ConversationEngine:
    """
    Central conversation FSM router.
    
    Coordinates message processing by:
    1. Looking up or creating user session
    2. Checking for duplicate messages (idempotency)
    3. Dispatching to current state's handler
    4. Processing state transitions
    5. Returning response messages
    
    Usage:
        engine = ConversationEngine()
        messages = engine.process_message(wa_id, phone, name, message_text, message_id)
    """

    def process_message(
        self,
        wa_id: str,
        phone_number: str,
        user_name: str,
        message_text: str,
        message_id: str,
    ) -> List[str]:
        """
        Process an incoming WhatsApp message.
        
        This is the main entry point for the conversation engine.
        
        Args:
            wa_id: WhatsApp user ID
            phone_number: User's phone number
            user_name: User's name from WhatsApp profile
            message_text: The message content
            message_id: WhatsApp message ID (for idempotency)
            
        Returns:
            List of response messages to send back
        """
        logger.info(
            f"Processing message from {wa_id}: '{message_text[:50]}...' "
            f"(id: {message_id})"
        )

        # Get or create user profile
        user = UserProfile.get_or_create_from_whatsapp(
            wa_id=wa_id,
            phone_number=phone_number,
            name=user_name
        )

        # Get or create conversation session
        session = ConversationSession.get_or_create_for_user(user)

        # Idempotency check - reject duplicate messages
        if session.is_duplicate_message(message_id):
            logger.warning(f"Duplicate message {message_id} - ignoring")
            return []

        # Mark message as processed
        session.mark_message_processed(message_id)

        # Get current state
        current_state = session.state
        logger.debug(f"Current state: {current_state.value}")

        # Get handler for current state
        handler_class = STATE_HANDLERS.get(current_state)
        if not handler_class:
            logger.error(f"No handler found for state {current_state}")
            session.reset()
            handler_class = StartHandler

        # Instantiate handler and process message
        handler = handler_class(session)
        result = handler.handle(message_text)

        # Collect response messages
        response_messages = list(result.messages)

        # Process state transition if specified
        if result.next_state and result.next_state != current_state:
            logger.info(
                f"State transition: {current_state.value} -> {result.next_state.value}"
            )
            
            # Apply context updates from handler
            session.transition_to(result.next_state, result.context_updates)
            
            # Get intro message for new state (if any)
            new_handler_class = STATE_HANDLERS.get(result.next_state)
            if new_handler_class and new_handler_class != handler_class:
                new_handler = new_handler_class(session)
                intro = new_handler.get_intro_message()
                if intro:
                    response_messages.append(intro)
        else:
            # No state change, but still apply context updates
            if result.context_updates:
                session.context.update(result.context_updates)
                session.save(update_fields=['context', 'updated_at'])

        logger.info(f"Returning {len(response_messages)} message(s)")
        return response_messages

    def get_user_session(self, wa_id: str) -> Optional[ConversationSession]:
        """
        Get existing session for a user (for external lookups).
        
        Args:
            wa_id: WhatsApp user ID
            
        Returns:
            ConversationSession if exists, None otherwise
        """
        try:
            user = UserProfile.objects.get(wa_id=wa_id)
            return ConversationSession.objects.get(user=user)
        except (UserProfile.DoesNotExist, ConversationSession.DoesNotExist):
            return None

    def reset_user_session(self, wa_id: str) -> bool:
        """
        Reset a user's conversation session.
        
        Args:
            wa_id: WhatsApp user ID
            
        Returns:
            True if reset, False if session not found
        """
        session = self.get_user_session(wa_id)
        if session:
            session.reset()
            logger.info(f"Reset session for {wa_id}")
            return True
        return False


# Singleton instance for convenience
conversation_engine = ConversationEngine()
