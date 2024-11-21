# Diary App

## Setup for Streamlit Cloud

1. Fork this repository
2. Go to [Streamlit Cloud](https://share.streamlit.io/)
3. Create a new app and select your forked repository
4. In the app settings, add the following secrets:
   ```toml
   password = "your-password-here"
   ```
5. Deploy the app
6. The app will automatically generate sample data on first run using `mock_data.py`

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
4. Run the app:
   ```bash
   python run.py
   ``` 