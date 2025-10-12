import sqlite3
import os
from datetime import datetime

def get_db_connection():
    # Use absolute path for Render
    db_path = os.path.join(os.getcwd(), 'campustrade.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    
    # Users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Barters table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS barters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            item TEXT NOT NULL,
            hostel TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Requests table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            item TEXT NOT NULL,
            hostel TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Trade offers table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS trade_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barter_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            barter_item TEXT NOT NULL,
            barter_owner TEXT NOT NULL,
            offerer_name TEXT NOT NULL,
            offerer_mobile TEXT NOT NULL,
            item_description TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (barter_id) REFERENCES barters (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database when module is imported
init_db()