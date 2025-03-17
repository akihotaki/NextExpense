# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_FILE_PATH = "../data/budget.db" # Using DATABASE_FILE_PATH for clarity
DEFAULT_EXPENSE_AMOUNTS = [5, 10, 20, 50, 100]