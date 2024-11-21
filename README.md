# Diary App

## Streamlit Cloud Deployment

1. Fork this repository
2. Go to [Streamlit Cloud](https://share.streamlit.io/)
3. Create a new app and select your forked repository
4. Important: Set the "Main file path" to `src/app.py` (not run.py)
5. In the app settings, add the following secrets:
   ```toml
   password = "your-password-here"
   ```
6. Deploy the app
7. The app will automatically generate sample data on first run

## Local Development

1. Clone the repository
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Create `.streamlit/secrets.toml` with your password:
   ```toml
   password = "your-password-here"
   ```
4. Run the app locally:
   ```bash
   # Option 1: Using run.py (recommended for local development)
   python run.py
   
   # Option 2: Direct streamlit run (same as Streamlit Cloud)
   streamlit run src/app.py
   ```

## Features
- Password protection
- Timeline view with date filtering
- Mood and topic analysis
- Multi-language support (中文/English)
- File attachments
- Tag system
