"""
Conversation state definitions.

Defines all possible states in the ordering conversation FSM.
Using str Enum for easy serialization to/from database.
"""
from enum import Enum


class ConversationState(str, Enum):
    """
    All possible conversation states.
    
    The FSM progresses through these states based on user input.
    Each state maps to a handler class that processes messages.
    
    State flow:
    START -> SHOW_MENU -> SELECT_CATEGORY -> SHOW_ITEMS -> SELECT_QUANTITY
                                                              |
    PAYMENT_CONFIRMED <- AWAITING_PAYMENT <- CONFIRM_ORDER <- VIEW_CART
    """
    # Initial/greeting state
    START = 'start'
    
    # Menu browsing states
    SHOW_MENU = 'show_menu'
    SELECT_CATEGORY = 'select_category'
    SHOW_ITEMS = 'show_items'
    SELECT_QUANTITY = 'select_quantity'
    
    # Cart and checkout states
    VIEW_CART = 'view_cart'
    COLLECT_ADDRESS = 'collect_address'
    COLLECT_EMAIL = 'collect_email'
    COLLECT_PHONE = 'collect_phone'
    CONFIRM_ORDER = 'confirm_order'
    
    # Payment states
    AWAITING_PAYMENT = 'awaiting_payment'
    PAYMENT_CONFIRMED = 'payment_confirmed'

    @classmethod
    def from_string(cls, value: str) -> 'ConversationState':
        """Convert string to state enum, defaulting to START if invalid."""
        try:
            return cls(value)
        except ValueError:
            return cls.START
