import sqlite3
import datetime
from typing import Optional, List, Dict, Any, Union
import os  # Import os module


class Database:
    def __init__(self, db_file: str):
        """Initialize database connection and create tables."""
        self.db_file = db_file
        self.conn = self._get_connection()  # Store connection as instance attribute
        self._create_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """Establish and return a database connection."""
        absolute_db_path = os.path.abspath(self.db_file)  # Get absolute path
        print(f"Attempting to connect to database file (absolute): {absolute_db_path}")  # Print absolute path
        conn = sqlite3.connect(absolute_db_path)  # Use absolute path
        conn.row_factory = sqlite3.Row  # For accessing rows as dictionaries
        return conn

    def _create_tables(self) -> None:
        """Create database tables (users, categories, expenses) if they don't exist."""
        cursor = self.conn.cursor()

        # Users table (Blueprint)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Categories table (Blueprint)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            icon TEXT DEFAULT '💰'
        )
        """)
        # Insert default categories (Blueprint - data directly in SQL)
        default_categories = [
            ('Food', '🍔'),
            ('Transport', '🚌'),
            ('Shopping', '🛍️'),
            ('Entertainment', '🎮'),
            ('Bills', '📄'),
            ('Health', '💊'),
            ('Other', '📦')
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO categories (name, icon) VALUES (?, ?)",
            default_categories
        )

        # Expenses table (Blueprint)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category_id INTEGER NOT NULL,
            description TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
        """)
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_expenses_user_date
        ON expenses (user_id, date)
        """)  # Index for performance

        self.conn.commit()  # Commit table creation

    def close_connection(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    # --- User Management ---
    def add_user(self, user_id: int, username: Optional[str] = None, first_name: Optional[str] = None, last_name: Optional[str] = None) -> None:
        """Add a new user to the database or update existing user info."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = COALESCE(?, username),
                first_name = COALESCE(?, first_name),
                last_name = COALESCE(?, last_name)
        """, (user_id, username, first_name, last_name, username, first_name, last_name))  # Parameterized query
        self.conn.commit()

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve user data by user ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))  # Parameterized query
        user_row = cursor.fetchone()  # Fetch one result

        if user_row:
            return dict(user_row)  # Convert sqlite3.Row to dictionary
        else:
            return None  # User not found

    # --- Category Management ---
    def get_categories(self) -> List[Dict[str, Any]]:
        """Retrieve all expense categories."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY name")  # Select all categories, ordered by name
        category_rows = cursor.fetchall()  # Fetch all results

        categories_list = []
        for row in category_rows:
            categories_list.append(dict(row))  # Convert each sqlite3.Row to a dictionary

        return categories_list

    def get_category_by_name(self, category_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a category by its name."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE name = ?", (category_name,))  # Select category by name
        category_row = cursor.fetchone()  # Fetch one result

        if category_row:
            return dict(category_row)  # Convert sqlite3.Row to dictionary
        else:
            return None  # Category not found

    def get_category(self, category_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a category by its ID."""
        conn = self._get_connection()  # Get connection - using per-operation connection for now
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))  # Select by ID
        category_row = cursor.fetchone()
        conn.close()  # Close connection after operation

        if category_row:
            return dict(category_row)
        else:
            return None

    # --- Expense Management ---
    def add_expense(self, user_id: int, amount: float, category_id: int, description: Optional[str] = None,
                    date: Optional[str] = None) -> int:
        """Add a new expense record to the database."""
        conn = self._get_connection()  # Get connection
        cursor = conn.cursor()

        if date is None:
            date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Default to current timestamp

        cursor.execute("""
              INSERT INTO expenses (user_id, amount, category_id, description, date)
              VALUES (?, ?, ?, ?, ?)
          """, (user_id, amount, category_id, description, date))  # Parameterized query

        expense_id = cursor.lastrowid  # Get the ID of the last inserted row
        conn.commit()  # Commit transaction
        conn.close()  # Close connection

        return expense_id  # Return the expense ID

    def get_user_expenses(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve a list of recent expenses for a specific user."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
               SELECT e.id, e.amount, e.date, e.description, c.name as category_name, c.icon as category_icon
               FROM expenses e
               JOIN categories c ON e.category_id = c.id
               WHERE e.user_id = ?
               ORDER BY e.date DESC
               LIMIT ?
           """, (user_id, limit))  # Parameterized query with user_id and limit

        expenses_rows = cursor.fetchall()
        conn.close()

        expenses_list = []
        for row in expenses_rows:
            expenses_list.append(dict(row))  # Convert each sqlite3.Row to a dictionary

        return expenses_list



    def get_user_expense_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get expense statistics for a user for the last N days."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Calculate date range for the last N days
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S') # Format for SQL query
        end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

        # Query to get total spending in the given period
        cursor.execute("""
            SELECT SUM(amount) as total_spending
            FROM expenses
            WHERE user_id = ? AND date BETWEEN ? AND ?
        """, (user_id, start_date_str, end_date_str))
        total_spending_row = cursor.fetchone()
        total_spending = total_spending_row['total_spending'] or 0.0 # Default to 0 if no spending

        # Query to get spending by category in the given period
        cursor.execute("""
            SELECT c.name as category_name, c.icon as category_icon, SUM(e.amount) as category_total
            FROM expenses e
            JOIN categories c ON e.category_id = c.id
            WHERE e.user_id = ? AND e.date BETWEEN ? AND ?
            GROUP BY c.id
            ORDER BY category_total DESC
        """, (user_id, start_date_str, end_date_str))
        category_spending_rows = cursor.fetchall()
        category_spending = []
        for row in category_spending_rows:
            category_spending.append(dict(row)) # Convert to list of dictionaries

        conn.close()

        return {
            'total_spending': total_spending,
            'category_spending': category_spending,
            'period_days': days
        }


    def bulk_add_expenses(self, user_id: int, expenses: List[Dict[str, Any]]) -> List[int]:
        """Add multiple expense records at once (e.g., from CSV)."""
        pass  # Blueprint