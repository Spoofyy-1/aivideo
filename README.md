# AI-Powered Video Ad Generator

This project is an AI-powered video ad generator that creates professional, cinematic advertisements using OpenAI's GPT-4 and Google's Veo-3 model. It analyzes company websites, generates creative ad scripts, and produces high-quality video content automatically.

## Features

- 🔍 **Company Research**: Automatically analyzes company websites to understand their business, products, and brand voice
- ✍️ **AI Script Generation**: Creates engaging, story-driven ad scripts using GPT-4 or Gemini
- 🎥 **Video Generation**: Produces high-quality video content using Google's Veo-3 model
- 🎯 **Customizable**: Supports various ad styles (cinematic, funny, emotional, etc.)
- 🔄 **Smart Retry**: Automatically handles sensitive content and regenerates when needed
- 📊 **Best Practices**: Incorporates learnings from successful ads

## Tech Stack

- **Backend**: Python/Flask
- **AI Models**: 
  - OpenAI GPT-4 for script generation
  - Google Gemini for script improvement
  - Google Veo-3 for video generation
- **Frontend**: HTML/CSS/JavaScript
- **APIs**: OpenAI, Google Gemini, Replicate (Veo-3)

## Prerequisites

- Python 3.8+
- OpenAI API key
- Google Gemini API key
- Replicate API key
- Internet connection

## Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/ai-video-ad-generator.git
   cd ai-video-ad-generator
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file:
   ```bash
   cp .env.example .env
   ```

4. Add your API keys to `.env`:
   ```
   OPENAI_API_KEY=your_openai_api_key
   GEMINI_API_KEY=your_gemini_api_key
   REPLICATE_API_KEY=your_replicate_api_key
   ```

5. Run the application:
   ```bash
   python app.py
   ```

6. Open your browser and navigate to `http://localhost:5000`

## Usage

1. Enter the company website URL
2. Select your preferred ad style
3. (Optional) Provide additional creative direction
4. Click "Generate Ad"
5. Wait for the AI to research, script, and generate your video
6. Download the final video and company report

## Project Structure

```
ai-video-ad-generator/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example          # Example environment variables
├── best_ads.json         # Database of successful ads
├── static/               # Static files (CSS, JS, generated content)
├── templates/            # HTML templates
└── README.md            # This file
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for GPT-4
- Google for Gemini and Veo-3
- Replicate for API access
- All the creative ads that inspired this project 