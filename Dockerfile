FROM sl/streamlit-base:latest

WORKDIR /app

# Install app-specific dependencies only
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "src/app.py", "--server.address", "0.0.0.0"] 