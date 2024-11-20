import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

class Config:
    DEBUG = os.getenv("ENVIRONMENT") == "development"
    TEST_VAR = os.getenv("TEST_VAR")

    # Streamlit secrets
    try:
        # Database
        DB_HOST = st.secrets["postgres"]["host"]
        DB_PORT = st.secrets["postgres"]["port"]
        DB_NAME = st.secrets["postgres"]["dbname"]
        DB_USER = st.secrets["postgres"]["user"]
        DB_PASS = st.secrets["postgres"]["password"]
        
        # API Keys
        OPENAI_KEY = st.secrets["api_keys"]["openai"]
    except Exception as e:
        if DEBUG:
            print(f"Warning: Some secrets not found: {e}")