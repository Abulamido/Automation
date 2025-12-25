"""
Message templates and formatters.

Centralized location for consistent message formatting.
"""

def format_menu_item(item) -> str:
    """Format a single menu item for listing."""
    return f"• {item.name} - {item.price_display}"

def format_cart_summary(summary: dict) -> str:
    """Format the cart summary for display."""
    items_text = "\n".join(
        f"  - {item['quantity']}x {item['name']} ({item['subtotal']})"
        for item in summary['items']
    )
    return (
        f"🛒 *Your Cart*\n"
        f"━━━━━━━━━━━━\n"
        f"{items_text}\n"
        f"━━━━━━━━━━━━\n"
        f"Total: *{summary['total']}*"
    )
