FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create user with same UID/GID as host user
RUN groupadd -g 1000 sshuser && \
    useradd -u 1000 -g 1000 -m -s /bin/bash sshuser

# Create data directory and set permissions
RUN mkdir -p /app/data /app/data/uploads && \
    chown -R sshuser:sshuser /app && \
    chmod 777 /app/data

# Copy requirements first
COPY --chown=sshuser:sshuser requirements.txt .

# Switch to sshuser
USER sshuser

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=sshuser:sshuser . .

# Create Python package
RUN touch src/__init__.py

# Set environment variables
ENV PYTHONPATH=/app
ENV PATH=/home/sshuser/.local/bin:${PATH}

# Expose port
EXPOSE 8501

# Run application
CMD ["streamlit", "run", "src/app.py", "--server.address", "0.0.0.0"] 
