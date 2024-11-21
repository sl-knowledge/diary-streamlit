import os
from pathlib import Path

class Config:
    # Get the project root directory
    ROOT_DIR = Path(__file__).parent.parent
    
    # Development mode
    DEBUG = True
    
    # Data directories
    DATA_DIR = ROOT_DIR / "data"
    UPLOAD_DIR = DATA_DIR / "uploads"
    DB_PATH = DATA_DIR / "diary.db"
    
    # Application configuration
    APP_CONFIG = {
        'allowed_extensions': {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx'}
    }
    
    def __init__(self):
        # Create necessary directories if they don't exist
        self.DATA_DIR.mkdir(exist_ok=True, mode=0o755)
        self.UPLOAD_DIR.mkdir(exist_ok=True, mode=0o755)