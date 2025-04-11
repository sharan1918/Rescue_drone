# Use official Python image
FROM python:3.10-slim

# Prevent interactive prompts during install
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies (for OpenCV, PIL, etc.)
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgl1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variable and expose port 8000
ENV PORT=8080
EXPOSE 8080

# Run the app with Gunicorn on port 8080
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
