FROM python:3.12-slim

# Configure pip to work with filtered network (SSL certificate interception)
ENV PIP_TRUSTED_HOST="pypi.org files.pythonhosted.org"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    # Playwright Chromium deps (installed in case Playwright is used later)
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2t64 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python output unbuffered so logs appear immediately in Docker
ENV PYTHONUNBUFFERED=1

# Default port (overridable via docker compose or FLASK_PORT env)
ARG FLASK_PORT=5000
ENV FLASK_PORT=${FLASK_PORT}

# Install Python dependencies (pip uses PIP_TRUSTED_HOST from env)
COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Note: Playwright browser download is skipped due to network restrictions.
# The web app (app.py) doesn't require Playwright — only main.py (shopping bot) does.
# To use the shopping bot, install Chromium manually in the container or on the host.

# Copy application code
COPY . .

# Expose Flask default port
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]
