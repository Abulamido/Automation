"""
Start/greeting state handler.

This is the initial state for new users or after reset.
Displays a welcome message and transitions to menu.
"""
from .base import BaseHandler, HandlerResult
from apps.conversations.states import ConversationState
from apps.orders.models import Order


class StartHandler(BaseHandler):
    """
    Handler for START state.
    
    Any message from this state triggers:
    1. Welcome message
    2. Menu category display
    3. Transition to SELECT_CATEGORY state
    """

    def handle(self, message: str) -> HandlerResult:
        """
        Handle any message in START state.
        
        Always shows welcome + menu, regardless of message content.
        """
        # Check for global keywords first
        global_result = self.check_global_keyword(message)
        if global_result:
            return global_result

        # Ensure user has a cart
        cart = Order.get_or_create_cart(self.user)
        self.session.current_order = cart
        self.session.save(update_fields=['current_order'])

        # Build welcome message
        welcome = self._build_welcome_message()
        
        return HandlerResult(
            messages=[welcome],
            next_state=ConversationState.SELECT_CATEGORY
        )

    def _build_welcome_message(self) -> str:
        """Build personalized welcome message with menu categories."""
        from apps.catalog.models import Category
        
        name = self.user.name or "there"
        
        # Get active categories
        categories = Category.get_active_categories()
        
        if not categories.exists():
            return (
                f"Welcome, {name}! 🍽️\n\n"
                "Sorry, our menu is currently unavailable. "
                "Please try again later."
            )
        
        # Build category list
        category_list = "\n".join(
            f"{i}. {cat.name}" 
            for i, cat in enumerate(categories, 1)
        )
        
        return (
            f"Welcome to FoodBot, {name}! 🍽️\n\n"
            f"Here are our menu categories:\n\n"
            f"{category_list}\n\n"
            f"Reply with a number to see items, or type 'cart' to view your cart."
        )

    def get_intro_message(self) -> str:
        return "Hi! Send any message to see our menu."
