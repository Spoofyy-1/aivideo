# Railway Deployment Instructions (Docker)

## Required Environment Variables

Set these environment variables in your Railway project:

```
OPENAI_API_KEY=your_openai_api_key_here
REPLICATE_API_TOKEN=your_replicate_api_token_here
```

## Deployment Steps

1. **Connect Repository**: Connect your GitHub repository to Railway
2. **Select Root Directory**: Choose the `backend` folder as the root directory
3. **Docker Build**: Railway will automatically detect the Dockerfile and use Docker builder
4. **Set Environment Variables**: Add the required API keys in Railway dashboard
5. **Deploy**: Railway will build the Docker image and deploy automatically

## Docker Configuration

- **Base Image**: Python 3.11 slim
- **System Dependencies**: FFmpeg (for video processing)
- **Port**: Automatically configured via Railway's PORT environment variable
- **Build Process**: Uses multi-stage caching for faster builds

## Files Structure

```
backend/
├── Dockerfile              # Docker build configuration
├── railway.json           # Railway deployment settings
├── .dockerignore          # Files to exclude from Docker build
├── Procfile               # Alternative process definition
├── requirements.txt       # Python dependencies
├── app.py                # Main Flask application
└── ...
```

## API Endpoints

Once deployed, your Railway app will have these endpoints:
- `GET /` - Health check
- `POST /generate` - Generate ad video
- `POST /research` - Research company
- `GET /test` - Test endpoint
- `GET /download/video/<filename>` - Download video
- `GET /download/report/<filename>` - Download report

## Frontend Configuration

Update your frontend API calls to use your Railway URL:
```javascript
const RAILWAY_URL = 'https://your-app-name.railway.app';
```

## Troubleshooting

- **Build Issues**: Check Railway build logs for Docker build errors
- **Runtime Issues**: Check Railway deployment logs for application errors
- **Environment Variables**: Ensure all required API keys are set correctly