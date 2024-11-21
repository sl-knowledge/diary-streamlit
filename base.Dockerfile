FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and development tools
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    python3-pip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install common Python packages
RUN pip install --upgrade pip
RUN pip install streamlit python-dotenv markdown pandas numpy yt-dlp translators jieba wordcloud matplotlib streamlit-timeline plotly

# Create a non-root user
RUN useradd -m -s /bin/bash vscode && \
    chown -R vscode:vscode /home/vscode

# Create app directories
RUN mkdir -p /app/data && \
    chown -R vscode:vscode /app

VOLUME ["/app/data"]

# Switch to non-root user
USER vscode

# Add local bin to PATH
ENV PATH="${PATH}:/home/vscode/.local/bin" 