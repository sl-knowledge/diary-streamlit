import sqlite3
from pathlib import Path
from config import Config

def init_database():
    """Initialize the SQLite database with required tables"""
    config = Config()
    
    # Connect to database (creates it if it doesn't exist)
    conn = sqlite3.connect(str(config.DB_PATH))
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS entries (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            attachments TEXT,
            mood TEXT,
            weather TEXT,
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS entry_tags (
            entry_id TEXT,
            tag_id INTEGER,
            FOREIGN KEY (entry_id) REFERENCES entries(id),
            FOREIGN KEY (tag_id) REFERENCES tags(id),
            PRIMARY KEY (entry_id, tag_id)
        );
        
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id TEXT,
            topic TEXT,
            keywords TEXT,
            sentiment REAL,
            FOREIGN KEY (entry_id) REFERENCES entries(id)
        );
    ''')
    
    conn.commit()
    conn.close()
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database() 