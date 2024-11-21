FROM diary-base:latest

WORKDIR /app

# Switch back to root for system updates
USER root

# Install system dependencies
RUN apt-get update && apt-get install -y sqlite3 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements first
COPY requirements.txt .
RUN pip install -r requirements.txt

# Switch back to vscode user
USER vscode

EXPOSE 8501

CMD ["streamlit", "run", "src/app.py", "--server.address", "0.0.0.0"] 
