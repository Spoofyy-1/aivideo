# Multi-stage build to get ffmpeg
FROM jrottenberg/ffmpeg:4.4-ubuntu2004 as ffmpeg

# Main Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy ffmpeg binaries from the ffmpeg stage
COPY --from=ffmpeg /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg /usr/local/bin/ffprobe /usr/local/bin/ffprobe

# Install Python dependencies directly
RUN pip install --no-cache-dir \
    replicate==0.22.0 \
    python-dotenv==1.0.1 \
    requests==2.31.0 \
    flask==3.0.2 \
    openai==1.12.0 \
    moviepy==1.0.3 \
    beautifulsoup4==4.12.3 \
    python-slugify==8.0.4 \
    flask-cors==4.0.0 \
    numpy==1.26.4 \
    gunicorn==21.2.0

# Copy all application files
COPY backend/. .

# Create static directory for generated files
RUN mkdir -p static/generated

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "app.py"] 