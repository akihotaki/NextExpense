import asyncio
import logging
import datetime

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove  # Import ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext  # Import FSMContext

import config
from database import Database
import keyboards
from states import ExpenseStates  # Import ExpenseStates from states.py

# Configure logging
logging.basicConfig(level=logging.INFO)

async def main():
    """Main function to set up and run the bot."""
    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    main_router = Router()
    dp.include_router(main_router)

    expense_callback_router = Router()
    dp.include_router(expense_callback_router)

    db = Database(config.DATABASE_FILE_PATH)

    # Command handler for /start command
    @main_router.message(CommandStart())
    async def cmd_start(message: Message):
        """Handle the /start command."""
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name

        user = db.get_user(user_id)  # Try to get existing user

        if user:
            welcome_message = f"👋 Welcome back, <b>{user['first_name'] or user['username'] or 'User'}</b>!\n\n"  # Personalized welcome
        else:
            db.add_user(user_id, username, first_name, last_name)  # Add new user if not found
            welcome_message = f"👋 Welcome to Budget Tracker Bot!\n\n"  # Initial welcome

        welcome_message += "I'm here to help you track your expenses and manage your budget effectively.\n\n"
        welcome_message += "Use the buttons below to get started:"  # Placeholder for keyboard later

        await message.answer(welcome_message, parse_mode=ParseMode.HTML)  # Send welcome message with HTML formatting

    # Command handler for /help command
    @main_router.message(Command("help"))
    async def cmd_help(message: Message):
        """Handle the /help command."""
        help_text = """
📚 <b>Budget Tracker Bot Help</b>

Here's what I can help you with:

• <b>Add Expense</b>: Track your spending quickly and easily.
• <b>Statistics</b>: View summaries and charts of your spending habits.
• <b>Recent Expenses</b>: See a list of your latest recorded expenses.

Use the buttons below to navigate, or use these commands:

/start - Start or restart the bot
/add - Begin adding a new expense
/stats - View your spending statistics
/recent - See recent expenses
/help - Show this help message
"""
        await message.answer(help_text, parse_mode=ParseMode.HTML)

    # Command handler for /add command
    @main_router.message(Command("add"))
    async def cmd_add_expense(message: Message, state: FSMContext):  # Add state: FSMContext parameter
        """Handle the /add command to start adding an expense."""
        categories = db.get_categories()
        category_keyboard = keyboards.get_category_selection_keyboard(categories)  # Generate category keyboard - function name changed

        await state.set_state(ExpenseStates.waiting_for_category)  # Set initial state

        await message.answer(
            "💸 <b>Add Expense</b>\n\n"
            "Please choose a category for your expense:",
            reply_markup=category_keyboard  # Set the generated category keyboard
        )

    @expense_callback_router.callback_query(F.data.startswith("select_category:"))
    async def process_category_selection(callback: CallbackQuery, state: FSMContext):  # Add state: FSMContext parameter
        """Process the category selection from the inline keyboard."""
        await callback.answer()

        category_id_str = callback.data.split(":")[1]
        category_id = int(category_id_str)

        # Store selected category_id in FSM state
        await state.update_data(selected_category_id=category_id)  # Store category_id

        await state.set_state(ExpenseStates.waiting_for_amount)  # Set next state - waiting for amount

        # Prompt user to enter the expense amount
        await callback.message.answer(
            f"✅ Category selected!\n\n"
            f"Now, please enter the <b>expense amount</b> (e.g., 10.5 or 25):",
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardRemove()  # Optionally remove reply keyboard if any
        )

    @expense_callback_router.callback_query(F.data == "cancel_add_expense")
    async def cancel_add_expense_operation(callback: CallbackQuery):
        """Handles the 'cancel' button callback."""
        await callback.answer()  # Acknowledge callback

        await callback.message.edit_text("❌ Add expense operation cancelled.")  # Edit the original message
        # In a real bot, you would also clear any FSM state here if you were using states

    @expense_callback_router.message(ExpenseStates.waiting_for_amount)
    async def process_amount_input(message: Message, state: FSMContext):
        """Process the amount input from the user."""
        amount_text = message.text
        try:
            amount = float(amount_text)
            if amount <= 0:
                await message.answer("Amount must be a positive number. Please try again.")
                return
        except ValueError:
            await message.answer("Invalid amount. Please enter a number (e.g., 10.5 or 25).")
            return

        # Store the entered amount in FSM state
        await state.update_data(amount=amount)

        # Set next state - waiting for description
        await state.set_state(ExpenseStates.waiting_for_description)  # Changed to waiting_for_description

        # Prompt user to enter description
        await message.answer(
            "✍️ <b>Optional:</b> Add a <b>description</b> for this expense (or send '-' to skip):",
            # Updated prompt for description
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardRemove()
        )

    @expense_callback_router.message(ExpenseStates.waiting_for_description)
    async def process_description_input(message: Message, state: FSMContext):
        """Process the description input from the user."""
        description_text = message.text

        if description_text == '-':  # User wants to skip description
            description = None  # Set description to None
        else:
            description = description_text  # Use the entered text as description

        # Store the description in FSM state
        await state.update_data(description=description)

        # Get category_id and amount from state
        user_data = await state.get_data()
        category_id = user_data.get("selected_category_id")
        amount = user_data.get("amount")

        # Get category details from database (for display)
        category = db.get_category(category_id)
        if not category:
            await message.answer("Error: Category not found. Please start again with /add.")
            await state.clear()
            return

        # Set next state - confirming expense
        await state.set_state(ExpenseStates.confirming_expense)

        # Display expense summary with description and ask for confirmation
        confirmation_message = f"🧾 <b>Confirm Expense?</b>\n\n"
        confirmation_message += f"Category: <b>{category['icon']} {category['name']}</b>\n"
        confirmation_message += f"Amount: <b>${amount:.2f}</b>\n"
        if description:  # Add description to confirmation message if provided
            confirmation_message += f"Description: <b>{description}</b>\n"
        confirmation_message += "\nPlease confirm or cancel:"
        confirmation_keyboard = keyboards.get_confirmation_keyboard()
        await message.answer(confirmation_message, parse_mode=ParseMode.HTML, reply_markup=confirmation_keyboard)

    @expense_callback_router.callback_query(F.data == "confirm_expense")
    async def confirm_expense_handler(callback: CallbackQuery, state: FSMContext):
        """Handles the 'confirm' button callback for expense confirmation."""
        await callback.answer()

        user_data = await state.get_data()
        category_id = user_data.get("selected_category_id")
        amount = user_data.get("amount")
        description = user_data.get("description")  # Retrieve description from state

        user_id = callback.from_user.id

        # Add expense to database, now passing description
        expense_id = db.add_expense(user_id=user_id, category_id=category_id, amount=amount,
                                    description=description)  # Pass description

        if expense_id:
            success_message = f"✅ Expense of <b>${amount:.2f}</b> in category confirmed and saved!"  # Base success message
            if description:  # Add description to success message if available
                success_message += f"\nDescription: <b>{description}</b>"
            await callback.message.edit_text(success_message,
                                             parse_mode=ParseMode.HTML)  # Edit confirmation message to success
        else:
            await callback.message.edit_text("❌ Failed to save expense. Please try again.")

        await state.clear()

    @expense_callback_router.callback_query(F.data == "cancel_confirm_expense")
    async def cancel_confirm_expense_handler(callback: CallbackQuery, state: FSMContext):
        """Handles the 'cancel' button callback during expense confirmation."""
        await callback.answer()  # Acknowledge callback

        await callback.message.edit_text("❌ Expense addition cancelled.")  # Edit message to indicate cancellation
        await state.clear()  # Clear FSM state

    # Command handler for /recent command
    @main_router.message(Command("recent"))
    async def cmd_recent_expenses(message: Message):
        """Handle the /recent command to show recent expenses."""
        user_id = message.from_user.id
        recent_expenses = db.get_user_expenses(user_id)  # Get recent expenses from database (default limit=5)

        if not recent_expenses:
            await message.answer("You haven't recorded any expenses yet.")
            return

        expenses_text = "📋 <b>Recent Expenses:</b>\n\n"
        for expense in recent_expenses:
            date_str = datetime.datetime.fromisoformat(expense['date']).strftime("%Y-%m-%d %H:%M")  # Format date
            description_str = f" - {expense['description']}" if expense[
                'description'] else ""  # Add description if available
            expenses_text += f"• <b>{expense['category_icon']} ${expense['amount']:.2f}</b> ({expense['category_name']}){description_str}\n"
            expenses_text += f"  <i>{date_str}</i>\n\n"  # Add date in italics

        await message.answer(expenses_text, parse_mode=ParseMode.HTML)

    @main_router.message(Command("stats"))
    async def cmd_show_statistics(message: Message):
        """Handle the /stats command to show spending statistics."""
        user_id = message.from_user.id

        stats_data = db.get_user_expense_stats(user_id)  # Get statistics data for the user (default 30 days)

        if not stats_data['category_spending']:  # Check if there is any category spending data (implies no expenses)
            await message.answer(
                "📊 <b>Your Spending Statistics (Last 30 Days)</b>\n\nNo expenses recorded for the last 30 days.",
                parse_mode=ParseMode.HTML)
            return

        stats_text = "📊 <b>Your Spending Statistics (Last 30 Days)</b>\n\n"
        stats_text += f"💰 <b>Total Spending:</b> ${stats_data['total_spending']:.2f}\n\n"

        stats_text += "<b> Spendings by category:</b>\n"  # Category spending breakdown heading (in Russian, you can change to English if needed)
        for category_stat in stats_data['category_spending'][:5]:  # Display top 5 categories
            percentage = (category_stat['category_total'] / stats_data['total_spending']) * 100 if stats_data[
                'total_spending'] else 0
            stats_text += f"• {category_stat['category_icon']} <b>{category_stat['category_name']}:</b> ${category_stat['category_total']:.2f} ({percentage:.1f}%)\n"

        await message.answer(stats_text, parse_mode=ParseMode.HTML)

































































    # ------------------ Polling --------------------------
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        db.close_connection()


if __name__ == "__main__":
    logging.info("Starting Budget Tracker Bot")
    asyncio.run(main())