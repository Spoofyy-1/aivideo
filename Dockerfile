# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy all files from current directory (which will be backend/ when Railway builds)
COPY . ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create static directory for generated files
RUN mkdir -p static/generated

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "app.py"]