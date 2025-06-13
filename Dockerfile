# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy everything first
COPY . .

# Debug: List files to see what we have
RUN ls -la /app
RUN ls -la /app/backend

# Install dependencies from the backend directory
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend files to app root for easier execution
RUN cp -r /app/backend/* /app/

# Create static directory for generated files
RUN mkdir -p static/generated

# Expose port (Railway will set PORT env var)
EXPOSE 8080

# Run the application
CMD ["python", "app.py"]