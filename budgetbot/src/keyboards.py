# src/keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any

# ... (other keyboard functions if you have any) ...

def get_category_selection_keyboard(categories: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Create keyboard for category selection."""
    builder = InlineKeyboardBuilder()

    # Category buttons (one row per category)
    for category in categories:
        builder.button(
            text=f"{category['icon']} {category['name']}",
            callback_data=f"select_category:{category['id']}" # Updated callback data: select_category
        )
    builder.adjust(1) # Arrange category buttons in single columns

    # Cancel button (last row)
    builder.button(
        text="❌ Cancel",
        callback_data="cancel_add_expense" # Callback data for cancel action
    )
    builder.adjust(1) # Cancel button in its own row

    return builder.as_markup()


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for confirming or cancelling an operation."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="✅ Confirm",
        callback_data="confirm_expense"  # Callback data for confirmation
    )

    builder.button(
        text="❌ Cancel",
        callback_data="cancel_confirm_expense" # New callback data for cancel at confirmation
    )

    builder.adjust(2)  # Arrange buttons in one row

    return builder.as_markup()


