FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for compiling pyswisseph
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration
COPY pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir .

# Download Swiss Ephemeris files (1800-2400 AD)
# This ensures high precision for production.
RUN mkdir -p /usr/local/share/swisseph && \
    apt-get update && apt-get install -y wget && \
    wget -O /usr/local/share/swisseph/sepl_18.se1 https://github.com/aloistr/swisseph/raw/master/ephe/sepl_18.se1 && \
    wget -O /usr/local/share/swisseph/semo_18.se1 https://github.com/aloistr/swisseph/raw/master/ephe/semo_18.se1 && \
    wget -O /usr/local/share/swisseph/seas_18.se1 https://github.com/aloistr/swisseph/raw/master/ephe/seas_18.se1 && \
    chmod -R 755 /usr/local/share/swisseph

# Set environment variable for pyswisseph (just in case)
ENV SE_EPHE_PATH=/usr/local/share/swisseph

# Copy source code
COPY bazi_engine/ ./bazi_engine/

# Expose port
EXPOSE 8080

# Run the application
CMD ["uvicorn", "bazi_engine.app:app", "--host", "0.0.0.0", "--port", "8080"]
