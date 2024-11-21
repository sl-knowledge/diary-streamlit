import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    DEBUG = os.getenv("ENVIRONMENT") == "development"
    TEST_VAR = os.getenv("TEST_VAR")

    # Project root directory
    ROOT_DIR = Path(__file__).parent.parent.absolute()
    # Data directory
    DATA_DIR = ROOT_DIR / 'data'
    # Database file
    DB_PATH = DATA_DIR / 'diary.db'
    # Upload directory
    UPLOAD_DIR = DATA_DIR / 'uploads'

    # Database configuration
    DB_CONFIG = {
        'journal_mode': 'WAL',
        'foreign_keys': 'ON'
    }

    # Application configuration
    APP_CONFIG = {
        'debug': True,
        'allowed_extensions': {'.png', '.jpg', '.jpeg', '.gif', '.bmp'}
    }

    # Streamlit secrets (only load if streamlit is available)
    try:
        import streamlit as st
        # Database
        DB_HOST = st.secrets["postgres"]["host"]
        DB_PORT = st.secrets["postgres"]["port"]
        DB_NAME = st.secrets["postgres"]["dbname"]
        DB_USER = st.secrets["postgres"]["user"]
        DB_PASS = st.secrets["postgres"]["password"]
        
        # API Keys
        OPENAI_KEY = st.secrets["api_keys"]["openai"]
    except ImportError:
        # Running without streamlit
        if DEBUG:
            print("Warning: Streamlit not available, some features will be disabled")
    except Exception as e:
        if DEBUG:
            print(f"Warning: Some secrets not found: {e}")

    # Ensure all necessary directories exist
    def ensure_directories(self):
        """Ensure all necessary directories exist"""
        try:
            self.DATA_DIR.mkdir(exist_ok=True)
            self.UPLOAD_DIR.mkdir(exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating directories: {e}")
            return False