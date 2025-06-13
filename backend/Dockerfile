# Multi-stage build to get ffmpeg
FROM jrottenberg/ffmpeg:4.4-ubuntu2004 as ffmpeg

# Main Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy ffmpeg binaries from the ffmpeg stage
COPY --from=ffmpeg /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg /usr/local/bin/ffprobe /usr/local/bin/ffprobe

# Copy requirements file first for better caching
COPY requirements.txt .

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Create static directory for generated files
RUN mkdir -p static/generated

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "app.py"] 