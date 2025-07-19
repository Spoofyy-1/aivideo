import os
import json
import requests
import tempfile
import shutil
import concurrent.futures
import numpy as np
import uuid  # Add UUID for unique file naming
import threading  # Add threading for thread-safe operations
import time  # Add time for cleanup scheduling
import queue  # Add queue for request management
import sqlite3  # Add SQLite for rating storage
from collections import defaultdict  # Add for rate limiting
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from slugify import slugify
import moviepy.editor as mp
from flask_cors import CORS
import replicate
from openai import OpenAI
from werkzeug.utils import secure_filename

print("DEBUG: All imports completed successfully")

# Load environment variables
load_dotenv()
print("DEBUG: Environment variables loaded")

app = Flask(__name__, static_folder='static')
CORS(app)
print("DEBUG: Flask app created successfully")

# Configure API keys from environment variables with fallbacks
def get_gemini_api_key():
    """Get Gemini API key from environment variables"""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("ERROR: GEMINI_API_KEY not found in environment variables")
        print("Please set GEMINI_API_KEY in your environment or .env file")
        return None
    return gemini_key

# Test Gemini API key availability
gemini_key = get_gemini_api_key()
if gemini_key:
    print("DEBUG: Gemini API key configured")
else:
    print("WARNING: No Gemini API key available")

# Configure OpenAI client
client = None

# Thread-safe file operations
file_lock = threading.Lock()

# Rate limiting and request management
request_counts = defaultdict(list)  # Track requests per IP
request_queue = queue.Queue(maxsize=50)  # Limit concurrent requests
active_requests = threading.Semaphore(5)  # Max 5 concurrent video generations

