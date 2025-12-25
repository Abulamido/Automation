"""
Menu browsing state handlers.

Handles category selection, item listing, and quantity selection.
These states form the core menu navigation flow.
"""
from typing import Optional
from .base import BaseHandler, HandlerResult
from apps.conversations.states import ConversationState
from apps.catalog.models import Category, MenuItem
from apps.orders.models import Order
from apps.orders.services import CartService


class MenuHandler(BaseHandler):
    """
    Handler for SHOW_MENU state.
    
    Displays menu categories and expects numeric selection.
    """

    def handle(self, message: str) -> HandlerResult:
        """Handle category selection or navigation commands."""
        global_result = self.check_global_keyword(message)
        if global_result:
            return global_result

        normalized = self.normalize_input(message)
        
        # Handle 'cart' keyword
        if normalized == 'cart':
            return HandlerResult(
                next_state=ConversationState.VIEW_CART
            )

        # Get categories for validation
        categories = list(Category.get_active_categories())
        
        # Try to parse as category selection
        choice = self.parse_numeric_choice(message, len(categories))
        
        if choice:
            selected_category = categories[choice - 1]
            return HandlerResult(
                next_state=ConversationState.SHOW_ITEMS,
                context_updates={'selected_category_id': selected_category.id}
            )
        
        # Invalid input - show menu again
        return HandlerResult(
            messages=[self._build_menu_message(categories)],
            next_state=ConversationState.SELECT_CATEGORY
        )

    def _build_menu_message(self, categories) -> str:
        """Build category menu message."""
        if not categories:
            return "No menu categories available. Please check back later."
            
        category_list = "\n".join(
            f"{i}. {cat.name}" 
            for i, cat in enumerate(categories, 1)
        )
        
        return (
            f"📋 Menu Categories:\n\n"
            f"{category_list}\n\n"
            f"Reply with a number to see items."
        )


class CategoryHandler(BaseHandler):
    """
    Handler for SELECT_CATEGORY state.
    
    Expects numeric selection from displayed categories.
    """

    def handle(self, message: str) -> HandlerResult:
        """Handle category selection."""
        global_result = self.check_global_keyword(message)
        if global_result:
            return global_result

        normalized = self.normalize_input(message)
        
        # Handle 'cart' keyword
        if normalized == 'cart':
            return HandlerResult(
                next_state=ConversationState.VIEW_CART
            )

        # Get categories
        categories = list(Category.get_active_categories())
        choice = self.parse_numeric_choice(message, len(categories))
        
        if choice:
            selected_category = categories[choice - 1]
            return HandlerResult(
                next_state=ConversationState.SHOW_ITEMS,
                context_updates={'selected_category_id': selected_category.id}
            )
        
        # Invalid input
        category_list = "\n".join(
            f"{i}. {cat.name}" 
            for i, cat in enumerate(categories, 1)
        )
        
        return HandlerResult(
            messages=[
                f"Please reply with a valid number (1-{len(categories)}).\n\n"
                f"{category_list}"
            ],
            next_state=ConversationState.SELECT_CATEGORY
        )


