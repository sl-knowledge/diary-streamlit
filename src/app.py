import streamlit as st
import sqlite3
from datetime import datetime
import json
from pathlib import Path
import uuid
import shutil
import logging
import os
from src.config import Config

# Add these constants at the top
UPLOAD_DIR = Path("data/uploads")
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp'}

logging.basicConfig(level=logging.DEBUG if Config.DEBUG else logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Initialize SQLite database"""
    try:
        logger.debug("Initializing database...")
        logger.debug(f"Database path: {Path('data/diary.db').absolute()}")
        
        Path("data").mkdir(exist_ok=True)
        
        db = sqlite3.connect('data/diary.db')
        
        # 强制删除旧表
        logger.debug("Dropping existing table if any...")
        db.execute("DROP TABLE IF EXISTS entries")
        db.commit()
        
        logger.debug("Creating table 'entries'...")
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA journal_mode = WAL")
        
        # 创建新表
        db.execute('''
            CREATE TABLE entries (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                type TEXT DEFAULT 'diary',
                attachments TEXT,
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()
        
        # 添加测试数据（仅在开发环境）
        if Config.DEBUG:
            logger.debug("Adding test entry...")
            db.execute('''
                INSERT INTO entries (id, date, title, content, type, attachments, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()),
                datetime.now().strftime('%Y-%m-%d'),
                'Test Entry',
                'This is a test entry',
                'diary',
                '[]',
                '{}'
            ))
            db.commit()
            
        logger.debug("Database initialized successfully")
        return db
    except sqlite3.OperationalError as e:
        logger.error(f"Database initialization error: {e}", exc_info=True)
        st.error(f"Database error: {e}")
        st.info("Try restarting the application or check data directory permissions")
        return None

def init_directories():
    """Initialize required directories"""
    Path("data").mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)

def save_uploaded_file(uploaded_file):
    """Save uploaded file and return the path"""
    if uploaded_file is None:
        return None
        
    # Create unique filename
    file_extension = Path(uploaded_file.name).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        st.error(f"Unsupported file type: {file_extension}")
        return None
        
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save the file
    with open(file_path, "wb") as f:
        shutil.copyfileobj(uploaded_file, f)
        
    return str(file_path.relative_to(Path("data")))

def save_entry(title, content, uploaded_files):
    """Save entry with attachments"""
    db = init_db()
    entry_id = str(uuid.uuid4())
    
    # Save uploaded files
    attachment_paths = []
    if uploaded_files:
        for file in uploaded_files:
            path = save_uploaded_file(file)
            if path:
                attachment_paths.append(path)
    
    # Save entry to database
    db.execute('''
        INSERT INTO entries (id, date, title, content, type, attachments, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        entry_id,
        datetime.now().strftime('%Y-%m-%d'),
        title,
        content,
        'diary',
        json.dumps(attachment_paths),
        '{}'
    ))
    db.commit()
    db.close()

def init_app():
    """Initialize application directories and database"""
    try:
        logger.debug(f"Current working directory: {Path.cwd()}")
        logger.debug(f"Data directory path: {Path('data').absolute()}")
        logger.debug(f"User running process: {os.getuid()}:{os.getgid()}")
        
        Path("data").mkdir(exist_ok=True)
        UPLOAD_DIR.mkdir(exist_ok=True)
        
        return True
    except Exception as e:
        logger.error(f"Initialization error: {e}", exc_info=True)
        return False

def main():
    st.set_page_config(page_title="Personal Journal", layout="wide")
    
    # Initialize app first
    if not init_app():
        st.error("Failed to initialize application. Please check permissions and try again.")
        return
        
    # Continue with normal flow
    page = st.sidebar.radio("Navigate", ["Timeline", "New Entry", "Web Clipper"])
    
    if page == "Timeline":
        show_timeline()
    elif page == "New Entry":
        show_editor()
    else:
        show_clipper()

def show_timeline():
    st.title("Timeline")
    
    # Date filter
    col1, col2 = st.columns([2, 3])
    with col1:
        selected_date = st.date_input("Filter by date", datetime.now())
    
    # Display entries
    entries = get_entries_by_date(selected_date)
    for entry in entries:
        with st.expander(f"{entry['date']} - {entry['title']}", expanded=False):
            st.markdown(entry['content'])
            
            # Display attachments if any
            attachments = json.loads(entry['attachments'] or '[]')
            if attachments:
                cols = st.columns(4)
                for idx, attachment in enumerate(attachments):
                    with cols[idx % 4]:
                        img_path = Path("data") / attachment
                        if img_path.exists():
                            st.image(str(img_path), use_column_width=True)

def show_editor():
    st.title("New Entry")
    
    # Basic editor
    title = st.text_input("Title")
    content = st.text_area("Content", height=300)
    
    # Attachments with preview
    uploaded_files = st.file_uploader(
        "Add images", 
        accept_multiple_files=True,
        type=list(ext.replace('.', '') for ext in ALLOWED_EXTENSIONS)
    )
    
    # Preview uploaded images
    if uploaded_files:
        cols = st.columns(4)
        for idx, file in enumerate(uploaded_files):
            with cols[idx % 4]:
                st.image(file, use_column_width=True)
    
    if st.button("Save"):
        if not title:
            st.error("Please enter a title")
            return
        save_entry(title, content, uploaded_files)
        st.success("Entry saved!")

def show_clipper():
    st.title("Web Clipper")
    url = st.text_input("Enter URL")
    if url:
        # Preview implementation will come later
        st.info("Web clipping feature coming soon!")

def get_entries_by_date(selected_date):
    """Get entries for a specific date"""
    logger.debug(f"Fetching entries for date: {selected_date}")
    
    db = init_db()
    if not db:
        logger.error("Failed to initialize database")
        return []
        
    try:
        date_str = selected_date.strftime('%Y-%m-%d')
        logger.debug(f"Formatted date: {date_str}")
        
        # 添加数据库连接验证
        logger.debug("Testing database connection...")
        test_cursor = db.execute("SELECT 1")
        test_cursor.fetchone()
        logger.debug("Database connection successful")
        
        # 检查表是否存在
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entries'")
        if not cursor.fetchone():
            logger.error("Table 'entries' does not exist")
            return []
            
        # 检查是否有数据
        cursor = db.execute('SELECT COUNT(*) FROM entries')
        count = cursor.fetchone()[0]
        logger.debug(f"Total entries in database: {count}")
        
        # 执行原始查询
        cursor = db.execute('''
            SELECT id, date, title, content, attachments
            FROM entries
            WHERE date = ?
            ORDER BY date DESC
        ''', (date_str,))
        
        entries = [dict(zip(['id', 'date', 'title', 'content', 'attachments'], row))
                  for row in cursor.fetchall()]
        
        logger.debug(f"Found {len(entries)} entries for date {date_str}")
        db.close()
        return entries
        
    except sqlite3.Error as e:
        logger.error(f"Database query error: {e}", exc_info=True)
        st.error("Failed to fetch entries")
        if db:
            db.close()
        return []

if __name__ == "__main__":
    main() 