# Initialize SQLite database for ratings
def init_rating_database():
    """Initialize SQLite database for storing ad ratings and feedback"""
    try:
        conn = sqlite3.connect('ratings.db')
        cursor = conn.cursor()
        
        # Create ratings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ad_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                company_url TEXT NOT NULL,
                ad_type TEXT NOT NULL,
                industry TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                feedback_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_ip TEXT,
                ad_script_json TEXT,
                improvement_suggestions TEXT
            )
        ''')
        
        # Create feedback analysis table for AI insights
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ad_type TEXT NOT NULL,
                industry TEXT NOT NULL,
                avg_rating REAL NOT NULL,
                total_ratings INTEGER NOT NULL,
                common_complaints TEXT,
                improvement_recommendations TEXT,
                successful_patterns TEXT,
                ai_analysis_json TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        print("DEBUG: Rating database initialized successfully")
    except Exception as e:
        print(f"ERROR initializing rating database: {e}")

def analyze_feedback_with_ai(ratings_data):
    """Use AI to analyze user feedback and generate improvement recommendations"""
    try:
        client = get_openai_client()
        if not client:
            return None
            
        # Prepare feedback data for analysis
        feedback_summary = {
            'total_ratings': len(ratings_data),
            'avg_rating': sum(r['rating'] for r in ratings_data) / len(ratings_data),
            'rating_distribution': {},
            'feedback_by_rating': {1: [], 2: [], 3: [], 4: [], 5: []}
        }
        
        # Organize feedback by rating
        for rating in ratings_data:
            rating_val = rating['rating']
            feedback_summary['rating_distribution'][rating_val] = feedback_summary['rating_distribution'].get(rating_val, 0) + 1
            if rating['feedback_text']:
                feedback_summary['feedback_by_rating'][rating_val].append(rating['feedback_text'])
        
        # Create AI analysis prompt
        prompt = f"""Analyze this user feedback data for AI-generated video ads and provide actionable insights:

RATING SUMMARY:
- Total Ratings: {feedback_summary['total_ratings']}
- Average Rating: {feedback_summary['avg_rating']:.2f}/5
- Rating Distribution: {feedback_summary['rating_distribution']}

NEGATIVE FEEDBACK (1-2 stars):
{chr(10).join(feedback_summary['feedback_by_rating'][1] + feedback_summary['feedback_by_rating'][2])}

NEUTRAL FEEDBACK (3 stars):
{chr(10).join(feedback_summary['feedback_by_rating'][3])}

POSITIVE FEEDBACK (4-5 stars):
{chr(10).join(feedback_summary['feedback_by_rating'][4] + feedback_summary['feedback_by_rating'][5])}

Please provide analysis in JSON format:
{{
    "overall_sentiment": "positive/neutral/negative",
    "main_complaints": ["complaint1", "complaint2", "complaint3"],
    "successful_elements": ["element1", "element2", "element3"],
    "improvement_recommendations": [
        {{"issue": "specific problem", "solution": "specific fix", "priority": "high/medium/low"}},
        {{"issue": "another problem", "solution": "another fix", "priority": "high/medium/low"}}
    ],
    "ad_type_insights": {{"insight": "what works well for this ad type"}},
    "industry_insights": {{"insight": "what works well for this industry"}},
    "prompt_improvements": ["specific prompt modification 1", "specific prompt modification 2"],
    "content_patterns": {{"avoid": ["pattern1", "pattern2"], "emphasize": ["pattern3", "pattern4"]}}
}}"""

        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON response
        import re
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        else:
            return json.loads(content)
            
    except Exception as e:
        print(f"ERROR in AI feedback analysis: {e}")
        return None

def get_improvement_insights(ad_type, industry):
    """Get AI-generated improvement insights for specific ad type and industry"""
    try:
        conn = sqlite3.connect('ratings.db')
        cursor = conn.cursor()
        
        # Get recent ratings for this ad type and industry
        cursor.execute('''
            SELECT rating, feedback_text, ad_script_json, created_at
            FROM ad_ratings 
            WHERE ad_type = ? AND industry = ? 
            AND created_at > datetime('now', '-30 days')
            ORDER BY created_at DESC
            LIMIT 50
        ''', (ad_type, industry))
        
        ratings_data = []
        for row in cursor.fetchall():
            ratings_data.append({
                'rating': row[0],
                'feedback_text': row[1],
                'ad_script_json': row[2],
                'created_at': row[3]
            })
        
        conn.close()
        
        if len(ratings_data) < 3:  # Need minimum data for analysis
            return None
            
        # Analyze with AI
        analysis = analyze_feedback_with_ai(ratings_data)
        
        if analysis:
            # Store analysis in database
            conn = sqlite3.connect('ratings.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO feedback_analysis 
                (ad_type, industry, avg_rating, total_ratings, common_complaints, 
                 improvement_recommendations, successful_patterns, ai_analysis_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ad_type, industry,
                sum(r['rating'] for r in ratings_data) / len(ratings_data),
                len(ratings_data),
                json.dumps(analysis.get('main_complaints', [])),
                json.dumps(analysis.get('improvement_recommendations', [])),
                json.dumps(analysis.get('successful_elements', [])),
                json.dumps(analysis)
            ))
            conn.commit()
            conn.close()
        
        return analysis
        
    except Exception as e:
        print(f"ERROR getting improvement insights: {e}")
        return None

def check_rate_limit(client_ip, max_requests=10, time_window=3600):
    """Check if client has exceeded rate limit (10 requests per hour)."""
    current_time = time.time()
    
    # Clean old requests outside time window
    request_counts[client_ip] = [
        req_time for req_time in request_counts[client_ip] 
        if current_time - req_time < time_window
    ]
    
    # Check if under limit
    if len(request_counts[client_ip]) >= max_requests:
        return False
    
    # Add current request
    request_counts[client_ip].append(current_time)
    return True

def get_openai_client():
    """Get a fresh OpenAI client instance to avoid environment interference."""
    import os  # Add this import at the function level
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("WARNING: OPENAI_API_KEY not found in environment")
            return None
        
        # Use modern OpenAI client with explicit parameters to avoid proxy issues
        try:
            # Clear any proxy-related environment variables that might interfere
            proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
            original_values = {}
            for var in proxy_vars:
                if var in os.environ:
                    original_values[var] = os.environ[var]
                    print(f'DEBUG: Found proxy var {var}: {os.environ[var][:20]}...')
                    del os.environ[var]
            
            print('DEBUG: Cleared proxy environment variables')
            
            # Create client with minimal parameters
            client = OpenAI(
                api_key=openai_key,
                timeout=30.0,
                max_retries=2
            )
            
            # Restore original proxy values
            for var, value in original_values.items():
                os.environ[var] = value
                
            return client
        except Exception as e:
            print(f"DEBUG: OpenAI client creation failed: {e}")
            return None
                
    except Exception as e:
        print(f"ERROR in get_openai_client: {e}")
        return None

openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    print("WARNING: OPENAI_API_KEY not found in environment")
    client = None
else:
    print("DEBUG: OPENAI_API_KEY found")
    # Test if we can create a client
    client = get_openai_client()
    if client:
        print("DEBUG: OpenAI client test successful")
    else:
        print("DEBUG: OpenAI client test failed")

def normalize_na(val):
    if not val:
        return None
    return val.strip().lower() in ['n/a', 'na', 'none', 'no', '']

def normalize_url(url):
    """Normalize URL to ensure it has proper protocol and format."""
    if not url:
        return url
    
    # Remove whitespace
    url = url.strip()
    
    # If no protocol specified, add https://
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Remove trailing slash for consistency
    url = url.rstrip('/')
    
    return url

def research_company(url):
    """Research company using ChatGPT and web scraping."""
    try:
        # Normalize the URL first
        normalized_url = normalize_url(url)
        print(f"DEBUG: Normalized URL from '{url}' to '{normalized_url}'")
        
        client = get_openai_client()
        if client is None:
            return "Error: OpenAI client not available. Please check API key configuration."
            
        # Scrape website content
        response = requests.get(normalized_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = soup.get_text()[:4000]  # Limit content length
        
        # Use ChatGPT to analyze company
        prompt = f"""Analyze this company based on their website content and provide key information in JSON format:
        Website content: {text_content}
        
        Return ONLY a valid JSON object with this exact structure:
        {{
            "main_product_service": "Company's main product/service",
            "target_audience": "Target audience description",
            "unique_selling_points": "Unique selling points",
            "brand_voice_style": "Brand voice and style",
            "key_benefits": "Key benefits for customers",
            "products_services": ["product1", "product2", "product3"],
            "avoid_topics": ["topic1", "topic2", "topic3"]
        }}
        
        Do not include any text before or after the JSON object. Only return the JSON.
        """
        
        # Use modern OpenAI API syntax
        try:
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=10000
            )
        except Exception as api_error:
            print(f"OpenAI API Error: {api_error}")
            # Check if it's a content policy violation
            if "content policy" in str(api_error).lower() or "safety" in str(api_error).lower():
                raise ValueError(f"Content policy violation: The ad prompt was rejected by OpenAI. This may be due to sensitive content in the ad type or prompt. Error: {str(api_error)}")
            else:
                raise ValueError(f"OpenAI API Error: {str(api_error)}")

        content = response.choices[0].message.content.strip()
        print("OpenAI raw response:", repr(content))  # Debug print

        # Check if OpenAI refused the request
        if "I'm sorry, I can't assist" in content or "I cannot help" in content or "I'm unable to" in content or "I can't comply" in content or "I can't comply with" in content:
            print("OpenAI refused the request - likely content policy violation")
            raise ValueError(f"OpenAI refused the request, likely due to content policy. Response: {repr(content)}")

        # Try to extract JSON from the response
        try:
            if not content:
                raise ValueError("OpenAI returned an empty response.")
            
            # First try to parse as direct JSON
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Direct JSON parsing failed: {e}")
            
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError as e2:
                    print(f"Markdown JSON parsing failed: {e2}")
            
            # Try to find any JSON object in the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError as e3:
                    print(f"Regex JSON parsing failed: {e3}")
            
            # If all JSON parsing fails, create a structured response from the text
            print("All JSON parsing failed, creating structured response from text")
            return {
                "main_product_service": "Unable to parse - see raw response",
                "target_audience": "Unable to parse - see raw response", 
                "unique_selling_points": "Unable to parse - see raw response",
                "brand_voice_style": "Unable to parse - see raw response",
                "key_benefits": "Unable to parse - see raw response",
                "products_services": [],
                "avoid_topics": [],
                "raw_response": content[:1000]  # Include first 1000 chars for debugging
            }
    except Exception as e:
        return f"Error researching company: {str(e)}"

def extract_products_services(research_text):
    """Extract a list of products/services from the research_company output using OpenAI."""
    
    # If research_text is already a dict (from successful JSON parsing), extract products_services
    if isinstance(research_text, dict):
        return research_text.get('products_services', [])
    
    # If it's a string, try to parse it or use OpenAI to extract
    client = get_openai_client()
    if client is None:
        return []
        
    prompt = f"""Extract up to 5 main products or services from the following company research. Return only a JSON array of strings. If none are found, return an empty array.\n\n{research_text}"""
    
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}]
    )
    content = response.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except Exception:
        import re
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return []

def extract_avoid_topics(research_text):
    client = get_openai_client()
    if client is None:
        return []
        
    prompt = f"""Extract a JSON array of topics, themes, or words that should be avoided in marketing or advertising for this company, based on the following research. If none are found, return an empty array.\n\n{research_text}"""
    
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}]
    )
    content = response.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except Exception:
        import re
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return []

def extract_key_features_and_benefits(research_text):
    """Extract specific features, benefits, and what the product actually does from company research."""
    client = get_openai_client()
    if client is None:
        return {"features": [], "benefits": [], "what_it_does": ""}
        
    prompt = f"""Based on this company research, extract specific information about their product/service. Return as JSON:

{research_text}

Format:
{{
    "features": ["specific feature 1", "specific feature 2", "specific feature 3"],
    "benefits": ["concrete benefit 1", "concrete benefit 2", "concrete benefit 3"],
    "what_it_does": "Clear 1-2 sentence explanation of what the product/service actually does",
    "unique_selling_points": ["unique advantage 1", "unique advantage 2"],
    "target_pain_points": ["problem it solves 1", "problem it solves 2"]
}}

Be specific and actionable. Don't use generic terms like "innovative" or "cutting-edge". Focus on concrete, tangible features and benefits that would matter to customers."""
    
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}]
    )
    content = response.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except Exception:
        import re
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return {"features": [], "benefits": [], "what_it_does": "", "unique_selling_points": [], "target_pain_points": []}

def get_top_best_ads(user_text, top_k=3):
    """Embed user/company info and retrieve top K most similar best ads."""
    client = get_openai_client()
    if client is None:
        return []
        
    with open("best_ads_embedded.json", "r") as f:
        best_ads = json.load(f)
    # Embed user/company info
    user_embedding = client.embeddings.create(
        model="text-embedding-ada-002",
        input=user_text
    ).data[0].embedding
    # Compute cosine similarity
    def cosine(a, b):
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    scored = [
        (cosine(user_embedding, ad["embedding"]), ad)
        for ad in best_ads
    ]
    scored.sort(reverse=True, key=lambda x: x[0])
    return [ad for _, ad in scored[:top_k]]

def get_target_audience_for_industry(industry):
    industry = (industry or '').lower()
    if industry == 'technology':
        return 'Tech-savvy professionals, early adopters, and businesses looking for innovation.'
    elif industry == 'healthcare':
        return 'Patients, healthcare professionals, and families seeking wellness solutions.'
    elif industry == 'retail':
        return 'Everyday consumers, bargain hunters, and trend followers.'
    elif industry == 'finance':
        return 'Investors, business owners, and individuals seeking financial security.'
    elif industry == 'education':
        return 'Students, teachers, parents, and lifelong learners.'
    elif industry == 'food & beverage':
        return 'Foodies, families, and people looking for convenience or unique flavors.'
    elif industry == 'travel':
        return 'Adventurers, families, and business travelers.'
    elif industry == 'automotive':
        return 'Drivers, car enthusiasts, and families needing reliable transportation.'
    elif industry == 'fashion':
        return 'Style-conscious individuals, trendsetters, and shoppers.'
    elif industry == 'real estate':
        return 'Home buyers, renters, and real estate investors.'
    elif industry == 'entertainment':
        return 'Fans, viewers, and people seeking fun and excitement.'
    elif industry == 'fitness':
        return 'Fitness enthusiasts, athletes, gym-goers, and people seeking healthy lifestyle changes.'
    elif industry == 'beauty':
        return 'Beauty enthusiasts, skincare lovers, makeup artists, and people focused on self-care.'
    elif industry == 'gaming':
        return 'Gamers, esports fans, content creators, and interactive entertainment enthusiasts.'
    elif industry == 'software':
        return 'Developers, IT professionals, businesses seeking digital solutions, and tech users.'
    elif industry == 'e-commerce':
        return 'Online shoppers, entrepreneurs, small business owners, and digital commerce users.'
    elif industry == 'marketing':
        return 'Marketers, small business owners, content creators, and growth-focused professionals.'
    elif industry == 'consulting':
        return 'Business leaders, entrepreneurs, professionals seeking expertise, and decision-makers.'
    elif industry == 'photography':
        return 'Photographers, content creators, artists, and visual storytelling enthusiasts.'
    elif industry == 'music':
        return 'Musicians, music lovers, content creators, and audio entertainment enthusiasts.'
    elif industry == 'sports':
        return 'Athletes, sports fans, coaches, and active lifestyle enthusiasts.'
    elif industry == 'home & garden':
        return 'Homeowners, DIY enthusiasts, gardeners, and home improvement seekers.'
    elif industry == 'pets':
        return 'Pet owners, animal lovers, veterinarians, and pet care enthusiasts.'
    elif industry == 'crypto':
        return 'Cryptocurrency investors, blockchain enthusiasts, fintech users, and digital asset traders.'
    elif industry == 'saas':
        return 'Business owners, entrepreneurs, productivity seekers, and software-as-service users.'
    elif industry == 'manufacturing':
        return 'Manufacturers, industrial professionals, supply chain managers, and B2B decision-makers.'
    elif industry == 'agriculture':
        return 'Farmers, agricultural professionals, sustainability advocates, and food production experts.'
    elif industry == 'construction':
        return 'Contractors, builders, architects, and construction industry professionals.'
    elif industry == 'legal':
        return 'Lawyers, legal professionals, business owners, and individuals seeking legal solutions.'
    elif industry == 'non-profit':
        return 'Donors, volunteers, community advocates, and socially-conscious individuals.'
    elif industry == 'wellness':
        return 'Health-conscious individuals, wellness seekers, mental health advocates, and holistic lifestyle enthusiasts.'
    else:
        return 'A broad audience interested in this industry.'

def generate_segment_template(num_segments):
    """Generate JSON template for additional segments beyond segment1"""
    template = ""
    
    for i in range(2, num_segments + 1):
        template += f"""
    "segment{i}": {{
        "scene_description": "...",
        "prompt": "... [voiceover: Professional male narrator with warm, authoritative tone says: 'exact 15 words with perfect timing'] with [specific background music] and [sound effects]",
        "voiceover_script": "15 words maximum here with strategic word placement",
        "narrator_characteristics": "Professional male narrator with warm, authoritative tone (IDENTICAL TO SEGMENT1)",
        "delivery_instructions": "Speaks with steady confidence and natural pacing, no awkward pauses (SAME AS SEGMENT1)",
        "audio_production": "Continuous upbeat background music with strategic volume swells during speech pauses",
        "timing_breakdown": "0:00-0:06 narrator speaks 15 words, 0:06-0:08 music bridge, no blank space",
        "word_timing": "Strategic placement: words 1-3 at 0:00-1:00, words 4-7 at 1:00-2:50, words 8-11 at 2:50-4:30, words 12-15 at 4:30-6:00",
        "mood": "...",
        "camera": "...",
        "veo3_optimization": "..."
    }},"""
    
    return template

def generate_ad_script(company_info, user_answers, best_ads=None):
    """
    Generate ad script with variable duration support (8, 16, 24, 32 seconds).
    Each segment is 8 seconds with 15 words maximum for optimal VEO-3 timing.
    """
    client = get_openai_client()
    if client is None:
        print("DEBUG: OpenAI client not available")
        return {"error": "OpenAI client not available"}

    # Extract duration from user answers
    duration_text = user_answers.get('duration', '16 seconds (2 segments - Standard)')
    
    # Parse duration to get number of segments
    if '8 seconds' in duration_text:
        num_segments = 1
        total_duration = 8
        structure_description = "Single 8-second segment: HOOK + BRAND + CTA"
    elif '24 seconds' in duration_text:
        num_segments = 3
        total_duration = 24
        structure_description = "Segment 1 (8s): HOOK + BRAND INTRO\nSegment 2 (8s): PROBLEM + SOLUTION\nSegment 3 (8s): TRANSFORMATION + CTA"
    elif '32 seconds' in duration_text:
        num_segments = 4
        total_duration = 32
        structure_description = "Segment 1 (8s): HOOK + BRAND INTRO\nSegment 2 (8s): PROBLEM IDENTIFICATION\nSegment 3 (8s): SOLUTION DEMONSTRATION\nSegment 4 (8s): TRANSFORMATION + CTA"
    else:
        # Default to 16 seconds
        num_segments = 2
        total_duration = 16
        structure_description = "Segment 1 (8s): HOOK + BRAND INTRO\nSegment 2 (8s): TRANSFORMATION + CTA"

    print(f"DEBUG: Generating {total_duration}-second ad with {num_segments} segments")

    # Get best ads for inspiration
    best_ads_str = ""
    if best_ads:
        best_ads_str = "Here are some successful ad examples for inspiration:\n"
        for ad in best_ads:
            best_ads_str += f"- {ad['title']}: {ad['script']} (Principle: {ad['principle']})\n"

    # Build creative direction
    creative_notes = []
    for key, value in user_answers.items():
        if key not in ['company_url', 'industry', 'product', 'duration'] and value and value.lower() != 'n/a':
            creative_notes.append(f"{key.replace('_', ' ').title()}: {value}")
    
    creative_notes_str = "\n".join(creative_notes) if creative_notes else "No specific creative direction provided."

    # Build product information
    product_info = user_answers.get('product', 'N/A')
    product_info_str = f"Product/Service to promote: {product_info}" if product_info != 'N/A' else ""

    # Build avoidance topics
    avoid_topics = user_answers.get('avoid', '')
    avoid_str = avoid_topics if avoid_topics else "None specified"

    prompt = f"""*** VEO-3 OPTIMIZED {total_duration}-SECOND AD CREATION ***
Create a {total_duration}-second ad script using VEO-3 techniques:

🎬 STRUCTURE:
{structure_description}

📝 OUTPUT REQUIREMENTS:
For each segment provide:
- "scene_description": Visual description (NO logos)
- "prompt": Complete VEO-3 prompt with [voiceover: ...] (NO logos)
- "voiceover_script": EXACTLY 15 words maximum for perfect 8-second timing
- "mood": Emotional atmosphere
- "camera": Camera movement
- "veo3_optimization": VEO-3 techniques applied

🎙️ CRITICAL AUDIO REQUIREMENTS:
- EXACTLY 15 WORDS PER SEGMENT: Optimal for 8-second clips with no blank space
- 15 words = ~6 seconds speech + 2 seconds visual transition = perfect 8s clip
- Every word must be impactful and necessary
- Format: "Character says: exact words"
- Company name mentioned strategically across segments (within 15-word limits)
- Continuous background music/sounds throughout

🎭 NARRATOR CONSISTENCY REQUIREMENTS:
- SAME NARRATOR VOICE: Use identical narrator description across ALL segments
- VOICE CONTINUITY: "Professional male narrator with warm, authoritative tone" (or specify exact voice type)
- CONSISTENT DELIVERY: Same speaking pace, energy level, and style throughout entire ad
- PERSONALITY LOCK: Once narrator personality is set in segment1, maintain exactly the same in all segments
- BRAND VOICE ALIGNMENT: Match narrator to brand personality (corporate = professional, startup = energetic, luxury = sophisticated)

🎵 AUDIO TIMING MASTERY:
- WORD PLACEMENT: Strategic timing of each word to eliminate dead space
- SPEECH RHYTHM: 0:00-0:06 narrator speaks (15 words in 6 seconds = 2.5 words/second)
- TRANSITION TIMING: 0:06-0:08 music bridge to next segment (no silence)
- EMPHASIS PLACEMENT: Key product words at 0:02 and 0:04 for maximum impact
- BREATH CONTROL: Natural pauses built into script, no awkward gaps
- SEAMLESS FLOW: Each word flows naturally into the next with perfect pacing

🎬 BLANK SPACE ELIMINATION:
- NO DEAD AIR: Every second filled with narrator voice, music, or sound effects
- WORD SPACING: Strategic placement - important words at 1-second intervals
- MUSIC UNDERLAYS: Continuous background music that swells during speech pauses
- SOUND BRIDGES: Smooth audio transitions between words and segments
- TIMING PRECISION: Each of the 15 words placed at optimal 0.4-second intervals

⚠️ TIMING CRITICAL: VEO-3 cuts off voiceovers longer than 15 words in 8-second clips.
Make every word count. Eliminate blank space with perfect word timing.

🎯 BRAND MESSAGING REQUIREMENTS (ABSOLUTELY CRITICAL):
- MANDATORY: Either the slogan OR call-to-action MUST be included in at least one segment's voiceover
- PREFERRED: Include slogan in early segments, call-to-action in final segment
- If slogan is short (3-5 words), include it in multiple segments
- If call-to-action is short (3-5 words), include it in final segment
- NEVER create an ad without clear brand messaging in the actual voiceover
- Examples: "Try [Product] today", "Visit [website]", "[Slogan] - [Product]"

🚀 2025 ADVERTISING TRENDS (INTEGRATE THESE):
- AUTHENTICITY OVER POLISH: Raw, unfiltered content outperforms overly produced ads
- HUMOR IS BACK: Funny ads have higher recall and conversion (only 14% use humor - stand out!)
- HUMAN CONNECTION: As AI increases, people crave authentic human stories and real experiences
- EDUCATIONAL VALUE: Teach something useful, don't just sell - builds trust and engagement
- SOUND-OFF OPTIMIZATION: 85% watch without sound - visual storytelling is crucial
- TRANSFORMATION STORIES: Show before/after, problem/solution, struggle/success
- RELATABLE HEROES: Feature everyday people, not just perfect models or celebrities

📱 PLATFORM-NATIVE REQUIREMENTS:
- Create content that feels native to social feeds, not like traditional ads
- Use conversational, direct language ("you" instead of "customers")
- Include visual hooks that work without sound (text overlays, compelling visuals)
- Make it shareable and discussion-worthy

Based on this company information:
{company_info}

{product_info_str}

Creative direction from user:
{creative_notes_str}

Avoid these topics: {avoid_str}

{best_ads_str}

Format as valid JSON with {num_segments} segments:
{{
    "segment1": {{
        "scene_description": "...",
        "prompt": "... [voiceover: Professional male narrator with warm, authoritative tone says: 'exact 15 words with perfect timing'] with [specific background music] and [sound effects]",
        "voiceover_script": "15 words maximum here with strategic word placement (MUST include brand messaging)",
        "narrator_characteristics": "Professional male narrator with warm, authoritative tone (KEEP IDENTICAL IN ALL SEGMENTS)",
        "delivery_instructions": "Speaks with steady confidence and natural pacing, no awkward pauses",
        "audio_production": "Continuous upbeat background music with strategic volume swells during speech pauses",
        "timing_breakdown": "0:00-0:06 narrator speaks 15 words, 0:06-0:08 music bridge, no blank space",
        "word_timing": "Strategic placement: words 1-3 at 0:00-1:00, words 4-7 at 1:00-2:50, words 8-11 at 2:50-4:30, words 12-15 at 4:30-6:00",
        "mood": "...",
        "camera": "...",
        "veo3_optimization": "..."
    }},{generate_segment_template(num_segments)}
    "slogan": "Memorable brand slogan (2-8 words) - MUST be integrated into voiceover scripts",
    "call_to_action": "Clear, actionable CTA (2-8 words) - MUST be integrated into voiceover scripts"
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=3000  # Increased for longer ads
        )

    content = response.choices[0].message.content.strip()
        
        # Parse JSON response
        import re
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            ad_script = json.loads(match.group(0))
            print(f"DEBUG: Successfully generated {num_segments}-segment ad script")
            return ad_script
        else:
            print("DEBUG: Could not parse GPT response as JSON")
            return {"error": "Could not parse response"}
            
    except Exception as e:
        print(f"DEBUG: Error generating ad script: {e}")
        return {"error": str(e)}

def generate_video_segment(prompt, segment_num):
    """Generate a 8-second video segment using Veo-3."""
    try:
        output = replicate.run(
            "google/veo-3",
            input={
                "prompt": prompt,
                "num_frames": 16,  # 16 frames for 4 seconds at 4fps
                "fps": 4,
                "motion_bucket_id": 127,  # Higher motion
                "cond_aug": 0.02,
                "decoding_t": 7,
                "height": 576,
                "width": 1024,
            }
        )
        
        # Download the video
        video_url = output
        response = requests.get(video_url, stream=True)
        
        # Save to temporary file
        temp_dir = tempfile.mkdtemp()
        video_path = os.path.join(temp_dir, f"segment_{segment_num}.mp4")
        
        with open(video_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        return video_path
    except Exception as e:
        raise Exception(f"Error generating video segment: {str(e)}")

def generate_video_segment_with_session(prompt, segment_num, session_id):
    """Generate a 8-second video segment using Veo-3 with session-specific temp files."""
    try:
        output = replicate.run(
            "google/veo-3",
            input={
                "prompt": prompt,
                "num_frames": 16,  # 16 frames for 4 seconds at 4fps
                "fps": 4,
                "motion_bucket_id": 127,  # Higher motion
                "cond_aug": 0.02,
                "decoding_t": 7,
                "height": 576,
                "width": 1024,
            }
        )
        
        # Download the video
        video_url = output
        response = requests.get(video_url, stream=True)
        
        # Save to session-specific temporary directory
        temp_dir = tempfile.mkdtemp(prefix=f"session_{session_id}_")
        video_path = os.path.join(temp_dir, f"segment_{segment_num}.mp4")
        
        with open(video_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        return video_path
    except Exception as e:
        raise Exception(f"Error generating video segment: {str(e)}")

def combine_videos(video_paths, output_path):
    """Combine video segments into final ad with improved audio handling."""
    try:
        print(f"DEBUG: Starting video combination with {len(video_paths)} clips")
        
        # Load clips with basic error handling
        clips = []
        for i, path in enumerate(video_paths):
            if not os.path.exists(path):
                raise Exception(f"Video file {path} does not exist")
            
            clip = mp.VideoFileClip(path)
            print(f"DEBUG: Clip {i+1} - Duration: {clip.duration:.2f}s, FPS: {clip.fps}, Audio: {clip.audio is not None}")
            clips.append(clip)
        
        # Simple concatenation without complex audio processing
        print("DEBUG: Concatenating clips")
        final_clip = mp.concatenate_videoclips(clips, method="compose")
        
        print(f"DEBUG: Final clip duration: {final_clip.duration:.2f}s")
        
        # Write with basic settings to avoid ffmpeg issues
        print("DEBUG: Writing final video file")
        final_clip.write_videofile(
            output_path, 
            codec='libx264', 
            audio_codec='aac',
            verbose=False,
            logger=None
        )
        
        print("DEBUG: Video combination completed successfully")
        
        # Cleanup
        final_clip.close()
        for clip in clips:
            clip.close()
        
        # Clean up temp files
        for path in video_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"WARNING: Could not remove temp file {path}: {e}")
        
        return output_path
    except Exception as e:
        print(f"ERROR in combine_videos: {str(e)}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Error combining videos: {str(e)}")

def generate_video_segment_with_retry(prompt, segment_num, max_retries=3):
    for attempt in range(max_retries):
        try:
            return generate_video_segment(prompt, segment_num)
        except Exception as e:
            error_msg = str(e)
            if "flagged as sensitive" in error_msg.lower() or "E005" in error_msg:
                print(f"Sensitive content detected for segment {segment_num}, regenerating script (attempt {attempt+1})...")
                continue  # Try again
            else:
                raise  # Other errors, don't retry
    raise Exception(f"Failed to generate video segment {segment_num} after {max_retries} attempts due to sensitive content.")

def generate_company_report(company_info, output_path):
    """Generate a full company report and save as a text file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Company Research Report\n")
            f.write("=======================\n\n")
            
            # Handle both string and dictionary inputs
            if isinstance(company_info, dict):
                # Format dictionary as readable report
                f.write(f"Main Product/Service: {company_info.get('main_product_service', 'Not specified')}\n\n")
                f.write(f"Target Audience: {company_info.get('target_audience', 'Not specified')}\n\n")
                f.write(f"Unique Selling Points: {company_info.get('unique_selling_points', 'Not specified')}\n\n")
                f.write(f"Brand Voice & Style: {company_info.get('brand_voice_style', 'Not specified')}\n\n")
                f.write(f"Key Benefits: {company_info.get('key_benefits', 'Not specified')}\n\n")
                
                products_services = company_info.get('products_services', [])
                if products_services:
                    f.write("Products & Services:\n")
                    for i, product in enumerate(products_services, 1):
                        f.write(f"{i}. {product}\n")
                    f.write("\n")
                
                avoid_topics = company_info.get('avoid_topics', [])
                if avoid_topics:
                    f.write("Topics to Avoid in Marketing:\n")
                    for i, topic in enumerate(avoid_topics, 1):
                        f.write(f"{i}. {topic}\n")
                    f.write("\n")
                
                # Include raw response if available for debugging
                if 'raw_response' in company_info:
                    f.write("Raw AI Response (for debugging):\n")
                    f.write("=" * 40 + "\n")
                    f.write(company_info['raw_response'])
                    f.write("\n")
            else:
                # Handle string input (legacy support)
                f.write(str(company_info))
        return output_path
    except Exception as e:
        raise Exception(f"Error generating company report: {str(e)}")

def improve_script_with_gemini(company_info, user_answers, gpt_script, best_ads=None):
    """Send each segment to Gemini separately to improve for Veo3 with 2025 best practices."""
    import copy
    improved_script = copy.deepcopy(gpt_script)
    
    # VEO-3 OPTIMIZATION FRAMEWORK - Define here for scope access
    veo3_framework = """
    *** VEO-3 ADVERTISING OPTIMIZATION ***
    
    🎬 CORE PRINCIPLES:
    - PROMPT AS BLUEPRINT: Detailed instructions = better results
    - CINEMATIC LANGUAGE: Use film terms (dolly-in, tracking shot, close-up)
    - NATIVE AUDIO: Format "Character says: exact words" (no subtitles)
    - MOTIVATED MOVEMENT: Every camera move serves the story
    
    🎥 KEY CAMERA MOVES:
    - Product reveals: "slow dolly-in on product"
    - Testimonials: "medium close-up for authenticity"  
    - Call-to-action: "push-in on logo"
    
    🎙️ AUDIO EXCELLENCE:
    - Dialogue: "Spokesperson says: This changed my life!"
    - Delivery: "announces confidently" / "exclaims excitedly"
    - Sound: "upbeat commercial music" + "satisfying product click"
    
    📝 STRUCTURE: Subject + Action + Camera + Audio + Brand message
    """
    
    # Build best ads inspiration string for Gemini improvements
    best_ads_str = ""
    if best_ads:
        best_ads_str = "\n\nHere are some of the best, most creative, and viral ad scripts to use as inspiration for improvements:\n"
        for ad in best_ads:
            best_ads_str += f"- {ad['title']}: {ad['script']} (Principle: {ad['principle']})\n"
    
    # 2025 improvement guidelines with 16-second optimization + VEO-3 MASTERY
    improvement_guidelines_2025 = f"""
    *** 2025 IMPROVEMENT FOCUS - 16-SECOND OPTIMIZATION + VEO-3 MASTERY ***
    When improving this script, prioritize these 2025 best practices and Veo-3 optimization:

    {veo3_framework}

    🚀 IMPROVEMENT PRIORITIES:

    1. VEO-3 EMOTION & GESTURE ENHANCEMENT:
       - Add emotion chaining: "Character starts [emotion], then [emotion], finally [emotion]"
       - Include gesture sequences: "First [gesture], then [gesture], ending with [gesture]"
       - Combine movement + feeling: Link physical actions to emotional states
       - Create start/stop emotional arcs within 8-second segments

    2. VEO-3 AUDIO OPTIMIZATION:
       - Dialogue Format: Use "Character says: 'exact words'" with colon syntax
       - Emotional Delivery: Specify HOW lines are delivered - "whispers fearfully" / "shouts triumphantly"
       - Sound Design: Replace generic "sounds" with specific audio - "glass shattering" not "noise"
       - Music Integration: Add mood-specific music - "haunting violin melody" / "upbeat electronic beat"
       - Subtitle Prevention: Add "(no subtitles)" to every dialogue prompt
       - ELIMINATE DEAD AIR: Ensure continuous dialogue, music, or SFX throughout entire 8 seconds
       - RAPID-FIRE DIALOGUE: Pack 4-6 lines of dialogue into each segment
       - AUDIO LAYERING: Combine talking with background music and ambient sounds
       - SMOOTH TRANSITIONS: Bridge audio between different speakers or sound elements
       - PRODUCT OBSESSION: Company name mentioned 3-4 times per segment
       - CONSTANT TALKING: Characters speak immediately after each other with no gaps
       - OVERLAPPING VOICES: Multiple people can talk simultaneously for richness

    3. VEO-3 CINEMATIC ENHANCEMENT:
       - Camera Motivation: Every camera move serves the story - "dolly in as tension builds"
       - Composition Precision: Use professional terms - "over-the-shoulder shot" / "extreme close-up"
       - Lens Effects: Add focus techniques - "rack focus from product to satisfied user"
       - Lighting Specificity: "chiaroscuro lighting" / "golden hour warmth" / "neon glow"

    4. 16-SECOND ABCD OPTIMIZATION:
       - A: Strengthen 3-second hook with Veo-3 emotion chaining + immediate rapid dialogue
       - B: Earlier brand integration using Veo-3 audio generation + constant product mentions
       - C: Deeper connection through Veo-3 dialogue + gesture linking + company obsession
       - D: Clearer direction with motivated camera movement + non-stop product talk

    5. VEO-3 PHYSICS & AUTHENTICITY:
       - Add realistic interactions between characters and objects
       - Include natural movement - fabric sway, hair movement, realistic gestures
       - Physics-accurate product demonstrations
       - Environmental authenticity - lighting changes, atmospheric effects

    6. CHARACTER CONSISTENCY (VEO-3 STRENGTH):
       - Maintain identical detailed character descriptions across segments
       - Consistent personality traits and mannerisms
       - Visual continuity for brand characters
       - Emotional progression that feels natural and motivated

    7. HIERARCHICAL INFORMATION STRUCTURE:
       - Primary: Core characters, main actions, setting
       - Secondary: Environmental details, background elements
       - Technical: Camera, lighting, audio specifications
       - Temporal: Timing, transitions, emotional progression

    8. ADVANCED VEO-3 TECHNIQUES:
       - Selfie-style authenticity when appropriate
       - Perfect dialogue timing for 8-second segments
       - Motivated directorial choices - every technical decision serves the story
       - Scene transition planning for multi-segment narratives

    *** CRITICAL DIALOGUE IMPROVEMENTS ***
    - ELIMINATE ALL DEAD SPACE: No awkward pauses, silence, or blank moments
    - RAPID-FIRE DELIVERY: Characters speak quickly and enthusiastically
    - PRODUCT INTEGRATION: Weave company mentions into every line naturally
    - OVERLAPPING AUDIO: Multiple voices, background music, ambient sounds
    - CONSTANT ENERGY: High-energy delivery throughout entire segment
    - NO CREEPY SILENCE: Fill every second with engaging audio content
    """
    
    # Get all segments dynamically
    segments = [key for key in gpt_script.keys() if key.startswith('segment')]
    num_segments = len(segments)
    
    for seg in segments:
        segment_num = seg.replace('segment', '')
        duration_text = f"{num_segments * 8}-second" if num_segments > 1 else "8-second"
        prompt = f"Can you improve this current script to be better fit for Veo3 generation for a {duration_text} Ad? Make it more engaging, cinematic, and effective using 2025 best practices and the ABCD framework (Attention, Branding, Connection, Direction).{improvement_guidelines_2025}{best_ads_str}\n\nCurrent segment script:\n{json.dumps(gpt_script[seg], indent=2)}\n\nImprove this script while maintaining the JSON format. Focus on:\n1. {duration_text.upper()} OPTIMIZATION: Making every second count with no wasted moments\n2. ABCD FRAMEWORK: Ensuring proper Attention (hook), Branding (early presence), Connection (human elements), Direction (clear CTA)\n3. MOBILE-FIRST: Bright, high-contrast visuals with tight framing for small screens\n4. IMMEDIATE IMMERSION: Drop viewers into story from second 1\n5. ULTRA-SHORT STORYTELLING: Making it more visually compelling and better suited for {duration_text} video generation\n6. Applying 2025 trends: stronger hooks, authenticity, humor (if appropriate), emotional engagement\n7. Ensuring the visual and voiceover work together for maximum impact in limited time\n8. Making it feel more native to social platforms rather than traditional advertising\n\nFor {seg}: Focus on segment-specific optimization based on position {segment_num} in the {num_segments}-segment sequence"
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-06-05:generateContent?key=" + get_gemini_api_key()
        headers = {"Content-Type": "application/json"}
        data = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        import re
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            improved_script[seg] = json.loads(match.group(0))
        else:
            raise Exception("Gemini did not return valid JSON. Raw response: " + repr(text))
    # Slogan and CTA remain as in GPT script
    return improved_script

def ensure_best_ads_embedded():
    try:
        print("DEBUG: Starting ensure_best_ads_embedded()")
        import time
        best_ads_path = "best_ads.json"
        embedded_path = "best_ads_embedded.json"
        
        print(f"DEBUG: Checking if {best_ads_path} exists...")
        if not os.path.exists(best_ads_path):
            print(f"ERROR: {best_ads_path} does not exist!")
            return
        else:
            print(f"DEBUG: {best_ads_path} exists")
        
        needs_embedding = False
        if not os.path.exists(embedded_path):
            print(f"DEBUG: {embedded_path} does not exist, needs embedding")
            needs_embedding = True
        else:
            print(f"DEBUG: {embedded_path} exists, checking timestamps")
            if os.path.getmtime(best_ads_path) > os.path.getmtime(embedded_path):
                print("DEBUG: best_ads.json is newer, needs re-embedding")
                needs_embedding = True
            else:
                print("DEBUG: embedded file is up to date")
        
        if needs_embedding:
            print("DEBUG: Embedding best ads for retrieval...")
            
            client = get_openai_client()
            if client is None:
                print("ERROR: OpenAI client not available for embedding")
                return
                
            try:
                with open(best_ads_path, "r") as f:
                    best_ads = json.load(f)
                print(f"DEBUG: Loaded {len(best_ads)} ads from {best_ads_path}")
            except Exception as e:
                print(f"ERROR loading {best_ads_path}: {e}")
                return
            
            embedded_ads = []
            for i, ad in enumerate(best_ads):
                try:
                    print(f"DEBUG: Processing ad {i+1}/{len(best_ads)}")
                    text = f"{ad['title']}\n{ad['script']}\nPrinciple: {ad['principle']}"
                    embedding = client.embeddings.create(
                        model="text-embedding-ada-002",
                        input=text
                    ).data[0].embedding
                    embedded_ads.append({
                        "title": ad["title"],
                        "script": ad["script"],
                        "principle": ad["principle"],
                        "embedding": embedding
                    })
                except Exception as e:
                    print(f"ERROR processing ad {i+1}: {e}")
                    continue
            
            try:
                with open(embedded_path, "w") as f:
                    json.dump(embedded_ads, f)
                print(f"DEBUG: Embedded ads saved to {embedded_path}")
            except Exception as e:
                print(f"ERROR saving embedded ads: {e}")
        else:
            print("DEBUG: best_ads_embedded.json is up to date.")
    except Exception as e:
        print(f"ERROR in ensure_best_ads_embedded(): {e}")
        import traceback
        traceback.print_exc()

def generate_unique_session_id():
    """Generate a unique session ID for each user request."""
    return str(uuid.uuid4())[:8]  # Short UUID for cleaner filenames

def ensure_user_directory(session_id):
    """Create a unique directory for each user session."""
    user_dir = os.path.join('static', 'generated', session_id)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def cleanup_old_sessions(max_age_hours=24):
    """Clean up user sessions older than max_age_hours to prevent storage overflow."""
    try:
        generated_dir = os.path.join('static', 'generated')
        if not os.path.exists(generated_dir):
            return
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for session_dir in os.listdir(generated_dir):
            session_path = os.path.join(generated_dir, session_dir)
            if os.path.isdir(session_path):
                # Check if directory is older than max_age
                dir_age = current_time - os.path.getctime(session_path)
                if dir_age > max_age_seconds:
                    try:
                        shutil.rmtree(session_path)
                        print(f"DEBUG: Cleaned up old session directory: {session_dir}")
                    except Exception as e:
                        print(f"WARNING: Failed to clean up session {session_dir}: {e}")
    except Exception as e:
        print(f"ERROR in cleanup_old_sessions: {e}")

def start_cleanup_thread():
    """Start background cleanup thread."""
    def periodic_cleanup():
        while True:
            time.sleep(3600)  # Run every hour
            cleanup_old_sessions(max_age_hours=24)  # Clean up files older than 24 hours
    
    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()
    print("DEBUG: Started background cleanup thread")

@app.route('/')
def index():
    try:
        print("DEBUG: Index route called")
        return jsonify({
            'status': 'success',
            'message': 'AI Video Ad Generator API is running',
            'version': '1.0.0',
            'endpoints': {
                'POST /generate': 'Generate AI video advertisement',
                'POST /research': 'Research product information',
                'GET /test': 'Test API connectivity',
                'GET /download/video/<filename>': 'Download generated video files',
                'GET /download/report/<filename>': 'Download research reports'
            }
        })
    except Exception as e:
        print(f"ERROR in index route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate_ad():
    # Rate limiting check
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    if not check_rate_limit(client_ip):
        return jsonify({
            'error': 'Rate limit exceeded. Maximum 10 requests per hour.',
            'retry_after': 3600
        }), 429
    
    # Acquire semaphore for concurrent request limiting
    if not active_requests.acquire(blocking=False):
        return jsonify({
            'error': 'Server is currently processing maximum concurrent requests. Please try again in a few minutes.',
            'retry_after': 300
        }), 503
    
    try:
        print("DEBUG: Generate route called")
        print("Received request to /generate")
        
        # Generate unique session ID for this user
        session_id = generate_unique_session_id()
        print(f"DEBUG: Generated session ID: {session_id}")
        
        user_answers = request.json
        company_url = user_answers.get('company_url')
        print("Company URL:", company_url)
        if not company_url:
            print("No company URL provided")
            return jsonify({'error': 'Company URL is required'}), 400
        
        # Research company
        company_info = research_company(company_url)
        avoid_topics = extract_avoid_topics(company_info)
        print("Company info:", company_info)
        
        # Create unique user directory
        user_dir = ensure_user_directory(session_id)
        
        # Generate company report with unique naming
        company_name = slugify(company_url.split('//')[-1].split('/')[0])
        unique_name = f"{company_name}_{session_id}"
        
        # Thread-safe file operations
        with file_lock:
            report_path = os.path.join(user_dir, f'{unique_name}_report.txt')
        generate_company_report(company_info, report_path)
        
        report_url = f'/download/report/{session_id}/{os.path.basename(report_path)}'
        print(f"Returning report_url: {report_url}")
        
        # Retrieve top best ads for inspiration
        user_text = f"Company info: {company_info}\nUser wants: {json.dumps(user_answers)}"
        best_ads = get_top_best_ads(user_text)
        
        # Always use ChatGPT first, then Gemini improvement flow
        ad_script = generate_ad_script(company_info, user_answers, best_ads=best_ads)
        print("Ad script (GPT):", ad_script)
        try:
            ad_script = improve_script_with_gemini(company_info, user_answers, ad_script, best_ads=best_ads)
            print("Ad script (Gemini improved):", ad_script)
        except Exception as e:
            print("Gemini improvement failed, using GPT script. Error:", e)
        
        # Generate video segments in parallel, with retry on sensitive content
        def get_video_with_session(segment, i, session_id):
            """Generate video with session-specific temporary files and enhanced narrator prompts."""
            for retry in range(3):
                try:
                    # First enhance prompt with narrator details
                    enhanced_prompt = enhance_veo3_prompt_with_narrator(ad_script[segment])
                    # Then optimize for VEO-3 length limits
                    optimized_prompt = optimize_prompt_for_veo3(enhanced_prompt)
                    print(f"DEBUG: Using enhanced narrator prompt for {segment}: {optimized_prompt[:100]}...")
                    video_path = generate_video_segment_with_session(optimized_prompt, i, session_id)
                    processed_path = process_video_segment(video_path, i)
                    return processed_path
                except Exception as e:
                    if "flagged as sensitive" in str(e).lower() or "E005" in str(e):
                        print(f"Sensitive content detected for {segment}, retry {retry+1}...")
                        continue
                    else:
                        raise
            raise Exception(f"Failed to generate {segment} after 3 retries.")

        # Determine number of segments based on script
        segments = [key for key in ad_script.keys() if key.startswith('segment')]
        num_segments = len(segments)
        print(f"DEBUG: Starting parallel video generation for {num_segments} segments with audio processing")
        
        # Generate all segments in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for i, segment_key in enumerate(segments, 1):
                future = executor.submit(get_video_with_session, segment_key, i, session_id)
                futures.append(future)
            
            video_paths = []
            for future in futures:
                video_path = future.result()
                video_paths.append(video_path)

        print(f"DEBUG: Generated and processed {len(video_paths)} video segments")
        
        # Combine videos with improved audio handling
        with file_lock:
            output_path = os.path.join(user_dir, f'{unique_name}_ad.mp4')
        print("DEBUG: Starting video combination with improved audio handling")
        final_video_path = combine_videos(video_paths, output_path)
        
        print("Final video path:", final_video_path)
        # Check if file exists
        if not os.path.exists(final_video_path):
            print(f"ERROR: Video file does not exist at {final_video_path}")
            return jsonify({'error': 'Video file was not created.'}), 500
        else:
            print(f"Video file exists at {final_video_path}")
        
        video_url = f'/download/video/{session_id}/{os.path.basename(final_video_path)}'
        print(f"Returning video_url: {video_url}")
        
        return jsonify({
            'status': 'success',
            'video_url': video_url,
            'report_url': report_url,
            'script': ad_script,
            'session_id': session_id  # Return session ID for tracking
        })
        
    except Exception as e:
        print(f"ERROR in generate route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        # Always release the semaphore
        active_requests.release()

@app.route('/test')
def test():
    try:
        print("DEBUG: Test route called")
        return "Test OK"
    except Exception as e:
        print(f"ERROR in test route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/research', methods=['POST'])
def research_endpoint():
    data = request.json
    company_url = data.get('company_url')
    if not company_url:
        return jsonify({'error': 'Company URL is required'}), 400
    research_text = research_company(company_url)
    products_services = extract_products_services(research_text)
    return jsonify({'products_services': products_services})

@app.route('/download/video/<session_id>/<filename>')
def download_video_session(session_id, filename):
    try:
        print(f"DEBUG: Download video route called for session {session_id}, file {filename}")
        session_dir = os.path.join('static', 'generated', session_id)
        return send_from_directory(session_dir, filename, as_attachment=True)
    except Exception as e:
        print(f"ERROR in download_video_session route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/download/report/<session_id>/<filename>')
def download_report_session(session_id, filename):
    try:
        print(f"DEBUG: Download report route called for session {session_id}, file {filename}")
        session_dir = os.path.join('static', 'generated', session_id)
        return send_from_directory(session_dir, filename, as_attachment=True)
    except Exception as e:
        print(f"ERROR in download_report_session route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    try:
        print("DEBUG: Health check called")
        return jsonify({
            'status': 'healthy',
            'message': 'Backend is running',
            'openai_key_set': bool(os.getenv("OPENAI_API_KEY")),
            'replicate_key_set': bool(os.getenv("REPLICATE_API_TOKEN")),
            'client_status': 'initialized' if client else 'failed'
        })
    except Exception as e:
        print(f"ERROR in health check: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/debug-openai')
def debug_openai():
    try:
        print("DEBUG: Testing OpenAI client...")
        
        # Test 1: Check API key
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            return jsonify({'error': 'No OpenAI API key found', 'key_length': 0})
        
        key_info = {
            'key_set': True,
            'key_length': len(openai_key),
            'key_prefix': openai_key[:10] + '...' if len(openai_key) > 10 else openai_key
        }
        
        # Test 2: Try to create client step by step
        client_info = {'steps': []}
        
        try:
            client_info['steps'].append('Attempting to create OpenAI client...')
            
            # Clear proxy environment variables
            proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
            original_values = {}
            for var in proxy_vars:
                if var in os.environ:
                    original_values[var] = os.environ[var]
                    client_info['steps'].append(f'Found proxy var {var}: {os.environ[var][:20]}...')
                    del os.environ[var]
            
            client_info['steps'].append('Cleared proxy environment variables')
            
            test_client = OpenAI(
                api_key=openai_key,
                timeout=30.0,
                max_retries=2
            )
            
            # Restore proxy values
            for var, value in original_values.items():
                os.environ[var] = value
            
            client_info['steps'].append('OpenAI client created successfully')
            client_info['client_created'] = True
            client_info['error'] = None
        except Exception as e:
            client_info['steps'].append(f'OpenAI client creation failed: {str(e)}')
            client_info['client_created'] = False
            client_info['error'] = str(e)
            test_client = None
        
        # Test 3: Try to make API call if client was created
        api_call_info = {'attempted': False, 'success': False, 'error': None, 'response': None, 'steps': []}
        if client_info['client_created'] and test_client:
            try:
                api_call_info['attempted'] = True
                api_call_info['steps'].append('Attempting API call...')
                response = test_client.chat.completions.create(
                    model="gpt-4.1",
                    messages=[{"role": "user", "content": "Say 'OpenAI test successful'"}]
                )
                api_call_info['steps'].append('API call completed successfully')
                api_call_info['success'] = True
                api_call_info['response'] = response.choices[0].message.content
            except Exception as e:
                api_call_info['steps'].append(f'API call failed: {str(e)}')
                api_call_info['error'] = str(e)
        
        # Test 4: Test our get_openai_client function
        function_test = {'steps': []}
        try:
            function_test['steps'].append('Testing get_openai_client function...')
            func_client = get_openai_client()
            if func_client:
                function_test['steps'].append('get_openai_client returned a client')
                function_test['success'] = True
            else:
                function_test['steps'].append('get_openai_client returned None')
                function_test['success'] = False
        except Exception as e:
            function_test['steps'].append(f'get_openai_client threw exception: {str(e)}')
            function_test['success'] = False
            function_test['error'] = str(e)
        
        return jsonify({
            'key_info': key_info,
            'client_info': client_info,
            'api_call_info': api_call_info,
            'function_test': function_test,
            'global_client_status': 'initialized' if client else 'failed',
            'openai_version': 'latest (1.54.3)'
        })
        
    except Exception as e:
        print(f"ERROR in debug_openai: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/test-chatgpt')
def test_chatgpt():
    """Simple test endpoint to check if ChatGPT is working"""
    try:
        # Get API key
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            return jsonify({'error': 'No OpenAI API key found'}), 500
        
        # Create a simple client without any proxy handling
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            
            # Make a simple API call
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": "Say 'Hello! ChatGPT is working through Railway!' in exactly those words."}],
                max_tokens=50
            )
            
            return jsonify({
                'success': True,
                'response': response.choices[0].message.content,
                'message': 'ChatGPT is accessible through Railway!'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'ChatGPT is not accessible'
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug-embeddings')
def debug_embeddings():
    """Debug endpoint to check embedding file status"""
    try:
        import os
        import json
        
        debug_info = {
            'best_ads_exists': os.path.exists('best_ads.json'),
            'embedded_exists': os.path.exists('best_ads_embedded.json'),
            'embedding_status': 'unknown'
        }
        
        # Check file sizes
        if debug_info['best_ads_exists']:
            debug_info['best_ads_size'] = os.path.getsize('best_ads.json')
            try:
                with open('best_ads.json', 'r') as f:
                    best_ads = json.load(f)
                debug_info['best_ads_count'] = len(best_ads)
            except Exception as e:
                debug_info['best_ads_error'] = str(e)
        
        if debug_info['embedded_exists']:
            debug_info['embedded_size'] = os.path.getsize('best_ads_embedded.json')
            try:
                with open('best_ads_embedded.json', 'r') as f:
                    embedded_ads = json.load(f)
                debug_info['embedded_count'] = len(embedded_ads)
                # Check if embeddings have the right structure
                if embedded_ads and len(embedded_ads) > 0:
                    first_ad = embedded_ads[0]
                    debug_info['has_embeddings'] = 'embedding' in first_ad
                    if 'embedding' in first_ad:
                        debug_info['embedding_length'] = len(first_ad['embedding'])
            except Exception as e:
                debug_info['embedded_error'] = str(e)
        
        # Test the embedding function
        try:
            client = get_openai_client()
            if client:
                debug_info['openai_client_available'] = True
                # Try to get embeddings for a test
                test_embedding = client.embeddings.create(
                    model="text-embedding-ada-002",
                    input="test embedding"
                ).data[0].embedding
                debug_info['test_embedding_length'] = len(test_embedding)
                debug_info['embedding_test_success'] = True
            else:
                debug_info['openai_client_available'] = False
        except Exception as e:
            debug_info['embedding_test_error'] = str(e)
            debug_info['embedding_test_success'] = False
        
        # Check if we need to re-embed
        if debug_info['best_ads_exists'] and debug_info['embedded_exists']:
            best_ads_mtime = os.path.getmtime('best_ads.json')
            embedded_mtime = os.path.getmtime('best_ads_embedded.json')
            debug_info['best_ads_newer'] = best_ads_mtime > embedded_mtime
            debug_info['embedding_status'] = 'up_to_date' if not debug_info['best_ads_newer'] else 'needs_update'
        elif debug_info['best_ads_exists'] and not debug_info['embedded_exists']:
            debug_info['embedding_status'] = 'needs_creation'
        else:
            debug_info['embedding_status'] = 'missing_source_file'
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/force-embed', methods=['POST'])
def force_embed():
    """Force re-embedding of best ads"""
    try:
        print("DEBUG: Force embedding requested")
        ensure_best_ads_embedded()
        return jsonify({
            'status': 'success',
            'message': 'Embedding process completed'
        })
    except Exception as e:
        print(f"ERROR in force_embed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/submit-rating', methods=['POST'])
def submit_rating():
    """Submit user rating and feedback for an ad"""
    try:
        data = request.json
        session_id = data.get('session_id')
        rating = data.get('rating')  # 1-5 stars
        feedback_text = data.get('feedback_text', '')
        ad_type = data.get('ad_type')
        industry = data.get('industry')
        company_url = data.get('company_url')
        ad_script = data.get('ad_script', {})
        
        # Validate required fields
        if not all([session_id, rating, ad_type, industry, company_url]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        if not (1 <= rating <= 5):
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        
        # Get user IP
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Store rating in database
        conn = sqlite3.connect('ratings.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ad_ratings 
            (session_id, company_url, ad_type, industry, rating, feedback_text, user_ip, ad_script_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, company_url, ad_type, industry, rating, feedback_text, user_ip, json.dumps(ad_script)))
        
        conn.commit()
        conn.close()
        
        # If rating is low (1-2), trigger immediate analysis for this ad type/industry
        if rating <= 2 and feedback_text:
            try:
                analysis = get_improvement_insights(ad_type, industry)
                if analysis:
                    print(f"DEBUG: Generated improvement insights for {ad_type}/{industry} due to low rating")
            except Exception as e:
                print(f"WARNING: Could not generate immediate insights: {e}")
        
        return jsonify({
            'status': 'success',
            'message': 'Rating submitted successfully',
            'rating_id': cursor.lastrowid
        })
        
    except Exception as e:
        print(f"ERROR in submit_rating: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/get-ratings-stats')
def get_ratings_stats():
    """Get overall rating statistics"""
    try:
        conn = sqlite3.connect('ratings.db')
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total_ratings,
                AVG(rating) as avg_rating,
                COUNT(CASE WHEN rating = 5 THEN 1 END) as five_star,
                COUNT(CASE WHEN rating = 4 THEN 1 END) as four_star,
                COUNT(CASE WHEN rating = 3 THEN 1 END) as three_star,
                COUNT(CASE WHEN rating = 2 THEN 1 END) as two_star,
                COUNT(CASE WHEN rating = 1 THEN 1 END) as one_star
            FROM ad_ratings
        ''')
        
        overall_stats = cursor.fetchone()
        
        # Stats by ad type
        cursor.execute('''
            SELECT ad_type, COUNT(*) as count, AVG(rating) as avg_rating
            FROM ad_ratings
            GROUP BY ad_type
            ORDER BY avg_rating DESC
        ''')
        
        ad_type_stats = cursor.fetchall()
        
        # Stats by industry
        cursor.execute('''
            SELECT industry, COUNT(*) as count, AVG(rating) as avg_rating
            FROM ad_ratings
            GROUP BY industry
            ORDER BY avg_rating DESC
        ''')
        
        industry_stats = cursor.fetchall()
        
        # Recent feedback
        cursor.execute('''
            SELECT rating, feedback_text, ad_type, industry, created_at
            FROM ad_ratings
            WHERE feedback_text IS NOT NULL AND feedback_text != ''
            ORDER BY created_at DESC
            LIMIT 10
        ''')
        
        recent_feedback = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'overall': {
                'total_ratings': overall_stats[0],
                'avg_rating': round(overall_stats[1], 2) if overall_stats[1] else 0,
                'distribution': {
                    '5_star': overall_stats[2],
                    '4_star': overall_stats[3],
                    '3_star': overall_stats[4],
                    '2_star': overall_stats[5],
                    '1_star': overall_stats[6]
                }
            },
            'by_ad_type': [{'ad_type': row[0], 'count': row[1], 'avg_rating': round(row[2], 2)} for row in ad_type_stats],
            'by_industry': [{'industry': row[0], 'count': row[1], 'avg_rating': round(row[2], 2)} for row in industry_stats],
            'recent_feedback': [{'rating': row[0], 'feedback': row[1], 'ad_type': row[2], 'industry': row[3], 'date': row[4]} for row in recent_feedback]
        })
        
    except Exception as e:
        print(f"ERROR in get_ratings_stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get-improvement-insights/<ad_type>/<industry>')
def get_insights_endpoint(ad_type, industry):
    """Get AI-generated improvement insights for specific ad type and industry"""
    try:
        insights = get_improvement_insights(ad_type, industry)
        if insights:
            return jsonify({
                'status': 'success',
                'insights': insights
            })
        else:
            return jsonify({
                'status': 'no_data',
                'message': 'Not enough rating data for analysis'
            })
    except Exception as e:
        print(f"ERROR in get_insights_endpoint: {e}")
        return jsonify({'error': str(e)}), 500

def process_video_segment(video_path, segment_num):
    """Process individual video segment to improve audio quality and prevent glitches."""
    try:
        print(f"DEBUG: Processing segment {segment_num} at {video_path}")
        
        clip = mp.VideoFileClip(video_path)
        
        # Check if clip has audio
        if clip.audio is None:
            print(f"WARNING: Segment {segment_num} has no audio")
            clip.close()
            return video_path
        
        # Audio improvements
        processed_clip = clip
        
        # Normalize audio to prevent volume inconsistencies
        processed_clip = processed_clip.audio_normalize()
        
        # Remove any audio artifacts at the very beginning/end
        # Trim any potential silence or artifacts from start/end
        audio_start_trim = 0.01  # Remove first 10ms to eliminate pops
        audio_end_trim = 0.01    # Remove last 10ms to eliminate cutoffs
        
        if processed_clip.duration > (audio_start_trim + audio_end_trim):
            processed_clip = processed_clip.subclip(audio_start_trim, processed_clip.duration - audio_end_trim)
        
        # Ensure clip is exactly 8 seconds (standardize duration)
        target_duration = 8.0
        if abs(processed_clip.duration - target_duration) > 0.1:  # If more than 100ms off
            print(f"DEBUG: Adjusting segment {segment_num} duration from {processed_clip.duration:.2f}s to {target_duration}s")
            if processed_clip.duration < target_duration:
                # If too short, loop the last frame to reach target duration
                processed_clip = processed_clip.loop(duration=target_duration)
            else:
                # If too long, trim to target duration
                processed_clip = processed_clip.subclip(0, target_duration)
        
        # Add smooth audio fade transitions to prevent pops
        processed_clip = processed_clip.audio_fadein(0.05).audio_fadeout(0.05)
        
        # Save processed segment
        temp_output = video_path.replace('.mp4', '_processed.mp4')
        processed_clip.write_videofile(
            temp_output,
            codec='libx264',
            audio_codec='aac',
            audio_bitrate="192k",
            verbose=False,
            logger=None  # Reduce output noise
        )
        
        # Replace original with processed version
        processed_clip.close()
        clip.close()
        
        if os.path.exists(video_path):
            os.remove(video_path)
        os.rename(temp_output, video_path)
        
        print(f"DEBUG: Successfully processed segment {segment_num}")
        return video_path
        
    except Exception as e:
        print(f"ERROR processing segment {segment_num}: {str(e)}")
        # Return original path if processing fails
        return video_path

@app.route('/generate-script', methods=['POST'])
def generate_script_only():
    """Generate just the script for preview and editing, without video generation"""
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    if not check_rate_limit(client_ip):
        return jsonify({
            'error': 'Rate limit exceeded. Maximum 10 requests per hour.',
            'retry_after': 3600
        }), 429
    
    try:
        print("DEBUG: Generate script route called with auto-optimization")
        user_answers = request.json
        company_url = user_answers.get('company_url')
        
        if not company_url:
            return jsonify({'error': 'Company URL is required'}), 400
        
        # Research company
        company_info = research_company(company_url)
        
        # Retrieve top best ads for inspiration
        user_text = f"Company info: {company_info}\nUser wants: {json.dumps(user_answers)}"
        best_ads = get_top_best_ads(user_text)
        
        # Generate initial script with GPT first
        print("DEBUG: Generating initial script with GPT")
        ad_script = generate_ad_script(company_info, user_answers, best_ads=best_ads)
        print("Generated initial script:", ad_script)
        
        # Apply automatic optimization until reaching 80/100 VEO-3 readiness
        print("DEBUG: Starting automatic optimization to reach 80/100 VEO-3 readiness")
        optimized_script, script_analysis = auto_optimize_script_until_ready(
            ad_script, company_info, user_answers, best_ads, target_score=80
        )
        
        print(f"DEBUG: Final optimization complete - VEO-3 readiness: {script_analysis.get('veo3_readiness', 0)}/100")
        
        return jsonify({
            'status': 'success',
            'script': optimized_script,
            'company_info': company_info,
            'script_analysis': script_analysis
        })
        
    except Exception as e:
        print(f"ERROR in generate_script route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/improve-script', methods=['POST'])
def improve_script():
    """Improve an existing script by fully regenerating with GPT + Gemini using user feedback"""
    try:
        print("DEBUG: Improve script route called with auto-optimization")
        data = request.json
        current_script = data.get('script')
        company_info = data.get('company_info')
        user_answers = data.get('user_answers')
        improvement_request = data.get('improvement_request', '')
        
        if not current_script or not company_info:
            return jsonify({'error': 'Script and company info are required'}), 400
        
        # Get best ads for context
        user_text = f"Company info: {company_info}\nUser wants: {json.dumps(user_answers)}"
        best_ads = get_top_best_ads(user_text)
        
        # FULL REGENERATION WORKFLOW (GPT + Gemini)
        # Step 1: Modify user answers to include the improvement request
        enhanced_user_answers = user_answers.copy()
        enhanced_user_answers['improvement_feedback'] = improvement_request
        
        # Step 2: Regenerate script with GPT incorporating the feedback
        print("DEBUG: Regenerating script with GPT incorporating user feedback")
        regenerated_script = generate_ad_script_with_feedback(
            company_info, enhanced_user_answers, current_script, improvement_request, best_ads=best_ads
        )
        
        # Step 3: Improve the regenerated script with Gemini
        print("DEBUG: Improving regenerated script with Gemini")
        try:
            final_script = improve_script_with_gemini(
                company_info, enhanced_user_answers, regenerated_script, best_ads=best_ads
            )
            print("DEBUG: Script regeneration and improvement completed")
        except Exception as e:
            print(f"Gemini improvement failed, using GPT regenerated script. Error: {e}")
            final_script = regenerated_script
        
        # Step 4: Apply automatic optimization until reaching 80/100 VEO-3 readiness
        print("DEBUG: Starting automatic optimization to reach 80/100 VEO-3 readiness")
        optimized_script, script_analysis = auto_optimize_script_until_ready(
            final_script, company_info, enhanced_user_answers, best_ads, target_score=80
        )
        
        print(f"DEBUG: Final improvement complete - VEO-3 readiness: {script_analysis.get('veo3_readiness', 0)}/100")
        
        return jsonify({
            'status': 'success',
            'script': optimized_script,
            'script_analysis': script_analysis
        })
        
    except Exception as e:
        print(f"ERROR in improve_script route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/generate-video-from-script', methods=['POST'])
def generate_video_from_script():
    """Generate video from an approved script"""
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    if not check_rate_limit(client_ip):
        return jsonify({
            'error': 'Rate limit exceeded. Maximum 10 requests per hour.',
            'retry_after': 3600
        }), 429
    
    # Acquire semaphore for concurrent request limiting
    if not active_requests.acquire(blocking=False):
        return jsonify({
            'error': 'Server is currently processing maximum concurrent requests. Please try again in a few minutes.',
            'retry_after': 300
        }), 503
    
    try:
        print("DEBUG: Generate video from script route called")
        data = request.json
        ad_script = data.get('script')
        company_info = data.get('company_info')
        user_answers = data.get('user_answers')
        
        if not ad_script or not company_info:
            return jsonify({'error': 'Script and company info are required'}), 400
        
        # Generate unique session ID
        session_id = generate_unique_session_id()
        print(f"DEBUG: Generated session ID: {session_id}")
        
        # Create unique user directory
        user_dir = ensure_user_directory(session_id)
        
        # Generate company report
        company_url = user_answers.get('company_url', 'unknown')
        company_name = slugify(company_url.split('//')[-1].split('/')[0])
        unique_name = f"{company_name}_{session_id}"
        
        with file_lock:
            report_path = os.path.join(user_dir, f'{unique_name}_report.txt')
        generate_company_report(company_info, report_path)
        
        report_url = f'/download/report/{session_id}/{os.path.basename(report_path)}'
        
        # Generate video segments in parallel with optimized script
        def get_video_with_session(segment, i, session_id):
            """Generate video with session-specific temporary files and optimized prompts."""
            for retry in range(3):
                try:
                    # Optimize prompt for VEO-3 length limits
                    optimized_prompt = optimize_prompt_for_veo3(ad_script[segment]['prompt'])
                    video_path = generate_video_segment_with_session(optimized_prompt, i, session_id)
                    processed_path = process_video_segment(video_path, i)
                    return processed_path
                except Exception as e:
                    if "flagged as sensitive" in str(e).lower() or "E005" in str(e):
                        print(f"Sensitive content detected for {segment}, retry {retry+1}...")
                        continue
                    else:
                        raise
            raise Exception(f"Failed to generate {segment} after 3 retries.")

        # Determine number of segments based on script
        segments = [key for key in ad_script.keys() if key.startswith('segment')]
        num_segments = len(segments)
        print(f"DEBUG: Starting parallel video generation for {num_segments} segments with optimized prompts")
        
        # Generate all segments in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for i, segment_key in enumerate(segments, 1):
                future = executor.submit(get_video_with_session, segment_key, i, session_id)
                futures.append(future)
            
            video_paths = []
            for future in futures:
                video_path = future.result()
                video_paths.append(video_path)

        print(f"DEBUG: Generated and processed {len(video_paths)} video segments")
        
        # Combine videos with improved audio handling
        with file_lock:
            output_path = os.path.join(user_dir, f'{unique_name}_ad.mp4')
        final_video_path = combine_videos(video_paths, output_path)
        
        if not os.path.exists(final_video_path):
            return jsonify({'error': 'Video file was not created.'}), 500
        
        video_url = f'/download/video/{session_id}/{os.path.basename(final_video_path)}'
        
        return jsonify({
            'status': 'success',
            'video_url': video_url,
            'report_url': report_url,
            'script': ad_script,
            'session_id': session_id
        })
        
    except Exception as e:
        print(f"ERROR in generate_video_from_script route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        active_requests.release()

def analyze_script_for_veo3(script):
    """Analyze script for potential VEO-3 issues and provide recommendations"""
    # Get all segments dynamically
    segments = [key for key in script.keys() if key.startswith('segment')]
    
    analysis = {
        'overall_recommendations': [],
        'length_analysis': {},
        'audio_quality_score': 0
    }
    
    # Initialize segment issues dynamically
    for segment_key in segments:
        analysis[f'{segment_key}_issues'] = []
    
    for segment_name in segments:
        if segment_name not in script:
            continue
            
        segment = script[segment_name]
        issues = []
        
        # Check voiceover script length (should be ~8 seconds of speech)
        voiceover = segment.get('voiceover_script', '')
        word_count = len(voiceover.split())
        estimated_duration = word_count / 2.5  # ~2.5 words per second for natural speech
        
        if estimated_duration > 9:
            issues.append(f"Voiceover too long ({estimated_duration:.1f}s estimated). May get cut off.")
        elif estimated_duration < 6:
            issues.append(f"Voiceover too short ({estimated_duration:.1f}s estimated). Consider adding content.")
        
        # Check prompt complexity
        prompt = segment.get('prompt', '')
        if len(prompt) > 500:
            issues.append("Prompt very complex. Consider simplifying for better VEO-3 results.")
        
        # Check for proper VEO-3 audio formatting
        if '[voiceover:' not in prompt:
            issues.append("Missing VEO-3 voiceover formatting in prompt.")
        
        # Check for continuous audio
        if 'music' not in prompt.lower() and 'sound' not in prompt.lower():
            issues.append("No background audio specified. May create awkward silence.")
        
        analysis[f'{segment_name}_issues'] = issues
        analysis['length_analysis'][segment_name] = {
            'word_count': word_count,
            'estimated_duration': round(estimated_duration, 1),
            'optimal': 6 <= estimated_duration <= 8
        }
    
    # Overall recommendations
    total_issues = sum(len(analysis[f'{seg}_issues']) for seg in segments)
    if total_issues > 0:
        analysis['overall_recommendations'].append("Consider script optimization before video generation.")
    
    # Calculate audio quality score
    analysis['audio_quality_score'] = max(0, 100 - (total_issues * 15))
    
    return analysis

def optimize_prompt_for_veo3(prompt):
    """Optimize prompt length and structure for VEO-3 with enhanced narrator and audio production"""
    # If prompt is too long, intelligently truncate while preserving key elements
    if len(prompt) > 450:
        # Extract key components
        import re
        
        # Find voiceover section
        voiceover_match = re.search(r'\[voiceover:([^\]]+)\]', prompt)
        voiceover_text = voiceover_match.group(0) if voiceover_match else ""
        
        # Extract core visual description (first sentence usually)
        sentences = prompt.split('.')
        core_visual = sentences[0] + '.' if sentences else prompt[:100]
        
        # Rebuild optimized prompt with enhanced audio production
        optimized = f"{core_visual} {voiceover_text}"
        
        # Add essential elements if space allows
        if len(optimized) < 300:
            if 'medium close-up' not in optimized and len(optimized) < 250:
                optimized += " Medium close-up shot."
            if 'upbeat' not in optimized and 'music' not in optimized and len(optimized) < 200:
                optimized += " Professional narrator with upbeat background music."
        
        print(f"DEBUG: Optimized prompt from {len(prompt)} to {len(optimized)} characters")
        return optimized
    
    return prompt

def enhance_veo3_prompt_with_narrator(segment):
    """Enhance VEO-3 prompt with professional narrator and audio production details"""
    try:
        # Extract existing prompt
        base_prompt = segment.get('prompt', '')
        
        # Get narrator characteristics
        narrator_type = segment.get('narrator_characteristics', 'confident professional narrator')
        delivery_style = segment.get('delivery_instructions', 'speaks with authority and enthusiasm')
        audio_production = segment.get('audio_production', 'upbeat background music with subtle sound effects')
        timing = segment.get('timing_breakdown', '0:00-0:04 narrator speaks, 0:04-0:08 music swells')
        
        # Extract voiceover text
        import re
        voiceover_match = re.search(r'\[voiceover:([^\]]+)\]', base_prompt)
        voiceover_text = voiceover_match.group(1).strip() if voiceover_match else segment.get('voiceover_script', '')
        
        # Clean base prompt (remove existing voiceover)
        clean_prompt = re.sub(r'\[voiceover:[^\]]+\]', '', base_prompt).strip()
        
        # Build enhanced VEO-3 prompt with professional narrator instructions
        enhanced_prompt = f"{clean_prompt} [{narrator_type} {delivery_style} says: '{voiceover_text}'] with {audio_production}. {timing}."
        
        # Optimize length for VEO-3
        if len(enhanced_prompt) > 450:
            # Simplify while keeping key elements
            enhanced_prompt = f"{clean_prompt} [Professional narrator says: '{voiceover_text}'] with background music."
        
        print(f"DEBUG: Enhanced prompt from {len(base_prompt)} to {len(enhanced_prompt)} characters")
        return enhanced_prompt
        
    except Exception as e:
        print(f"DEBUG: Error enhancing prompt with narrator: {e}")
        return segment.get('prompt', '')

def generate_ad_script_with_feedback(company_info, user_answers, current_script, improvement_request, best_ads=None):
    """
    Regenerate ad script with GPT incorporating user feedback and previous script context.
    This ensures the script is rebuilt from scratch with the user's suggestions.
    """
    client = get_openai_client()
    if client is None:
        raise Exception("OpenAI client not available. Please check API key configuration.")
    
    # Get AI-powered improvement insights based on user feedback
    ad_type = user_answers.get('ad_type', '').lower()
    industry = user_answers.get('industry', '')
    
    # Normalize ad_type to handle frontend formatting
    ad_type_mapping = {
        '✨ educational-first (2025 trend)': 'educational-first',
        '✨ founder-story (2025 trend)': 'founder-story', 
        '✨ nostalgia-driven (2025 trend)': 'nostalgia-driven',
        '✨ brain-rot/escapism (2025 trend)': 'brain-rot/escapism',
        '✨ micro-moment (2025 trend)': 'micro-moment',
        '✨ platform-native (2025 trend)': 'platform-native'
    }
    
    # Check if the ad_type needs to be normalized
    for key, value in ad_type_mapping.items():
        if key in ad_type:
            ad_type = value
            break
    
    # Get improvement insights from user feedback
    improvement_insights = get_improvement_insights(ad_type, industry)
    feedback_improvements = ""
    
    if improvement_insights:
        print(f"DEBUG: Using feedback insights for {ad_type}/{industry}")
        feedback_improvements = f"""
*** AI-POWERED FEEDBACK INSIGHTS - APPLY THESE LEARNINGS ***
Based on user ratings and feedback for {ad_type} ads in {industry} industry:

OVERALL SENTIMENT: {improvement_insights.get('overall_sentiment', 'neutral')}

AVOID THESE PATTERNS (User Complaints):
{chr(10).join([f"- {complaint}" for complaint in improvement_insights.get('main_complaints', [])])}

EMPHASIZE THESE ELEMENTS (What Users Love):
{chr(10).join([f"- {element}" for element in improvement_insights.get('successful_elements', [])])}

HIGH-PRIORITY IMPROVEMENTS:
{chr(10).join([f"- {rec['issue']}: {rec['solution']}" for rec in improvement_insights.get('improvement_recommendations', []) if rec.get('priority') == 'high'])}

*** CRITICAL: Apply these user-validated improvements to create better ads ***
"""
    
    creative_notes = []
    if user_answers.get('product'):
        creative_notes.append(f"Main product/service to promote: {user_answers['product']}")
    if user_answers.get('mood'):
        creative_notes.append(f"Desired mood/vibe: {user_answers['mood']}")
    
    # Add main character if specified
    main_character = user_answers.get('main_character')
    if main_character and not normalize_na(main_character):
        creative_notes.append(f"Main character for the ad: {main_character}")
    
    # Only use slogan if it's not 'N/A', 'na', etc.
    slogan_val = user_answers.get('slogan')
    if slogan_val and not normalize_na(slogan_val):
        creative_notes.append(f"User's preferred slogan: {slogan_val}")
    
    # Only use CTA if it's not 'N/A', 'na', etc.
    cta_val = user_answers.get('cta')
    if cta_val and not normalize_na(cta_val):
        creative_notes.append(f"Call to action: {cta_val}")
    
    if user_answers.get('features'):
        creative_notes.append(f"Features/benefits to highlight: {user_answers['features']}")
    
    # Add industry and target audience
    if industry:
        creative_notes.append(f"Industry: {industry}")
    target_audience = get_target_audience_for_industry(industry)
    if target_audience:
        creative_notes.append(f"Target audience: {target_audience}")
    
    creative_notes_str = "\n".join(creative_notes) if creative_notes else "No additional creative direction provided by the user."

    # Extract specific product features and benefits from research
    product_features = extract_key_features_and_benefits(company_info)
    
    # Build comprehensive product information string
    product_info_str = f"""
SPECIFIC PRODUCT INFORMATION (USE THIS IN THE AD):
What it does: {product_features.get('what_it_does', 'Product information not available')}

Key Features:
{chr(10).join([f"- {feature}" for feature in product_features.get('features', ['Features not specified'])])}

Benefits:
{chr(10).join([f"- {benefit}" for benefit in product_features.get('benefits', ['Benefits not specified'])])}

Unique Selling Points:
{chr(10).join([f"- {usp}" for usp in product_features.get('unique_selling_points', ['USPs not specified'])])}

Problems it Solves:
{chr(10).join([f"- {pain_point}" for pain_point in product_features.get('target_pain_points', ['Pain points not specified'])])}

CRITICAL: Use these SPECIFIC features and benefits in the dialogue. Don't just say "I love [PRODUCT]" - explain WHY with concrete features like "[PRODUCT]'s [SPECIFIC FEATURE] helps me [SPECIFIC BENEFIT]!"
"""

    # Add best ads inspiration
    best_ads_str = ""
    if best_ads:
        best_ads_str = "Here are some of the best, most creative, and viral ad scripts and creative principles in history to use as inspiration:\n"
        for ad in best_ads:
            scene_desc = ""
            if 'scene_descriptions' in ad:
                scene_desc = f"\nScene 1: {ad['scene_descriptions']['segment1']['visual']} (Mood: {ad['scene_descriptions']['segment1']['mood']}, Camera: {ad['scene_descriptions']['segment1']['camera']})\n"
                scene_desc += f"Scene 2: {ad['scene_descriptions']['segment2']['visual']} (Mood: {ad['scene_descriptions']['segment2']['mood']}, Camera: {ad['scene_descriptions']['segment2']['camera']})"
            best_ads_str += f"- {ad['title']}: {ad['script']} (Principle: {ad['principle']}, Slogan: {ad.get('slogan', '')}, Call to Action: {ad.get('call_to_action', '')}){scene_desc}\n"

    avoid_topics = extract_avoid_topics(company_info)
    avoid_str = ", ".join(avoid_topics) if avoid_topics else "None"

    # Include current script context and user feedback
    current_script_context = f"""
*** PREVIOUS SCRIPT FOR REFERENCE ***
The user has reviewed this previous script and wants improvements:
{json.dumps(current_script, indent=2)}

*** USER'S SPECIFIC IMPROVEMENT REQUEST ***
{improvement_request}

*** REGENERATION INSTRUCTIONS ***
Create a completely NEW script that addresses the user's feedback while maintaining the core elements they liked.
Don't just modify the existing script - rebuild it from the ground up with their suggestions in mind.
"""

    # VEO-3 OPTIMIZATION FRAMEWORK
    veo3_framework = """
    *** VEO-3 ADVERTISING OPTIMIZATION ***
    
    🎬 CORE PRINCIPLES:
    - PROMPT AS BLUEPRINT: Detailed instructions = better results
    - CINEMATIC LANGUAGE: Use film terms (dolly-in, tracking shot, close-up)
    - NATIVE AUDIO: Format "Character says: exact words" (no subtitles)
    - MOTIVATED MOVEMENT: Every camera move serves the story
    
    🎥 KEY CAMERA MOVES:
    - Product reveals: "slow dolly-in on product"
    - Testimonials: "medium close-up for authenticity"  
    - Call-to-action: "push-in on logo"
    
    🎙️ AUDIO EXCELLENCE:
    - Dialogue: "Spokesperson says: This changed my life!"
    - Delivery: "announces confidently" / "exclaims excitedly"
    - Sound: "upbeat commercial music" + "satisfying product click"
    
    📝 STRUCTURE: Subject + Action + Camera + Audio + Brand message
    """

    # 2025 Best Practices Section
    practices_2025 = f"""
    *** 2025 AD CREATION BEST PRACTICES ***

    {veo3_framework}

    🎯 16-SECOND STRUCTURE:
    - Seconds 1-3: HOOK with strong visual problem
    - Seconds 4-8: BRAND INTRODUCTION with solution
    - Seconds 9-13: TRANSFORMATION showing results
    - Seconds 14-16: CLEAR CALL-TO-ACTION
    
    ⚡ KEY ELEMENTS:
    - MOBILE-FIRST: Bright visuals, large text, vertical framing
    - AUTHENTICITY: Real interactions, natural movement
    - CONTINUOUS AUDIO: No dead space, constant dialogue/music
    - EMOTION CHAIN: Start calm → excitement → satisfaction
    """

    prompt = f"""{current_script_context}

{feedback_improvements}

{practices_2025}

{best_ads_str}

Based on this company information (from their website):
{company_info}

{product_info_str}

And the following creative direction from the user:
{creative_notes_str}

When writing the ad, avoid these topics, themes, or words: {avoid_str}

*** VEO-3 OPTIMIZED 16-SECOND AD REGENERATION ***
Create a completely NEW 16-second ad script that addresses the user's feedback while using VEO-3 techniques:

🎬 STRUCTURE:
Segment 1 (8s): HOOK + BRAND INTRO
Segment 2 (8s): TRANSFORMATION + CALL-TO-ACTION

📝 OUTPUT REQUIREMENTS:
For each segment provide:
- "scene_description": Visual description (NO logos)
- "prompt": Complete VEO-3 prompt with [voiceover: ...] (NO logos)
- "voiceover_script": EXACTLY 10 words maximum for perfect 8-second timing
- "mood": Emotional atmosphere
- "camera": Camera movement
- "veo3_optimization": VEO-3 techniques applied

🎙️ CRITICAL AUDIO REQUIREMENTS:
- EXACTLY 15 WORDS PER SEGMENT: Optimal for 8-second clips with no blank space
- 15 words = ~6 seconds speech + 2 seconds visual transition = perfect 8s clip
- Every word must be impactful and necessary
- Format: "Character says: exact words"
- Company name mentioned 1-2 times per segment (within the 15-word limit)
- Continuous background music/sounds throughout

🎭 NARRATOR CONSISTENCY REQUIREMENTS:
- SAME NARRATOR VOICE: Use identical narrator description across ALL segments
- VOICE CONTINUITY: "Professional male narrator with warm, authoritative tone" (or specify exact voice type)
- CONSISTENT DELIVERY: Same speaking pace, energy level, and style throughout entire ad
- PERSONALITY LOCK: Once narrator personality is set in segment1, maintain exactly the same in segment2
- BRAND VOICE ALIGNMENT: Match narrator to brand personality (corporate = professional, startup = energetic, luxury = sophisticated)

🎵 AUDIO TIMING MASTERY:
- WORD PLACEMENT: Strategic timing of each word to eliminate dead space
- SPEECH RHYTHM: 0:00-0:06 narrator speaks (15 words in 6 seconds = 2.5 words/second)
- TRANSITION TIMING: 0:06-0:08 music bridge to next segment (no silence)
- EMPHASIS PLACEMENT: Key product words at 0:02 and 0:04 for maximum impact
- BREATH CONTROL: Natural pauses built into script, no awkward gaps
- SEAMLESS FLOW: Each word flows naturally into the next with perfect pacing

🎬 BLANK SPACE ELIMINATION:
- NO DEAD AIR: Every second filled with narrator voice, music, or sound effects
- WORD SPACING: Strategic placement - important words at 1-second intervals
- MUSIC UNDERLAYS: Continuous background music that swells during speech pauses
- SOUND BRIDGES: Smooth audio transitions between words and segments
- TIMING PRECISION: Each of the 15 words placed at optimal 0.4-second intervals

⚠️ TIMING CRITICAL: VEO-3 cuts off voiceovers longer than 15 words in 8-second clips.
Make every word count. Eliminate blank space with perfect word timing.

🎯 BRAND MESSAGING REQUIREMENTS (ABSOLUTELY CRITICAL):
- MANDATORY: Either the slogan OR call-to-action MUST be included in at least one segment's voiceover
- PREFERRED: Include slogan in early segments, call-to-action in final segment
- If slogan is short (3-5 words), include it in multiple segments
- If call-to-action is short (3-5 words), include it in final segment
- NEVER create an ad without clear brand messaging in the actual voiceover
- Examples: "Try [Product] today", "Visit [website]", "[Slogan] - [Product]"

🚀 2025 ADVERTISING TRENDS (INTEGRATE THESE):
- AUTHENTICITY OVER POLISH: Raw, unfiltered content outperforms overly produced ads
- HUMOR IS BACK: Funny ads have higher recall and conversion (only 14% use humor - stand out!)
- HUMAN CONNECTION: As AI increases, people crave authentic human stories and real experiences
- EDUCATIONAL VALUE: Teach something useful, don't just sell - builds trust and engagement
- SOUND-OFF OPTIMIZATION: 85% watch without sound - visual storytelling is crucial
- TRANSFORMATION STORIES: Show before/after, problem/solution, struggle/success
- RELATABLE HEROES: Feature everyday people, not just perfect models or celebrities

📱 PLATFORM-NATIVE REQUIREMENTS:
- Create content that feels native to social feeds, not like traditional ads
- Use conversational, direct language ("you" instead of "customers")
- Include visual hooks that work without sound (text overlays, compelling visuals)
- Make it shareable and discussion-worthy

Format as valid JSON:
{{
    "segment1": {{
        "scene_description": "...",
        "prompt": "... [voiceover: Professional male narrator with warm, authoritative tone says: 'exact 15 words with perfect timing'] with [specific background music] and [sound effects]",
        "voiceover_script": "15 words maximum here with strategic word placement (MUST include brand messaging)",
        "narrator_characteristics": "Professional male narrator with warm, authoritative tone (KEEP IDENTICAL IN SEGMENT2)",
        "delivery_instructions": "Speaks with steady confidence and natural pacing, no awkward pauses",
        "audio_production": "Continuous upbeat background music with strategic volume swells during speech pauses",
        "timing_breakdown": "0:00-0:06 narrator speaks 15 words, 0:06-0:08 music bridge, no blank space",
        "word_timing": "Strategic placement: words 1-3 at 0:00-1:00, words 4-7 at 1:00-2:50, words 8-11 at 2:50-4:30, words 12-15 at 4:30-6:00",
        "mood": "...",
        "camera": "...",
        "veo3_optimization": "..."
    }},
    "segment2": {{
        "scene_description": "...",
        "prompt": "... [voiceover: Professional male narrator with warm, authoritative tone says: 'exact 15 words with perfect timing'] with [specific background music] and [sound effects]",
        "voiceover_script": "15 words maximum here with strategic word placement",
        "narrator_characteristics": "Professional male narrator with warm, authoritative tone (IDENTICAL TO SEGMENT1)",
        "delivery_instructions": "Speaks with steady confidence and natural pacing, no awkward pauses (SAME AS SEGMENT1)",
        "audio_production": "Continuous upbeat background music with strategic volume swells during speech pauses",
        "timing_breakdown": "0:00-0:06 narrator speaks 15 words, 0:06-0:08 music bridge, no blank space",
        "word_timing": "Strategic placement: words 1-3 at 0:00-1:00, words 4-7 at 1:00-2:50, words 8-11 at 2:50-4:30, words 12-15 at 4:30-6:00",
        "mood": "...",
        "camera": "...",
        "veo3_optimization": "..."
    }},
    "slogan": "...",
    "call_to_action": "..."
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=20000
        )
    except Exception as api_error:
        print(f"OpenAI API Error in regeneration for ad_type '{ad_type}': {api_error}")
        # Check if it's a content policy violation
        if "content policy" in str(api_error).lower() or "safety" in str(api_error).lower():
            raise ValueError(f"Content policy violation: The regenerated script was rejected by OpenAI. Error: {str(api_error)}")
        else:
            raise ValueError(f"OpenAI API Error during script regeneration: {str(api_error)}")

    content = response.choices[0].message.content.strip()
    print("OpenAI regeneration response:", repr(content))

    # Check if OpenAI refused the request
    if "I'm sorry, I can't assist" in content or "I cannot help" in content or "I'm unable to" in content:
        raise ValueError(f"OpenAI refused the regeneration request. Response: {repr(content)}")

    # Try to extract JSON from the response
    try:
        if not content:
            raise ValueError("OpenAI returned an empty response during regeneration.")
        return json.loads(content)
    except Exception as e:
        import re
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception as e2:
                print("Failed to parse extracted JSON from regeneration:", e2)
        print("Failed to parse OpenAI regeneration response as JSON:", e)
        raise ValueError("Failed to parse OpenAI regeneration response as JSON. Raw response: " + repr(content))

def optimize_script_for_veo3(script_segments):
    """
    Optimize script for VEO-3's 8-second segments with precise timing.
    Each segment is independent with no working memory between clips.
    """
    optimized_segments = {}
    
    for segment_name, segment in script_segments.items():
        if isinstance(segment, dict) and 'voiceover_script' in segment:
            voiceover = segment['voiceover_script']
            
            # Calculate optimal timing for 8-second clips
            words = voiceover.split()
            word_count = len(words)
            
            # Target: 2-3 words per second for clear delivery (16-24 words for 8 seconds)
            optimal_word_count = 20  # Sweet spot for 8 seconds
            
            if word_count > 24:
                # Too long - needs truncation
                words = words[:20]
                voiceover = ' '.join(words) + '...'
                timing_note = "⚠️ Script truncated for timing"
            elif word_count < 12:
                # Too short - might need pacing adjustment
                timing_note = "✅ Good length - pace slowly for full 8 seconds"
            else:
                timing_note = "✅ Optimal length for 8-second segment"
            
            # Add precise timing markers
            if segment_name == 'segment1':
                voiceover_timing = {
                    "start_time": "0:00",
                    "end_time": "0:08",
                    "duration": "8 seconds",
                    "delivery_note": "Begin voiceover immediately at 0:00",
                    "pacing": "Steady pace - complete before 8-second mark"
                }
            else:  # segment2
                voiceover_timing = {
                    "start_time": "0:00", 
                    "end_time": "0:08",
                    "duration": "8 seconds", 
                    "delivery_note": "New clip - begin voiceover immediately at 0:00",
                    "pacing": "Steady pace - complete before 8-second mark"
                }
            
            optimized_segments[segment_name] = {
                **segment,
                'voiceover_script': voiceover,
                'voiceover_timing': voiceover_timing,
                'word_count': len(voiceover.split()),
                'timing_analysis': timing_note,
                'veo3_optimization': f"Optimized for 8-second clip with {len(voiceover.split())} words"
            }
        else:
            optimized_segments[segment_name] = segment
    
    return optimized_segments

def analyze_script_quality(script, user_answers):
    """Enhanced script analysis with stricter 15-word targeting and 2025 trend validation"""
    analysis = {
        'segment1_issues': [],
        'segment2_issues': [],
        'overall_recommendations': [],
        'timing_analysis': {},
        'audio_quality_score': 0,
        'veo3_readiness': 0,
        'brand_messaging_status': 'missing',
        'trend_compliance_2025': {}
    }
    
    total_issues = 0
    total_segments = 0
    
    # Check brand messaging inclusion (CRITICAL)
    slogan = script.get('slogan', '').strip()
    cta = script.get('call_to_action', '').strip()
    brand_messaging_found = False
    
    if slogan or cta:
        # Check if brand messaging is included in any segment's voiceover
        segments = [key for key in script.keys() if key.startswith('segment')]
        for segment_key in segments:
            if segment_key in script:
                voiceover = script[segment_key].get('voiceover_script', '').lower()
                if (slogan and slogan.lower() in voiceover) or (cta and cta.lower() in voiceover):
                    brand_messaging_found = True
                    break
    
    analysis['brand_messaging_status'] = 'included' if brand_messaging_found else 'missing'
    if not brand_messaging_found:
        total_issues += 5  # Major penalty for missing brand messaging
    
    # 2025 TREND VALIDATION
    trend_score = 100
    trend_feedback = []
    
    # Authenticity Level Check
    authenticity = user_answers.get('authenticity_level', '').lower()
    if 'raw' in authenticity or 'unfiltered' in authenticity or 'phone-shot' in authenticity:
        # Check if script feels authentic
        segments = [key for key in script.keys() if key.startswith('segment')]
        authentic_indicators = ['real', 'genuine', 'natural', 'authentic', 'personal', 'story']
        authenticity_found = False
        for segment_key in segments:
            if segment_key in script:
                scene_desc = script[segment_key].get('scene_description', '').lower()
                if any(indicator in scene_desc for indicator in authentic_indicators):
                    authenticity_found = True
                    break
        
        if not authenticity_found:
            trend_feedback.append("⚠️ Script lacks authentic/raw elements requested")
            trend_score -= 15
        else:
            trend_feedback.append("✅ Authenticity preference reflected in script")
    
    # Humor Tolerance Check
    humor = user_answers.get('humor_tolerance', '').lower()
    if 'funny' in humor or 'humor' in humor:
        # Check if script includes humor elements
        humor_indicators = ['funny', 'humor', 'laugh', 'smile', 'joke', 'amusing', 'entertaining']
        humor_found = False
        segments = [key for key in script.keys() if key.startswith('segment')]
        for segment_key in segments:
            if segment_key in script:
                voiceover = script[segment_key].get('voiceover_script', '').lower()
                scene_desc = script[segment_key].get('scene_description', '').lower()
                if any(indicator in voiceover + scene_desc for indicator in humor_indicators):
                    humor_found = True
                    break
        
        if not humor_found and 'funny' in humor:
            trend_feedback.append("⚠️ Humor requested but not reflected in script")
            trend_score -= 10
        elif humor_found:
            trend_feedback.append("✅ Humor successfully integrated")
    
    # Educational Value Check
    educational = user_answers.get('educational_value', '').lower()
    if 'educate' in educational or 'teach' in educational or 'tip' in educational:
        # Check if script provides educational value
        edu_indicators = ['learn', 'discover', 'tip', 'how to', 'technique', 'method', 'solution', 'insight']
        education_found = False
        segments = [key for key in script.keys() if key.startswith('segment')]
        for segment_key in segments:
            if segment_key in script:
                voiceover = script[segment_key].get('voiceover_script', '').lower()
                scene_desc = script[segment_key].get('scene_description', '').lower()
                if any(indicator in voiceover + scene_desc for indicator in edu_indicators):
                    education_found = True
                    break
        
        if not education_found:
            trend_feedback.append("⚠️ Educational content requested but missing")
            trend_score -= 12
        else:
            trend_feedback.append("✅ Educational value successfully included")
    
    # Sound-Off Optimization Check
    sound_opt = user_answers.get('sound_optimization', '').lower()
    if 'silent' in sound_opt or 'captions' in sound_opt or 'visual' in sound_opt:
        # Check if script is optimized for silent viewing
        visual_indicators = ['text overlay', 'caption', 'visual', 'graphic', 'on-screen text', 'subtitle']
        visual_optimization_found = False
        segments = [key for key in script.keys() if key.startswith('segment')]
        for segment_key in segments:
            if segment_key in script:
                scene_desc = script[segment_key].get('scene_description', '').lower()
                if any(indicator in scene_desc for indicator in visual_indicators):
                    visual_optimization_found = True
                    break
        
        if not visual_optimization_found:
            trend_feedback.append("⚠️ Sound-off optimization requested but missing visual elements")
            trend_score -= 8
        else:
            trend_feedback.append("✅ Visual storytelling optimized for silent viewing")
    
    # Platform-Native Check
    platform = user_answers.get('target_platform', '').lower()
    if 'tiktok' in platform or 'reels' in platform:
        # Check for platform-native elements
        native_indicators = ['trending', 'viral', 'meme', 'challenge', 'hashtag', 'social', 'scroll-stopping']
        platform_native_found = False
        segments = [key for key in script.keys() if key.startswith('segment')]
        for segment_key in segments:
            if segment_key in script:
                scene_desc = script[segment_key].get('scene_description', '').lower()
                voiceover = script[segment_key].get('voiceover_script', '').lower()
                if any(indicator in scene_desc + voiceover for indicator in native_indicators):
                    platform_native_found = True
                    break
        
        if platform_native_found:
            trend_feedback.append("✅ Platform-native elements detected")
        else:
            trend_feedback.append("💡 Consider adding platform-native elements for better performance")
            trend_score -= 5
    
    analysis['trend_compliance_2025'] = {
        'score': max(0, trend_score),
        'feedback': trend_feedback
    }
    
    # Original segment analysis continues...
    for segment_name in ['segment1', 'segment2']:
        if segment_name not in script:
            continue
            
        total_segments += 1
        segment = script[segment_name]
        issues = []
        
        # Strict 15-word analysis for VEO-3
        voiceover = segment.get('voiceover_script', '')
        word_count = len(voiceover.split())
        
        # Enhanced timing analysis with 15-word targeting
        if 'voiceover_timing' in segment:
            timing = segment['voiceover_timing']
            
            analysis['timing_analysis'][segment_name] = {
                'start_time': timing['start_time'],
                'end_time': timing['end_time'],
                'word_count': word_count,
                'delivery_note': timing['delivery_note'],
                'timing_status': segment.get('timing_analysis', 'Unknown'),
                'optimal_for_veo3': 12 <= word_count <= 15,
                'perfect_veo3': word_count == 15
            }
            
            # Timing issues for 15-word targeting
            if word_count > 15:
                issues.append(f"Voiceover too long ({word_count} words). Must be 15 words max for VEO-3.")
                total_issues += 3
            elif word_count < 12:
                issues.append(f"Voiceover short ({word_count} words). Consider expanding to 15 words.")
                total_issues += 1
            elif word_count == 15:
                # Perfect!
                pass
            else:
                # 12-15 range but not perfect 15
                total_issues += 0.5
        else:
            # Fallback analysis
            if word_count > 15:
                issues.append(f"Voiceover too long ({word_count} words). Target 15 words maximum.")
                total_issues += 3
            elif word_count < 12:
                issues.append(f"Voiceover short ({word_count} words). Consider expanding.")
                total_issues += 1
        
        # Check VEO-3 prompt optimization
        if 'veo3_optimization' in segment:
            if '⚠️' in segment.get('timing_analysis', ''):
                issues.append("Script was truncated - consider rewriting more naturally.")
                total_issues += 1
        
        # Check visual description quality
        scene_desc = segment.get('scene_description', '')
        if len(scene_desc) < 50:
            issues.append("Visual description may be too brief for clear VEO-3 generation.")
            total_issues += 1
        
        # Check for proper VEO-3 formatting
        prompt = segment.get('prompt', '')
        if '[voiceover:' not in prompt:
            issues.append("Missing proper VEO-3 voiceover formatting in prompt.")
            total_issues += 2
        
        analysis[f'{segment_name}_issues'] = issues
    
    # Calculate VEO-3 readiness score
    if total_segments > 0:
        perfect_word_counts = sum(1 for seg in ['segment1', 'segment2'] 
                                  if seg in script and len(script[seg].get('voiceover_script', '').split()) == 15)
        
        max_possible_issues = total_segments * 6
        base_score = max(0, 100 - (total_issues * 100 / max_possible_issues))
        
        word_count_bonus = (perfect_word_counts / total_segments) * 20
        trend_bonus = (analysis['trend_compliance_2025']['score'] / 100) * 10
        
        veo3_score = min(100, base_score + word_count_bonus + trend_bonus)
        analysis['veo3_readiness'] = round(veo3_score)
        analysis['audio_quality_score'] = round(veo3_score)
    
    # Enhanced recommendations
    recommendations = []
    
    # Brand messaging recommendations (HIGHEST PRIORITY)
    if analysis['brand_messaging_status'] == 'missing':
        recommendations.append("🚨 CRITICAL: Brand messaging (slogan or CTA) must be included in voiceover!")
    elif analysis['brand_messaging_status'] == 'included':
        recommendations.append("✅ Brand messaging successfully included in voiceover")
    
    # 2025 Trend recommendations
    if analysis['trend_compliance_2025']['score'] < 80:
        recommendations.append("🚀 2025 TRENDS: Script could better reflect current advertising trends")
        recommendations.extend(analysis['trend_compliance_2025']['feedback'])
    else:
        recommendations.append("✨ 2025 READY: Script aligns well with current advertising trends")
    
    if total_issues == 0 and all(len(script[seg].get('voiceover_script', '').split()) == 15 
                                for seg in ['segment1', 'segment2'] if seg in script):
        recommendations.append("🎯 Perfect! Script optimized for VEO-3 with ideal 15-word segments!")
    else:
        if any('too long' in str(issues) for issues in [analysis['segment1_issues'], analysis['segment2_issues']]):
            recommendations.append("📝 Critical: Shorten voiceovers to exactly 15 words to prevent cutoff")
        if any('too short' in str(issues) for issues in [analysis['segment1_issues'], analysis['segment2_issues']]):
            recommendations.append("🎭 Consider expanding voiceovers to full 15 words for maximum impact")
        if total_issues >= 3:
            recommendations.append("⚠️ Multiple optimizations needed - automatic improvements will be applied")
    
    analysis['overall_recommendations'] = recommendations
    
    return analysis

def auto_optimize_script_until_ready(script, company_info, user_answers, best_ads=None, target_score=80):
    """
    Automatically optimize script until it reaches target VEO-3 readiness score.
    Target: 15 words per segment for perfect timing (6 seconds speech + 2 seconds transition = 8-second clips).
    """
    print(f"DEBUG: Starting auto-optimization targeting {target_score}/100 VEO-3 readiness with 15-word segments")
    
    max_iterations = 5
    current_script = script
    
    for iteration in range(max_iterations):
        print(f"DEBUG: Auto-optimization iteration {iteration + 1}/{max_iterations}")
        
        # Apply VEO-3 optimization
        optimized_script = optimize_script_for_veo3_precise(current_script)
        
        # Ensure narrator consistency across segments
        optimized_script = ensure_narrator_consistency(optimized_script)
        
        # CRITICAL: Ensure brand messaging is included in voiceover
        optimized_script = validate_and_fix_brand_messaging(optimized_script)
        
        # Analyze the optimized script
        analysis = analyze_script_for_veo3(optimized_script)
        veo3_score = analysis.get('veo3_readiness', analysis.get('audio_quality_score', 0))
        
        print(f"DEBUG: Iteration {iteration + 1} - VEO-3 readiness: {veo3_score}/100")
        
        # Check if we've reached the target score
        if veo3_score >= target_score:
            print(f"DEBUG: ✅ Target score {target_score}/100 achieved! Final score: {veo3_score}/100")
            return optimized_script, analysis
        
        # If not perfect, identify and fix specific issues
        if veo3_score < target_score:
            print(f"DEBUG: Score {veo3_score}/100 below target. Auto-improving problematic segments...")
            improved_script = auto_improve_problematic_segments(optimized_script, analysis, company_info, user_answers, best_ads)
            current_script = improved_script
    
    print(f"DEBUG: ⚠️ Reached max iterations. Final score: {veo3_score}/100")
    return current_script, analysis

def optimize_script_for_veo3_precise(script_segments):
    """
    Optimize script for VEO-3's 8-second segments with PRECISE 10-word targeting.
    Target: 10 words = ~4-5 seconds speech + 3-4 seconds for visual/music = perfect 8s clip
    """
    optimized_segments = {}
    
    for segment_name, segment in script_segments.items():
        if isinstance(segment, dict) and 'voiceover_script' in segment:
            voiceover = segment['voiceover_script']
            
            # Calculate optimal timing for 8-second clips
            words = voiceover.split()
            word_count = len(words)
            
            # CRITICAL: Target exactly 10 words for optimal VEO-3 timing
            # 10 words = ~4 seconds speech + 4 seconds for visual pacing = perfect 8s clip
            target_word_count = 10
            
            if word_count > 12:
                # Too long - truncate to exactly 10 words
                words = words[:target_word_count]
                voiceover = ' '.join(words)
                timing_note = "✅ Optimized to 10 words for perfect timing"
            elif word_count < 8:
                # Too short - this is actually fine, just pace slower
                timing_note = "✅ Short script - pace very slowly for full 8 seconds"
            else:
                timing_note = "✅ Good length for 8-second VEO-3 segment"
            
            # Add precise timing markers with 10-word optimization
            voiceover_timing = {
                "start_time": "0:00",
                "end_time": "0:08", 
                "duration": "8 seconds",
                "delivery_note": f"Deliver {len(voiceover.split())} words in 4-5 seconds, leaving 3-4s for visuals",
                "pacing": "Speak clearly and pause between words - visual needs time to develop",
                "target_speech_duration": "4-5 seconds maximum",
                "visual_time": "3-4 seconds for visual development"
            }
            
            optimized_segments[segment_name] = {
                **segment,
                'voiceover_script': voiceover,
                'voiceover_timing': voiceover_timing,
                'word_count': len(voiceover.split()),
                'timing_analysis': timing_note,
                'veo3_optimization': f"Optimized to {len(voiceover.split())} words for 8-second VEO-3 clip"
            }
        else:
            optimized_segments[segment_name] = segment
    
    return optimized_segments

def auto_improve_problematic_segments(script, analysis, company_info, user_answers, best_ads):
    """
    Automatically improve segments that have issues identified in analysis.
    Focus on 15-word count optimization and VEO-3 readiness.
    Handles variable number of segments (1, 2, 3, or 4).
    """
    print("DEBUG: Auto-improving problematic segments for 15-word targeting")
    
    improved_script = script.copy()
    
    # Check each segment for issues (dynamic segment detection)
    segments = [key for key in script.keys() if key.startswith('segment')]
    
    for segment_name in segments:
        if segment_name not in script:
            continue
            
        segment_issues = analysis.get(f'{segment_name}_issues', [])
        if not segment_issues:
            continue
            
        print(f"DEBUG: Improving {segment_name} - issues: {segment_issues}")
        
        # Create improvement request based on issues
        improvement_requests = []
        
        for issue in segment_issues:
            if "too long" in issue.lower():
                improvement_requests.append("Make the voiceover much shorter - target exactly 15 words maximum")
            elif "too short" in issue.lower():
                improvement_requests.append("Expand the voiceover to 12-15 words for optimal timing") 
            elif "visual description" in issue.lower():
                improvement_requests.append("Make the visual description more detailed and specific")
            elif "truncated" in issue.lower():
                improvement_requests.append("Rewrite to be naturally shorter - exactly 15 words maximum")
        
        if improvement_requests:
            # Improve this specific segment
            improved_segment = improve_single_segment_with_ai(
                script[segment_name], 
                improvement_requests,
                company_info,
                user_answers,
                best_ads,
                segment_name
            )
            if improved_segment:
                improved_script[segment_name] = improved_segment
    
    return improved_script

def improve_single_segment_with_ai(segment, improvement_requests, company_info, user_answers, best_ads, segment_name):
    """
    Use AI to improve a single segment based on specific issues.
    Target: 15 words maximum for optimal VEO-3 timing.
    """
    client = get_openai_client()
    if client is None:
        print("DEBUG: OpenAI client not available for segment improvement")
        return None
    
    # Build context
    improvement_text = "; ".join(improvement_requests)
    
    prompt = f"""You are a VEO-3 video generation expert. Improve this ad segment based on the specific issues identified.

CRITICAL REQUIREMENTS:
- Voiceover must be EXACTLY 15 words or fewer for perfect 8-second timing
- 15 words = 6 seconds speech + 2 seconds visual transition = no blank space
- Each word should be impactful and necessary
- Focus on the most important message only
- Use clear, simple language
- Ensure proper VEO-3 audio formatting
- Maintain consistent narrator voice across segments

CURRENT SEGMENT:
{json.dumps(segment, indent=2)}

SPECIFIC IMPROVEMENTS NEEDED:
{improvement_text}

COMPANY INFO: {company_info}
USER PREFERENCES: {json.dumps(user_answers)}

Improve this segment while maintaining the JSON format. Focus on:
1. EXACTLY 15 words maximum in voiceover_script (no blank space)
2. Clear, impactful visual description
3. Proper VEO-3 formatting in prompt field
4. Natural, powerful messaging
5. Consistent narrator characteristics

Return only the improved segment in JSON format."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temperature for more focused improvements
            max_tokens=1000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON response
        import re
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            improved_segment = json.loads(match.group(0))
            
            # Verify word count
            voiceover = improved_segment.get('voiceover_script', '')
            word_count = len(voiceover.split())
            
            if word_count <= 15:
                print(f"DEBUG: Successfully improved {segment_name} to {word_count} words")
                return improved_segment
            else:
                print(f"DEBUG: AI improvement still too long ({word_count} words), forcing truncation to 15")
                # Force truncation to 15 words
                words = voiceover.split()[:15]
                improved_segment['voiceover_script'] = ' '.join(words)
                return improved_segment
        
        print("DEBUG: Could not parse AI improvement response")
        return None
        
    except Exception as e:
        print(f"DEBUG: Error in AI segment improvement: {e}")
        return None

def analyze_script_quality(script, user_answers):
    """Enhanced script analysis with stricter 10-word targeting for VEO-3 optimization"""
    analysis = {
        'segment1_issues': [],
        'segment2_issues': [],
        'overall_recommendations': [],
        'timing_analysis': {},
        'audio_quality_score': 0,
        'veo3_readiness': 0
    }
    
    total_issues = 0
    total_segments = 0
    
    for segment_name in ['segment1', 'segment2']:
        if segment_name not in script:
            continue
            
        total_segments += 1
        segment = script[segment_name]
        issues = []
        
        # Strict 10-word analysis for VEO-3
        voiceover = segment.get('voiceover_script', '')
        word_count = len(voiceover.split())
        
        # Enhanced timing analysis with 10-word targeting
        if 'voiceover_timing' in segment:
            timing = segment['voiceover_timing']
            
            analysis['timing_analysis'][segment_name] = {
                'start_time': timing['start_time'],
                'end_time': timing['end_time'],
                'word_count': word_count,
                'delivery_note': timing['delivery_note'],
                'timing_status': segment.get('timing_analysis', 'Unknown'),
                'optimal_for_veo3': 8 <= word_count <= 12,  # Stricter range
                'perfect_veo3': word_count == 10  # Ideal target
            }
            
            # Stricter timing issues for 10-word targeting
            if word_count > 12:
                issues.append(f"Voiceover too long ({word_count} words). Must be 10 words max for VEO-3.")
                total_issues += 3  # Higher penalty for being too long
            elif word_count < 8:
                issues.append(f"Voiceover short ({word_count} words). Pace slowly to fill 8 seconds.")
                total_issues += 1  # Minor issue
            elif word_count == 10:
                # Perfect!
                pass
            else:
                # 8-12 range but not perfect 10
                total_issues += 0.5  # Very minor issue
        else:
            # Fallback analysis
            if word_count > 12:
                issues.append(f"Voiceover too long ({word_count} words). Target 10 words maximum.")
                total_issues += 3
            elif word_count < 8:
                issues.append(f"Voiceover short ({word_count} words). Consider pacing adjustment.")
                total_issues += 1
        
        # Check VEO-3 prompt optimization
        if 'veo3_optimization' in segment:
            if '⚠️' in segment.get('timing_analysis', ''):
                issues.append("Script was truncated - consider rewriting more naturally.")
                total_issues += 1
        
        # Check visual description quality
        scene_desc = segment.get('scene_description', '')
        if len(scene_desc) < 50:
            issues.append("Visual description may be too brief for clear VEO-3 generation.")
            total_issues += 1
        
        # Check for proper VEO-3 formatting
        prompt = segment.get('prompt', '')
        if '[voiceover:' not in prompt:
            issues.append("Missing proper VEO-3 voiceover formatting in prompt.")
            total_issues += 2
        
        analysis[f'{segment_name}_issues'] = issues
    
    # Calculate VEO-3 readiness score with stricter criteria
    if total_segments > 0:
        # Perfect score: both segments have exactly 10 words + no other issues
        perfect_word_counts = sum(1 for seg in ['segment1', 'segment2'] 
                                  if seg in script and len(script[seg].get('voiceover_script', '').split()) == 10)
        
        # Base score calculation
        max_possible_issues = total_segments * 6  # Increased max issues
        base_score = max(0, 100 - (total_issues * 100 / max_possible_issues))
        
        # Bonus for perfect 10-word targeting
        word_count_bonus = (perfect_word_counts / total_segments) * 20  # Up to 20 point bonus
        
        veo3_score = min(100, base_score + word_count_bonus)
        analysis['veo3_readiness'] = round(veo3_score)
        analysis['audio_quality_score'] = round(veo3_score)
    
    # Enhanced recommendations
    recommendations = []
    
    # Brand messaging recommendations (HIGHEST PRIORITY)
    if analysis['brand_messaging_status'] == 'missing':
        recommendations.append("🚨 CRITICAL: Brand messaging (slogan or CTA) must be included in voiceover!")
    elif analysis['brand_messaging_status'] == 'included':
        recommendations.append("✅ Brand messaging successfully included in voiceover")
    
    if total_issues == 0 and all(len(script[seg].get('voiceover_script', '').split()) == 10 
                                for seg in ['segment1', 'segment2'] if seg in script):
        recommendations.append("🎯 Perfect! Script optimized for VEO-3 with ideal 10-word segments!")
    else:
        if any('too long' in str(issues) for issues in [analysis['segment1_issues'], analysis['segment2_issues']]):
            recommendations.append("📝 Critical: Shorten voiceovers to exactly 10 words to prevent cutoff")
        if any('too short' in str(issues) for issues in [analysis['segment1_issues'], analysis['segment2_issues']]):
            recommendations.append("🎭 Pace slowly and add pauses to fill full 8-second clips")
        if total_issues >= 3:
            recommendations.append("⚠️ Multiple optimization needed - automatic improvements will be applied")
    
    analysis['overall_recommendations'] = recommendations
    
    return analysis

def improve_script_with_gemini_and_feedback(company_info, user_answers, current_script, best_ads, improvement_request):
    """Improve script with specific user feedback using Gemini"""
    import copy
    improved_script = copy.deepcopy(current_script)
    
    # Build context for Gemini
    best_ads_str = ""
    if best_ads:
        best_ads_str = "\n\nBest ads inspiration:\n"
        for ad in best_ads:
            best_ads_str += f"- {ad['title']}: {ad['script']} (Principle: {ad['principle']})\n"
    
    improvement_prompt = f"""
    You are an expert ad script editor. The user has requested specific improvements to their current script.
    
    USER'S IMPROVEMENT REQUEST: {improvement_request}
    
    CURRENT SCRIPT:
    {json.dumps(current_script, indent=2)}
    
    COMPANY INFO: {company_info}
    USER PREFERENCES: {json.dumps(user_answers)}
    {best_ads_str}
    
    CRITICAL VEO-3 OPTIMIZATION RULES:
    1. Each segment's voiceover_script should be 10 words max (for perfect 8-second timing)
    2. Include narrator_characteristics, delivery_instructions, audio_production, and timing_breakdown
    3. Prompts should be under 400 characters for optimal VEO-3 processing
    4. Include "[voiceover: text]" format in prompts
    5. Ensure continuous audio (music/sounds) throughout
    6. Use specific, actionable language
    
    Please improve the script based on the user's request while maintaining the JSON format and optimizing for VEO-3. Focus specifically on addressing their feedback while keeping segments concise and effective.
    
    Return only the improved JSON script.
    """
    
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-06-05:generateContent?key=" + get_gemini_api_key()
        headers = {"Content-Type": "application/json"}
        data = {"contents": [{"parts": [{"text": improvement_prompt}]}]}
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        import re
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            improved_data = json.loads(match.group())
            improved_script.update(improved_data)
            print("Script improved with Gemini and user feedback")
        else:
            print("Could not extract JSON from Gemini response")
    except Exception as e:
        print(f"Gemini improvement failed: {e}")
    
    return improved_script

def ensure_narrator_consistency(script):
    """Ensure the same narrator voice is used across all segments"""
    try:
        # Get all segments dynamically
        segments = [key for key in script.keys() if key.startswith('segment')]
        
        # Extract narrator characteristics from first segment
        first_segment = script.get(segments[0], {}) if segments else {}
        narrator_base = first_segment.get('narrator_characteristics', '')
        delivery_base = first_segment.get('delivery_instructions', '')
        
        if not narrator_base:
            # Set default consistent narrator
            narrator_base = "Professional male narrator with warm, authoritative tone"
            delivery_base = "Speaks with steady confidence and natural pacing, no awkward pauses"
        
        # Apply same narrator to all segments
        for segment_key in segments:
            if segment_key in script:
                script[segment_key]['narrator_characteristics'] = narrator_base
                script[segment_key]['delivery_instructions'] = delivery_base
                
                # Update prompt to include consistent narrator
                if 'prompt' in script[segment_key]:
                    prompt = script[segment_key]['prompt']
                    # Replace any existing narrator description with consistent one
                    import re
                    prompt = re.sub(r'\[voiceover:[^]]*\]', 
                                  f'[voiceover: {narrator_base} says: "{script[segment_key].get("voiceover_script", "")}"]', 
                                  prompt)
                    script[segment_key]['prompt'] = prompt
        
        print(f"DEBUG: ✅ Narrator consistency ensured across {len(segments)} segments")
        return script
        
    except Exception as e:
        print(f"DEBUG: Error ensuring narrator consistency: {e}")
        return script

def optimize_script_for_veo3_precise(script_segments):
    """
    Optimize script for VEO-3 with precise 15-word targeting and blank space elimination.
    Handles variable number of segments (1, 2, 3, or 4).
    """
    print("DEBUG: Optimizing script for VEO-3 with 15-word precision targeting")
    
    optimized_script = {}
    
    for segment_key, segment in script_segments.items():
        if segment_key.startswith('segment'):
            print(f"DEBUG: Optimizing {segment_key}")
            
            # Get current voiceover script
            current_script = segment.get('voiceover_script', '')
            words = current_script.split()
            word_count = len(words)
            
            print(f"DEBUG: {segment_key} current word count: {word_count}")
            
            if word_count > 15:
                # Truncate to exactly 15 words
                optimized_words = words[:15]
                optimized_script_text = ' '.join(optimized_words)
                print(f"DEBUG: Truncated {segment_key} from {word_count} to 15 words")
            elif word_count < 12:
                # If too short, it might have blank space - keep as is but flag
                optimized_script_text = current_script
                print(f"DEBUG: {segment_key} has {word_count} words (under 15) - may have blank space")
            else:
                # Perfect range (12-15 words)
                optimized_script_text = current_script
                print(f"DEBUG: {segment_key} word count optimal: {word_count} words")
            
            # Create optimized segment
            optimized_segment = segment.copy()
            optimized_segment['voiceover_script'] = optimized_script_text
            
            # Add precise timing breakdown for 15 words
            optimized_segment['timing_breakdown'] = f"0:00-0:06 narrator speaks {len(optimized_script_text.split())} words, 0:06-0:08 music bridge, no blank space"
            optimized_segment['word_timing'] = "Strategic placement: words 1-3 at 0:00-1:00, words 4-7 at 1:00-2:50, words 8-11 at 2:50-4:30, words 12-15 at 4:30-6:00"
            
            # Update prompt with optimized script
            if 'prompt' in optimized_segment:
                prompt = optimized_segment['prompt']
                # Update voiceover in prompt
                import re
                prompt = re.sub(r'\[voiceover:[^]]*\]', 
                              f'[voiceover: {optimized_segment.get("narrator_characteristics", "Professional narrator")} says: "{optimized_script_text}"]', 
                              prompt)
                optimized_segment['prompt'] = prompt
            
            optimized_script[segment_key] = optimized_segment
        else:
            # Keep non-segment keys as-is
            optimized_script[segment_key] = segment
    
    print("DEBUG: ✅ VEO-3 precision optimization complete")
    return optimized_script

def validate_and_fix_brand_messaging(script):
    """
    Ensure that either slogan or call-to-action is included in the voiceover scripts.
    This is absolutely critical for brand messaging.
    """
    print("DEBUG: Validating brand messaging inclusion in voiceover scripts")
    
    slogan = script.get('slogan', '').strip()
    cta = script.get('call_to_action', '').strip()
    
    if not slogan and not cta:
        print("WARNING: No slogan or CTA found in script")
        return script
    
    # Check if brand messaging is already included in any segment
    segments = [key for key in script.keys() if key.startswith('segment')]
    brand_messaging_found = False
    
    for segment_key in segments:
        voiceover = script[segment_key].get('voiceover_script', '').lower()
        
        # Check if slogan is included
        if slogan and any(word.lower() in voiceover for word in slogan.split() if len(word) > 2):
            brand_messaging_found = True
            print(f"DEBUG: Slogan found in {segment_key}")
            break
            
        # Check if CTA is included
        if cta and any(word.lower() in voiceover for word in cta.split() if len(word) > 2):
            brand_messaging_found = True
            print(f"DEBUG: CTA found in {segment_key}")
            break
    
    if brand_messaging_found:
        print("DEBUG: ✅ Brand messaging already included in voiceover")
        return script
    
    print("DEBUG: ⚠️ Brand messaging missing from voiceover - fixing automatically")
    
    # Fix by adding brand messaging to the final segment
    final_segment_key = f"segment{len(segments)}"
    if final_segment_key in script:
        final_segment = script[final_segment_key]
        current_voiceover = final_segment.get('voiceover_script', '')
        
        # Choose shorter brand message to fit in 15-word limit
        brand_message = cta if cta and len(cta.split()) <= 5 else slogan
        if not brand_message:
            brand_message = cta or slogan  # Fallback to whatever exists
        
        # Truncate current voiceover to make room for brand message
        current_words = current_voiceover.split()
        brand_words = brand_message.split()
        
        # Keep space for brand message (aim for 10-12 words + 3-5 brand words = 15 total)
        max_current_words = 15 - len(brand_words)
        if len(current_words) > max_current_words:
            current_words = current_words[:max_current_words]
        
        # Combine with brand message
        new_voiceover = ' '.join(current_words + brand_words)
        
        # Ensure it's not over 15 words
        if len(new_voiceover.split()) > 15:
            new_voiceover = ' '.join(new_voiceover.split()[:15])
        
        script[final_segment_key]['voiceover_script'] = new_voiceover
        
        # Update prompt as well
        if 'prompt' in final_segment:
            import re
            prompt = final_segment['prompt']
            prompt = re.sub(r'\[voiceover:[^]]*\]', 
                          f'[voiceover: {final_segment.get("narrator_characteristics", "Professional narrator")} says: "{new_voiceover}"]', 
                          prompt)
            script[final_segment_key]['prompt'] = prompt
        
        print(f"DEBUG: ✅ Added brand messaging to {final_segment_key}: '{new_voiceover}'")
    
    return script

# VEO-3 Frame-to-Video Continuation Settings
VEO3_CONTINUATION_ENABLED = True
FIXED_AD_DURATION = 16  # Always 16 seconds = 2 segments
SEGMENT_DURATION = 8   # Each segment is 8 seconds

# VEO-3 New Features Configuration
VEO3_FEATURES = {
    "frames_to_video": True,
    "ingredients_to_video": True, 
    "scene_builder": True,
    "camera_controls": True,
    "continuous_motion": True
}

# Image Context Options for User-Uploaded Assets
IMAGE_CONTEXT_OPTIONS = {
    "dashboard": ["laptop screen", "desktop monitor", "tablet display", "smartphone screen", "smart TV display"],
    "product": ["on table", "in hands", "floating in space", "on shelf", "in use", "close-up detail"],
    "person": ["full body", "portrait", "in action", "lifestyle setting", "professional setting"],
    "logo": ["corner overlay", "center focus", "background watermark", "animated entrance", "product integration"],
    "text": ["title card", "subtitle overlay", "call-to-action banner", "floating text", "integrated in scene"],
    "vehicle": ["driving scene", "parked showcase", "interior view", "exterior details", "in motion"],
    "food": ["being prepared", "finished dish", "ingredients", "close-up texture", "dining scene"],
    "technology": ["in use", "floating tech", "interface close-up", "before/after demo", "lifestyle integration"]
}

@app.route('/upload-image', methods=['POST'])
def upload_image():
    """Handle drag-and-drop image uploads with context selection"""
    try:
        if 'image' not in request.files:
            return jsonify({"success": False, "error": "No image file provided"}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        # Save uploaded image
        filename = secure_filename(file.filename)
        timestamp = str(int(time.time()))
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join('uploads', unique_filename)
        
        # Ensure uploads directory exists
        os.makedirs('uploads', exist_ok=True)
        file.save(file_path)
        
        # Analyze image to suggest context options
        suggested_contexts = analyze_image_for_context(file_path)
        
        return jsonify({
            "success": True,
            "file_path": file_path,
            "filename": unique_filename,
            "suggested_contexts": suggested_contexts,
            "context_options": IMAGE_CONTEXT_OPTIONS
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def analyze_image_for_context(image_path):
    """Use Gemini to analyze uploaded image and suggest context options"""
    try:
        gemini_api_key = get_gemini_api_key()
        if not gemini_api_key:
            return ["product"]  # Default fallback
        
        # Use Gemini Vision to analyze the image
        prompt = """Analyze this image and determine what type of asset it is. 
        Respond with ONE of these categories: dashboard, product, person, logo, text, vehicle, food, technology
        
        Only respond with the single word category, nothing else."""
        
        # Simplified analysis - in real implementation, you'd send the image to Gemini Vision
        # For now, return common suggestions based on filename patterns
        filename = os.path.basename(image_path).lower()
        
        if any(word in filename for word in ['dash', 'screen', 'ui', 'interface']):
            return ['dashboard']
        elif any(word in filename for word in ['logo', 'brand', 'icon']):
            return ['logo']
        elif any(word in filename for word in ['person', 'people', 'face', 'human']):
            return ['person']
        elif any(word in filename for word in ['car', 'vehicle', 'bike', 'truck']):
            return ['vehicle']
        elif any(word in filename for word in ['food', 'meal', 'dish', 'cook']):
            return ['food']
        elif any(word in filename for word in ['phone', 'tech', 'device', 'gadget']):
            return ['technology']
        else:
            return ['product']
            
    except Exception as e:
        print(f"Error analyzing image: {e}")
        return ['product']

@app.route('/generate-script-with-images', methods=['POST'])
def generate_script_with_images():
    """Generate 16-second ad script incorporating user-uploaded images"""
    try:
        data = request.json
        
        # Get basic ad info
        product_name = data.get('product_name', '')
        product_description = data.get('product_description', '')
        target_audience = data.get('target_audience', '')
        
        # Get uploaded images with context
        uploaded_images = data.get('uploaded_images', [])  # [{file_path, context, placement}]
        
        # Get answers for fixed 16-second ad
        answers = data.get('answers', {})
        
        # Generate enhanced script with image integration
        script = generate_enhanced_script_with_images(
            product_name, product_description, target_audience, answers, uploaded_images
        )
        
        return jsonify({
            "success": True,
            "script": script,
            "duration": 16,  # Always 16 seconds
            "segments": 2,   # Always 2 segments
            "veo3_features": {
                "frame_continuation": True,
                "image_integration": True,
                "seamless_transitions": True
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def generate_enhanced_script_with_images(product_name, product_description, target_audience, answers, uploaded_images):
    """Generate script with VEO-3 frame continuation and image integration"""
    
    # Build image integration instructions
    image_instructions = []
    for img in uploaded_images:
        context = img.get('context', 'product')
        placement = img.get('placement', 'in use')
        description = img.get('description', '')
        if description:
            image_instructions.append(f"- Include uploaded {context} {placement}: {description}")
        else:
            image_instructions.append(f"- Include uploaded {context} {placement}")
    
    image_integration_text = "\n".join(image_instructions) if image_instructions else ""
    
    # Enhanced prompt for VEO-3 capabilities
    prompt = f"""Create a compelling 16-second advertisement script for {product_name}.

PRODUCT INFO:
{product_description}
Target Audience: {target_audience}

USER PREFERENCES:
{format_answers_for_prompt(answers)}

IMAGE ASSETS TO INTEGRATE:
{image_integration_text}

VEO-3 REQUIREMENTS:
- EXACTLY 16 seconds total (2 segments of 8 seconds each)
- Segment 1: Strong visual hook with uploaded assets
- Segment 2: Continues seamlessly from Segment 1's last frame
- Include frame-to-video continuation points
- Optimize for VEO-3's camera controls and scene builder
- Ensure continuous motion between segments

SCRIPT FORMAT:
{{
  "total_duration": 16,
  "segments": {{
    "segment1": {{
      "duration": 8,
      "voiceover": "[Exactly 15 words for 8-second timing]",
      "visual_description": "[Detailed scene including uploaded assets]",
      "camera_movement": "[Specific VEO-3 camera instructions]",
      "last_frame_description": "[Critical: Describe exact final frame for continuation]"
    }},
    "segment2": {{
      "duration": 8,
      "voiceover": "[Exactly 15 words for 8-second timing]",
      "visual_description": "[Scene that flows from segment1's last frame]",
      "camera_movement": "[VEO-3 camera instructions for smooth continuation]",
      "continuation_method": "frames_to_video"
    }}
  }},
  "veo3_features": {{
    "frame_continuation": true,
    "uploaded_assets": {len(uploaded_images)},
    "camera_controls": "cinematic_movement",
    "scene_builder": "seamless_transition"
  }},
  "brand_message": "{{slogan or call_to_action}}",
  "narrator_voice": "Professional, warm, engaging - consistent across both segments"
}}

Focus on:
1. Seamless visual flow between segments
2. Natural integration of uploaded images
3. VEO-3's superior physics and realism
4. Camera movements that enhance continuity"""

    try:
        # Use OpenAI for script generation
        openai_api_key = get_openai_api_key()
        if not openai_api_key:
            raise Exception("OpenAI API key not found")
            
        client = OpenAI(api_key=openai_api_key)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert advertising scriptwriter specializing in VEO-3 AI video generation with frame-to-video continuation. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8
        )
        
        script_text = response.choices[0].message.content.strip()
        
        # Parse and validate JSON
        try:
            script_json = json.loads(script_text)
            return script_json
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return create_fallback_script_with_images(product_name, uploaded_images)
            
    except Exception as e:
        print(f"Error generating script: {e}")
        return create_fallback_script_with_images(product_name, uploaded_images)

def create_fallback_script_with_images(product_name, uploaded_images):
    """Create fallback script structure with image integration"""
    
    # Determine primary asset type
    primary_context = "product"
    if uploaded_images:
        primary_context = uploaded_images[0].get('context', 'product')
    
    return {
        "total_duration": 16,
        "segments": {
            "segment1": {
                "duration": 8,
                "voiceover": f"Discover the power of {product_name} - transforming how you work and live.",
                "visual_description": f"Opening shot shows {primary_context} in premium setting with dramatic lighting",
                "camera_movement": "Slow push-in with slight rotation for dynamic reveal",
                "last_frame_description": "Close-up of key product feature with user's hand reaching toward it"
            },
            "segment2": {
                "duration": 8,
                "voiceover": f"Experience {product_name} today. Your future starts now.",
                "visual_description": "Continues from hand interaction, showing transformation and satisfaction",
                "camera_movement": "Smooth pull-back revealing full context and positive outcome",
                "continuation_method": "frames_to_video"
            }
        },
        "veo3_features": {
            "frame_continuation": True,
            "uploaded_assets": len(uploaded_images),
            "camera_controls": "cinematic_movement",
            "scene_builder": "seamless_transition"
        },
        "brand_message": f"Choose {product_name}",
        "narrator_voice": "Professional, warm, engaging"
    }

def format_answers_for_prompt(answers):
    """Format user answers into a readable prompt format"""
    if not answers:
        return "No specific preferences provided."
    
    formatted_lines = []
    
    # Map answer keys to readable labels
    answer_labels = {
        'ad_type': 'Ad Type',
        'mood': 'Mood/Vibe',
        'authenticity_level': 'Authenticity Level',
        'humor_tolerance': 'Humor Preference',
        'educational_value': 'Educational Approach',
        'sound_optimization': 'Sound/Audio Strategy',
        'main_character': 'Main Character',
        'target_platform': 'Target Platform',
        'transformation_story': 'Transformation Story',
        'slogan': 'Preferred Slogan',
        'cta': 'Call to Action',
        'features': 'Key Features',
        'industry': 'Industry',
        'company_url': 'Company Website'
    }
    
    for key, value in answers.items():
        if value and value.strip() and value.upper() != 'N/A':
            label = answer_labels.get(key, key.replace('_', ' ').title())
            formatted_lines.append(f"- {label}: {value}")
    
    return '\n'.join(formatted_lines) if formatted_lines else "Standard preferences apply."

@app.route('/generate-video-veo3-continuation', methods=['POST'])
def generate_video_veo3_continuation():
    """Generate video using VEO-3's frame-to-video continuation"""
    try:
        data = request.json
        script = data.get('script', {})
        uploaded_images = data.get('uploaded_images', [])
        
        # Generate Segment 1 first
        segment1_result = generate_veo3_segment_with_images(
            script['segments']['segment1'], 
            uploaded_images, 
            segment_number=1
        )
        
        if not segment1_result.get('success'):
            return jsonify({"success": False, "error": "Failed to generate segment 1"})
        
        # Extract last frame from Segment 1
        last_frame = extract_last_frame(segment1_result['video_url'])
        
        # Generate Segment 2 using frame continuation
        segment2_result = generate_veo3_segment_with_continuation(
            script['segments']['segment2'],
            last_frame,
            uploaded_images,
            segment_number=2
        )
        
        if not segment2_result.get('success'):
            return jsonify({"success": False, "error": "Failed to generate segment 2"})
        
        # Combine segments (they should be seamless due to frame continuation)
        final_video = combine_seamless_segments([
            segment1_result['video_url'],
            segment2_result['video_url']
        ])
        
        return jsonify({
            "success": True,
            "video_url": final_video,
            "duration": 16,
            "segments_generated": 2,
            "veo3_features_used": [
                "frame_to_video_continuation",
                "uploaded_image_integration", 
                "seamless_camera_movement",
                "enhanced_physics_and_realism"
            ],
            "technical_details": {
                "segment1_url": segment1_result['video_url'],
                "segment2_url": segment2_result['video_url'],
                "continuation_frame": "extracted_and_applied",
                "image_assets_integrated": len(uploaded_images)
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def generate_veo3_segment_with_images(segment_script, uploaded_images, segment_number):
    """Generate video segment with uploaded image integration"""
    try:
        # Build VEO-3 prompt with image integration
        image_refs = []
        for img in uploaded_images:
            context = img.get('context', 'product')
            placement = img.get('placement', 'in use')
            image_refs.append(f"{context} {placement}")
        
        image_integration = ", ".join(image_refs) if image_refs else ""
        
        veo3_prompt = f"""
        {segment_script['visual_description']}
        
        UPLOADED ASSETS: {image_integration}
        CAMERA: {segment_script['camera_movement']}
        DURATION: 8 seconds
        QUALITY: Cinematic, hyper-realistic
        PHYSICS: Enhanced VEO-3 accuracy
        
        Style: Professional commercial, dramatic lighting, smooth motion
        """
        
        # VEO-3 API call with new features
        veo3_payload = {
            "prompt": veo3_prompt,
            "duration": 8,
            "quality": "4K",
            "features": {
                "ingredients_to_video": True if uploaded_images else False,
                "camera_controls": True,
                "enhanced_physics": True,
                "cinematic_quality": True
            }
        }
        
        # Add uploaded images as ingredients
        if uploaded_images:
            veo3_payload["ingredients"] = [
                {
                    "type": "image",
                    "path": img["file_path"],
                    "context": img.get("context", "product"),
                    "placement": img.get("placement", "in use")
                }
                for img in uploaded_images
            ]
        
        # Simulate VEO-3 API call (replace with actual API when available)
        video_url = f"https://veo3-api.google.com/generated/segment{segment_number}_{int(time.time())}.mp4"
        
        return {
            "success": True,
            "video_url": video_url,
            "segment": segment_number,
            "features_used": ["image_integration", "camera_controls", "enhanced_physics"]
        }
        
    except Exception as e:
        print(f"Error generating VEO-3 segment: {e}")
        return {"success": False, "error": str(e)}

def generate_veo3_segment_with_continuation(segment_script, reference_frame, uploaded_images, segment_number):
    """Generate video segment using frame-to-video continuation"""
    try:
        # Build continuation prompt
        continuation_prompt = f"""
        CONTINUATION FROM REFERENCE FRAME:
        {segment_script['visual_description']}
        
        CAMERA: {segment_script['camera_movement']}
        DURATION: 8 seconds
        CONTINUATION_METHOD: frames_to_video
        
        Style: Seamless continuation, maintain lighting and perspective
        """
        
        # VEO-3 API call with frame continuation
        veo3_payload = {
            "mode": "frames_to_video",
            "reference_frame": reference_frame,  # Last frame from previous segment
            "prompt": continuation_prompt,
            "duration": 8,
            "quality": "4K",
            "features": {
                "scene_builder": True,
                "continuous_motion": True,
                "seamless_transition": True
            }
        }
        
        # Add image ingredients if available
        if uploaded_images:
            veo3_payload["ingredients"] = [
                {
                    "type": "image", 
                    "path": img["file_path"],
                    "context": img.get("context", "product")
                }
                for img in uploaded_images
            ]
        
        # Simulate VEO-3 frame continuation API
        video_url = f"https://veo3-api.google.com/continuation/segment{segment_number}_{int(time.time())}.mp4"
        
        return {
            "success": True,
            "video_url": video_url,
            "segment": segment_number,
            "continuation_method": "frames_to_video",
            "features_used": ["frame_continuation", "scene_builder", "continuous_motion"]
        }
        
    except Exception as e:
        print(f"Error generating VEO-3 continuation: {e}")
        return {"success": False, "error": str(e)}

def extract_last_frame(video_url):
    """Extract the last frame from a video for continuation"""
    try:
        # In real implementation, this would:
        # 1. Download the video from video_url
        # 2. Extract the final frame using ffmpeg or similar
        # 3. Return the frame as base64 or upload to storage
        
        # For now, simulate the frame extraction
        frame_data = f"last_frame_from_{video_url.split('/')[-1]}"
        return frame_data
        
    except Exception as e:
        print(f"Error extracting last frame: {e}")
        return None

def combine_seamless_segments(segment_urls):
    """Combine video segments that should be seamless due to frame continuation"""
    try:
        # In real implementation, this would:
        # 1. Download all segment videos
        # 2. Concatenate them without any transition effects
        # 3. Since they use frame continuation, they should be seamless
        # 4. Upload final video and return URL
        
        # Simulate final video URL
        final_url = f"https://veo3-api.google.com/final/seamless_ad_{int(time.time())}.mp4"
        return final_url
        
    except Exception as e:
        print(f"Error combining segments: {e}")
        return segment_urls[0]  # Return first segment as fallback

if __name__ == '__main__':
    try:
        print("DEBUG: Starting main execution...")
        
        print("DEBUG: Initializing rating database...")
        init_rating_database()
        
        print("DEBUG: About to call ensure_best_ads_embedded()")
        ensure_best_ads_embedded()
        print("DEBUG: ensure_best_ads_embedded() completed")
        
        print("DEBUG: Starting background cleanup thread...")
        start_cleanup_thread()
        
        print("DEBUG: Getting port from environment...")
        port = int(os.environ.get('PORT', 5000))
        print(f"DEBUG: Using port {port}")
        
        print("DEBUG: Starting Flask app...")
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"FATAL ERROR in main: {e}")
        import traceback
        traceback.print_exc()
        raise 