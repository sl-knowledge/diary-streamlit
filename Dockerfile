FROM sl/streamlit-base:latest

WORKDIR /app

# Install sudo and set up permissions
USER root
RUN apt-get update && apt-get install -y sudo && \
    echo "vscode ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create data directory and set permissions
RUN mkdir -p /app/data /app/data/uploads && \
    chown -R vscode:vscode /app

# Copy requirements first (better layer caching)
COPY --chown=vscode:vscode requirements.txt .

# Switch to vscode user for pip install
USER vscode

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=vscode:vscode . .

# Create Python package
RUN touch src/__init__.py

# Set environment variables
ENV PYTHONPATH="/app:${PYTHONPATH}"
ENV PATH="/home/vscode/.local/bin:${PATH}"

# Expose port
EXPOSE 8501

# Run application
CMD ["streamlit", "run", "src/app.py", "--server.address", "0.0.0.0"] 
