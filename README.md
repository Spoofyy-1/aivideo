# AI Video Ad Generator

A full-stack application that generates AI-powered video advertisements using advanced AI models.

## 🚀 Features

- **AI-Powered Ad Generation**: Uses GPT-4, Gemini, and Google's Veo-3 for script and video generation
- **Company Research**: Automatically researches companies and generates detailed reports
- **Multiple Ad Types**: Support for various ad styles (Cinematic, Funny, Emotional, etc.)
- **Instant Download**: Download generated videos and reports immediately
- **Modern UI**: Beautiful, responsive Next.js frontend with custom design system

## 📁 Project Structure

```
├── next-frontend/          # Next.js frontend application
│   ├── src/
│   │   ├── app/           # Next.js app router pages
│   │   ├── components/    # React components
│   │   └── api.js         # API client
│   ├── public/            # Static assets
│   └── vercel.json        # Vercel deployment config
├── backend/               # Python Flask backend
│   ├── app.py            # Main Flask application
│   ├── requirements.txt  # Python dependencies
│   ├── templates/        # Flask templates
│   └── static/           # Static files
├── .gitignore
└── README.md
```

## 🛠️ Setup & Development

### Frontend (Next.js)

```bash
cd next-frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Backend (Python Flask)

```bash
cd backend
pip install -r requirements.txt
python app.py
```

The backend API will be available at `http://localhost:5000`

## 🚀 Deployment

### Frontend (Vercel)
- The frontend is configured for Vercel deployment
- Set the root directory to `next-frontend` in Vercel dashboard
- The `vercel.json` file is already configured

### Backend
- Deploy the `backend/` directory to your preferred Python hosting service
- Ensure all environment variables are set for API keys

## 🔧 Environment Variables

Create appropriate environment files for:
- OpenAI API keys
- Google AI API keys
- Other service credentials

## 📝 License

See LICENSE file for details. 