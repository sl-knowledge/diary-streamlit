import streamlit as st
from config import Config

def main():
    st.set_page_config(
        page_title="Streamlit App",
        page_icon="🚀",
        layout="wide"
    )
    
    st.title("Streamlit App")
    
    if Config.DEBUG:
        st.write("Running in development mode")
        # Safely show secrets in debug mode
        st.write("Database:", Config.DB_HOST)
    
    st.write("Hello, this is a test!")
    
    st.write(f"Test var: {Config.TEST_VAR}")

if __name__ == "__main__":
    main() 