class ItemsHandler(BaseHandler):
    """
    Handler for SHOW_ITEMS state.
    
    Displays items in selected category and handles item selection.
    """

    def handle(self, message: str) -> HandlerResult:
        """Handle item selection or navigation."""
        global_result = self.check_global_keyword(message)
        if global_result:
            return global_result

        normalized = self.normalize_input(message)
        
        # Navigation keywords
        if normalized == 'cart':
            return HandlerResult(
                next_state=ConversationState.VIEW_CART
            )
        
        if normalized in ('back', 'categories', 'menu'):
            return HandlerResult(
                messages=[self._build_categories_message()],
                next_state=ConversationState.SELECT_CATEGORY,
                context_updates={'selected_category_id': None}
            )

        # Get current category
        category_id = self.session.get_context('selected_category_id')
        if not category_id:
            return HandlerResult(
                messages=["Please select a category first."],
                next_state=ConversationState.SELECT_CATEGORY
            )

        # Get items in category
        items = list(MenuItem.get_available_items(category_id))
        
        if not items:
            return HandlerResult(
                messages=[
                    "No items available in this category.\n\n"
                    "Type 'back' to see categories."
                ],
                next_state=ConversationState.SHOW_ITEMS
            )

        # Check for item selection
        choice = self.parse_numeric_choice(message, len(items))
        
        if choice:
            selected_item = items[choice - 1]
            return HandlerResult(
                messages=[
                    f"You selected: {selected_item.name} ({selected_item.price_display})\n\n"
                    f"How many would you like? (Enter 1-10)"
                ],
                next_state=ConversationState.SELECT_QUANTITY,
                context_updates={'selected_item_id': selected_item.id}
            )
        
        # Invalid input - show items again
        return HandlerResult(
            messages=[self._build_items_message(items, category_id)],
            next_state=ConversationState.SHOW_ITEMS
        )

    def _build_categories_message(self) -> str:
        """Build category listing message."""
        categories = Category.get_active_categories()
        category_list = "\n".join(
            f"{i}. {cat.name}" 
            for i, cat in enumerate(categories, 1)
        )
        return f"📋 Menu Categories:\n\n{category_list}\n\nReply with a number."

    def _build_items_message(self, items, category_id) -> str:
        """Build item listing message."""
        try:
            category = Category.objects.get(id=category_id)
            category_name = category.name
        except Category.DoesNotExist:
            category_name = "Items"

        item_list = "\n".join(
            f"{i}. {item.name} - {item.price_display}"
            for i, item in enumerate(items, 1)
        )
        
        return (
            f"🍽️ {category_name}:\n\n"
            f"{item_list}\n\n"
            f"Reply with item number to add to cart, or 'back' for categories."
        )

    def get_intro_message(self) -> Optional[str]:
        """Show items when entering this state."""
        category_id = self.session.get_context('selected_category_id')
        if not category_id:
            return None
            
        items = list(MenuItem.get_available_items(category_id))
        return self._build_items_message(items, category_id)


class QuantityHandler(BaseHandler):
    """
    Handler for SELECT_QUANTITY state.
    
    Collects quantity for selected item and adds to cart.
    """

    def handle(self, message: str) -> HandlerResult:
        """Handle quantity input."""
        global_result = self.check_global_keyword(message)
        if global_result:
            return global_result

        normalized = self.normalize_input(message)
        
        # Allow cancellation
        if normalized in ('cancel', 'back', 'no'):
            category_id = self.session.get_context('selected_category_id')
            return HandlerResult(
                messages=["Cancelled. Returning to items."],
                next_state=ConversationState.SHOW_ITEMS,
                context_updates={'selected_item_id': None}
            )

        # Get selected item
        item_id = self.session.get_context('selected_item_id')
        if not item_id:
            return HandlerResult(
                messages=["No item selected. Please select an item first."],
                next_state=ConversationState.SHOW_ITEMS
            )

        try:
            menu_item = MenuItem.objects.get(id=item_id, is_active=True, is_available=True)
        except MenuItem.DoesNotExist:
            return HandlerResult(
                messages=["Item is no longer available. Please select another."],
                next_state=ConversationState.SHOW_ITEMS,
                context_updates={'selected_item_id': None}
            )

        # Parse quantity
        quantity = self.parse_numeric_choice(message, 10)  # Max 10 per add
        
        if not quantity:
            return HandlerResult(
                messages=["Please enter a valid quantity (1-10)."],
                next_state=ConversationState.SELECT_QUANTITY
            )

        # Add to cart
        cart = self.session.current_order
        if not cart:
            cart = Order.get_or_create_cart(self.user)
            self.session.current_order = cart
            self.session.save(update_fields=['current_order'])

        try:
            CartService.add_item(cart, menu_item, quantity)
        except ValueError as e:
            return HandlerResult(
                messages=[str(e)],
                next_state=ConversationState.SHOW_ITEMS
            )

        # Success - show confirmation and category items
        cart_summary = CartService.get_cart_summary(cart)
        
        return HandlerResult(
            messages=[
                f"✅ Added {quantity}x {menu_item.name} to your cart.\n\n"
                f"Cart total: {cart_summary['total']} ({cart_summary['item_count']} items)\n\n"
                f"Reply with another item number, 'cart' to checkout, or 'back' for categories."
            ],
            next_state=ConversationState.SHOW_ITEMS,
            context_updates={'selected_item_id': None}
        )
