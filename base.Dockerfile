FROM python:3.11-slim

# Install system dependencies and development tools
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    python3-pip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -s /bin/bash vscode
RUN chown -R vscode:vscode /home/vscode

# Install common Python packages you'll use across apps
RUN pip install --upgrade pip
RUN pip install streamlit python-dotenv markdown pandas numpy pypinyin translators yt-dlp jieba

# Switch to non-root user
USER vscode

# Add local bin to PATH
ENV PATH="${PATH}:/home/vscode/.local/bin" 