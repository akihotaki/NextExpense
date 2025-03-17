# src/states.py
from aiogram.fsm.state import State, StatesGroup

class ExpenseStates(StatesGroup):
    """States for adding a new expense."""
    waiting_for_category = State()
    waiting_for_amount = State()
    waiting_for_description = State() # New state for waiting for description input
    confirming_expense = State()