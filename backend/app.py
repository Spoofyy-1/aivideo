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

print("DEBUG: All imports completed successfully")

# Load environment variables
load_dotenv()
print("DEBUG: Environment variables loaded")

app = Flask(__name__, static_folder='static')
CORS(app)
print("DEBUG: Flask app created successfully")

GEMINI_API_KEY = "AIzaSyABk6wdtiL7JHhpVsTM-criOeDyzr29lwk"
print("DEBUG: Gemini API key set")

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

def generate_ad_script(company_info, user_answers, best_ads=None):
    """
    Generate a cinematic, story-driven, and entertaining ad script with two 8-second segments, plus a creative slogan and a call-to-action line.
    Updated for 2025 best practices: authenticity, 3-second hooks, humor comeback, educational content.
    Now includes AI-powered feedback insights for continuous improvement.
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

CONTENT PATTERNS TO FOLLOW:
- AVOID: {', '.join(improvement_insights.get('content_patterns', {}).get('avoid', []))}
- EMPHASIZE: {', '.join(improvement_insights.get('content_patterns', {}).get('emphasize', []))}

PROMPT IMPROVEMENTS FROM USER FEEDBACK:
{chr(10).join([f"- {improvement}" for improvement in improvement_insights.get('prompt_improvements', [])])}

AD TYPE INSIGHTS: {improvement_insights.get('ad_type_insights', {}).get('insight', 'No specific insights available')}
INDUSTRY INSIGHTS: {improvement_insights.get('industry_insights', {}).get('insight', 'No specific insights available')}

*** CRITICAL: Apply these user-validated improvements to create better ads ***
"""
    else:
        print(f"DEBUG: No feedback insights available for {ad_type}/{industry}")
        
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

    ad_type = user_answers.get('ad_type', '').lower()
    
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

    ad_type_instructions = ""
    if ad_type == "unhinged":
        ad_type_instructions = (
            "ENTHUSIASTIC PRODUCT DEMONSTRATION: Create a high-energy, engaging commercial focused on showcasing specific product features and benefits. "
            "Philosophy: 'Excited characters genuinely sharing their positive product experiences' - build brand recall through authentic enthusiasm and clear product education. "
            "CORE APPROACH: FEATURE-FOCUSED STORYTELLING - Every scene highlights a specific product capability or benefit. "
            "KEY ELEMENTS: "
            "1) ENTHUSIASTIC TESTIMONIALS: Characters sharing genuine excitement about specific product features "
            "2) RAPID PRODUCT BENEFITS: Quick demonstration of different product capabilities and real-world applications "
            "3) 'THIS WORKS BECAUSE...' APPROACH: Always explain the practical reasons why the product delivers results "
            "4) SOLUTION-ORIENTED: Show specific problems being solved by specific product features "
            "5) EDUCATIONAL FOCUS: Every character teaches viewers about a specific product feature or benefit "
            "POSITIVE TESTIMONIAL EXAMPLES: "
            "- Happy customer explaining: '[PRODUCT] has this amazing [FEATURE] that helps me [SPECIFIC BENEFIT]!' "
            "- Satisfied user sharing: 'I love how [PRODUCT] solves [SPECIFIC PROBLEM] with [SPECIFIC FEATURE]!' "
            "- Enthusiastic reviewer: '[PRODUCT] includes [FEATURE] which means I can [SPECIFIC ACTION/RESULT]!' "
            "- Grateful customer: 'Before [PRODUCT], I struggled with [PROBLEM]. Now with [FEATURE], everything is easier!' "
            "- Product advocate: '[PRODUCT]'s [FEATURE] is perfect for people who want [SPECIFIC BENEFIT]!' "
            "- Delighted user: 'The [SPECIFIC FEATURE] in [PRODUCT] saves me so much [TIME/MONEY/EFFORT]!' "
            "- Excited fan: '[PRODUCT] is special because it has [UNIQUE FEATURE] that provides [SPECIFIC BENEFIT]!' "
            "- Happy demonstrator: 'Watch how [PRODUCT]'s [FEATURE] works in [SPECIFIC SCENARIO] - it's incredible!' "
            "- Satisfied customer: 'I've tried many options, but [PRODUCT]'s [FEATURE] actually delivers [SPECIFIC RESULT]!' "
            "POSITIVE BENEFIT CATEGORIES: "
            "- Efficiency: 'With [PRODUCT]'s [FEATURE], I complete [TASK] much faster!' "
            "- Value: '[PRODUCT]'s [FEATURE] helps me save money on [EXPENSE]!' "
            "- Simplicity: '[PRODUCT]'s [FEATURE] makes [COMPLEX TASK] really easy!' "
            "- Results: '[PRODUCT]'s [FEATURE] gives me better [OUTCOME] than anything else!' "
            "- Innovation: '[PRODUCT] offers [UNIQUE CAPABILITY] through its [SPECIAL FEATURE]!' "
            "- Problem-Solving: '[PRODUCT]'s [FEATURE] finally addressed my [PAIN POINT]!' "
            "TONE: Positive, enthusiastic product advocacy with specific proof points. Make viewers think 'I want to experience these benefits!' "
            "Focus on genuine customer satisfaction and feature-specific enthusiasm. "
            "Every character should be authentically excited about specific product capabilities and real benefits. "
            "VISUAL STYLE: Clean product demonstrations with positive energy and clear educational content. "
            "Show the product working effectively, highlight features visually, and make benefits obvious through happy customer experiences."
        )
    elif ad_type == "informative":
        ad_type_instructions = (
            "Make this ad clear, concise, and focused on delivering key information. Use a trustworthy tone, clear visuals, and step-by-step explanations. "
            "IMPORTANT: Lead with education first (8 seconds) before introducing the product - this builds trust and reduces skepticism."
        )
    elif ad_type == "emotional":
        ad_type_instructions = (
            "Make this ad emotionally powerful. Use storytelling, music, and visuals to evoke strong feelings—whether it's inspiration, joy, nostalgia, or empathy."
        )
    elif ad_type == "cinematic":
        ad_type_instructions = (
            "Make this ad feel like a movie trailer: cinematic, visually stunning, and story-driven. Use dramatic lighting, dynamic camera angles, and a clear story arc."
        )
    elif ad_type == "funny":
        ad_type_instructions = (
            "PRIORITY: Make this ad hilarious and memorable. Use clever jokes, visual gags, comedic timing, and unexpected punchlines. "
            "Research shows humor is making a major comeback in 2025 - 25% of highest-spending ads use humor. "
            "Focus on humor that connects to the product benefit, not just random comedy."
        )
    elif ad_type == "heartwarming":
        ad_type_instructions = (
            "Make this ad touching and uplifting. Use real people, authentic moments, and emotional storytelling to create a feel-good, heartwarming experience."
        )
    elif ad_type == "aspirational":
        ad_type_instructions = (
            "Make this ad inspiring and visionary. Show how the product helps people achieve their dreams, reach new heights, or become their best selves."
        )
    elif ad_type == "testimonial":
        ad_type_instructions = (
            "AUTHENTICITY FOCUS: Make this ad feel like a genuine testimonial. Use authentic voices, real stories, and social proof to build trust and credibility. "
            "In 2025, consumers crave authentic human stories over AI-generated content. Feature real people with genuine experiences."
        )
    elif ad_type == "product demo":
        ad_type_instructions = (
            "Make this ad a clear, engaging product demonstration. Show the product in action, highlight key features, and make it easy to understand the benefits."
        )
    elif ad_type == "viral/meme":
        ad_type_instructions = (
            "Make this ad designed for MAXIMUM VIRALITY using internet culture and memes. Use trending formats like: "
            "TikTok dances, viral challenges, popular meme templates (Drake pointing, distracted boyfriend, woman yelling at cat), "
            "internet slang and Gen Z language, trending audio clips, popular social media personalities, "
            "viral video formats (POV videos, 'Tell me you... without telling me', 'This you?'), "
            "internet phenomena, social media trends, popular hashtags, influencer culture, "
            "AVOID mythical creatures or cryptids - focus on REAL internet culture, memes, and viral content. "
            "Make it feel like something that would naturally go viral on TikTok, Twitter, or Instagram. "
            "Use current internet humor, relatable situations, and shareable moments that people actually post online."
        )
    elif ad_type == "story-driven":
        ad_type_instructions = (
            "Make this ad a mini-story. Use a clear narrative arc, character development, and a satisfying resolution."
        )
    elif ad_type == "minimalist":
        ad_type_instructions = (
            "Make this ad visually simple and focused. Use minimal visuals, clean design, and a single powerful message."
        )
    elif ad_type == "high-energy":
        ad_type_instructions = (
            "Make this ad fast-paced, energetic, and exciting. Use quick cuts, upbeat music, and dynamic visuals to keep the viewer engaged."
        )
    elif ad_type == "social proof":
        ad_type_instructions = (
            "TRUST-BUILDING FOCUS: Make this ad focus on social proof. Show real people, testimonials, and evidence of popularity or trust. "
            "84% of consumers are influenced by user-generated content - emphasize authentic customer experiences."
        )
    elif ad_type == "pop culture reference":
        ad_type_instructions = (
            "Make this ad packed with pop culture references, memes, and trending topics. Make it feel current, relevant, and shareable."
        )
    elif ad_type == "educational-first":
        ad_type_instructions = (
            "2025 TREND: Lead with education and value before selling. Build trust by teaching something useful first. "
            "Introduce the product later (after 40+ seconds) - this addresses consumer skepticism and builds authority. "
            "Make the viewer feel smarter for watching."
        )
    elif ad_type == "founder-story":
        ad_type_instructions = (
            "2025 AUTHENTICITY TREND: Feature the founder's personal story, passion, and behind-the-scenes journey. "
            "Show the human side of the business. Use first-person POV and authentic, relatable moments. "
            "Make it feel like a personal conversation, not a corporate pitch."
        )
    elif ad_type == "nostalgia-driven":
        ad_type_instructions = (
            "2025 TREND: Use nostalgia marketing to create emotional connections. Reference past eras, childhood memories, "
            "or 'simpler times' that resonate with your audience. Blend retro aesthetics with modern sensibilities. "
            "Make viewers feel warm and connected to shared cultural memories."
        )
    elif ad_type == "brain-rot/escapism":
        ad_type_instructions = (
            "2025 TREND: Create satisfying, low-cognitive-load content that provides mental relief from information overload. "
            "Use ASMR-like elements, satisfying visuals, slow movements, calming colors. "
            "Make it a palate cleanser from the chaos of social media - give viewers a mental break."
        )
    elif ad_type == "micro-moment":
        ad_type_instructions = (
            "2025 TREND: Capture specific micro-moments and pain points. Focus on very specific, relatable situations "
            "that make viewers say 'that's exactly what happens to me!' Ultra-targeted, highly specific scenarios."
        )
    elif ad_type == "platform-native":
        ad_type_instructions = (
            "2025 CRITICAL: Make this ad feel like organic social content, not an ad. "
            "Use smartphone-shot aesthetics, natural lighting, casual framing. "
            "Make it look like something a friend would post, not a corporation."
        )
    elif ad_type == "normal":
        ad_type_instructions = (
            "CLASSIC PROBLEM-SOLUTION ADVERTISING: Create a traditional but effective ad that introduces a relatable problem in a unique way, then presents the product as the perfect solution. "
            "Structure: Problem Introduction → Problem Amplification → Solution Reveal → Product Benefits → Call to Action "
            "CORE ELEMENTS: "
            "1) UNIQUE PROBLEM INTRODUCTION: Start with a relatable but creatively presented problem that your target audience faces "
            "2) EMOTIONAL CONNECTION: Make viewers think 'That's exactly my problem!' through specific, recognizable scenarios "
            "3) SMOOTH TRANSITION: Bridge from problem to solution naturally without feeling forced or sales-y "
            "4) CLEAR SOLUTION PRESENTATION: Show how the product specifically solves the identified problem "
            "5) TANGIBLE BENEFITS: Highlight concrete improvements the product provides "
            "PROBLEM PRESENTATION TECHNIQUES: "
            "- Start with a frustrating but relatable scenario that your audience knows well "
            "- Use visual metaphors or creative analogies to represent the problem "
            "- Show the emotional or practical impact of not having a solution "
            "- Present multiple angles of the same core problem to increase relatability "
            "- Use before/after scenarios to emphasize the problem's effects "
            "SOLUTION REVEAL STRATEGIES: "
            "- Natural transition: 'But what if there was a way...' or 'Imagine if you could...' "
            "- Direct introduction: 'Meet [PRODUCT] - the solution you've been waiting for' "
            "- Demonstration approach: Show the product solving the exact problem just presented "
            "- Transformation narrative: 'Here's how [PRODUCT] changes everything...' "
            "BENEFIT COMMUNICATION: "
            "- Connect each product feature directly to solving the specific problem shown "
            "- Use concrete examples: 'Instead of [PROBLEM], you get [SPECIFIC BENEFIT]' "
            "- Show real-world applications that relate to the initial problem scenario "
            "- Emphasize the contrast between the problem state and solution state "
            "TONE: Professional yet approachable, empathetic to the problem, confident about the solution "
            "Make viewers feel understood and hopeful - 'Finally, someone gets my problem AND has the answer!' "
            "VISUAL STYLE: Clean, professional, focused on clear storytelling that guides viewers from problem to solution "
            "Use visual contrast between problem scenes (darker, more chaotic) and solution scenes (brighter, more organized)."
        )
    # ... add more types as needed ...

    avoid_topics = extract_avoid_topics(company_info)
    avoid_str = ", ".join(avoid_topics) if avoid_topics else "None"

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

    # Add best ads inspiration with enhanced scene descriptions
    best_ads_str = ""
    if best_ads:
        best_ads_str = "Here are some of the best, most creative, and viral ad scripts and creative principles in history to use as inspiration (be bold, surprising, and memorable!):\n"
        for ad in best_ads:
            scene_desc = ""
            if 'scene_descriptions' in ad:
                scene_desc = f"\nScene 1: {ad['scene_descriptions']['segment1']['visual']} (Mood: {ad['scene_descriptions']['segment1']['mood']}, Camera: {ad['scene_descriptions']['segment1']['camera']})\n"
                scene_desc += f"Scene 2: {ad['scene_descriptions']['segment2']['visual']} (Mood: {ad['scene_descriptions']['segment2']['mood']}, Camera: {ad['scene_descriptions']['segment2']['camera']})"
            best_ads_str += f"- {ad['title']}: {ad['script']} (Principle: {ad['principle']}, Slogan: {ad.get('slogan', '')}, Call to Action: {ad.get('call_to_action', '')}){scene_desc}\n"

    # VEO-3 OPTIMIZATION FRAMEWORK - Based on Latest Research & Best Practices
    veo3_framework = """
    *** ADVANCED VEO-3 OPTIMIZATION FRAMEWORK ***
    CRITICAL: Apply these cutting-edge Veo-3 techniques for cinematic excellence:

    🎬 VEO-3 CORE PRINCIPLES:
    1. "PROMPT AS BLUEPRINT" - Your prompt is a detailed architectural plan for Veo-3
    2. CINEMATIC LANGUAGE - Veo-3 understands professional film terminology
    3. NATIVE AUDIO GENERATION - Dialogue, SFX, and music from single prompt
    4. PHYSICS SIMULATION - Realistic motion and interactions
    5. SEQUENCE UNDERSTANDING - "This then that" emotional/gesture chains
    6. CREATIVE DIVERSITY - Avoid repetitive scenarios, be unpredictable and varied

    🎭 EMOTION & GESTURE CHAINING (Veo-3 Specialty):
    - Use "this then that" sequences for complex emotional arcs
    - Chain emotions: "Starts calm, then bursts into laughter, suddenly stops with terror"
    - Chain gestures: "Spreads arms wide, brings hands to chest, points outward"
    - Combine gesture + emotion: "Turns head like hearing something, pauses, whips back fast, eyes dart"
    - Define start/stop points: "Begins composed, flash of violence, returns to calm"

    🎥 CINEMATIC CONTROL OPTIMIZATION:
    - Camera Motion Keywords: static shot, dolly in/out, pan left/right, tracking shot, crane shot, zoom in/out
    - Composition Control: close-up, medium shot, wide shot, over-the-shoulder, point-of-view (POV)
    - Lens Effects: shallow depth of field, rack focus, soft focus, macro lens, wide-angle lens
    - Motivated Movement: Camera moves serve narrative purpose, not arbitrary

    🎙️ AUDIO MASTERY (Veo-3's Breakthrough Feature):
    - Dialogue Format: "Character says: 'exact words'" (use colon, not quotes)
    - Emotional Delivery: "He confessed with trembling voice" / "She announced triumphantly"
    - Sound Effects: Be specific - "rhythmic clatter of train tracks" not "noise"
    - Music Description: "melancholic piano melody" / "driving electronic bassline"
    - Avoid Subtitles: Add "(no subtitles)" and use colon format
    - Background Audio: Specify explicitly to avoid unwanted studio audience
    - CONTINUOUS AUDIO: Ensure dialogue, music, or SFX fills every second - NO SILENCE
    - OVERLAPPING AUDIO: Layer dialogue with background music and ambient sounds
    - AUDIO TRANSITIONS: Smooth audio bridges between dialogue segments
    - PACING CONTROL: Use "rapid-fire dialogue" or "conversational pace" specifications
    - ELIMINATE DEAD AIR: Pack multiple lines of dialogue into each 8-second segment
    - RAPID-FIRE DELIVERY: Characters speak quickly without pauses between sentences
    - CONSTANT TALKING: Someone is always speaking - no awkward silence or blank space
    - PRODUCT INTEGRATION: Weave company/product mentions into every line of dialogue

    🎨 VISUAL ENHANCEMENT:
    - Style References: film noir, anime, documentary, Wes Anderson style, claymation
    - Lighting Control: chiaroscuro, golden hour, neon glow, candlelit
    - Color Palette: desaturated cool blues, warm orange tones, monochromatic
    - Physics Integration: Fabric movement, water flow, realistic interactions

    📝 HIERARCHICAL PROMPT STRUCTURE:
    1. Primary Elements: Main characters, core actions, setting
    2. Secondary Elements: Environmental details, background elements  
    3. Technical Specifications: Camera angles, lighting, audio
    4. Temporal Indicators: Scene duration, emotional progression

    ⚡ VEO-3 SPECIFIC OPTIMIZATIONS:
    - Character Consistency: Use identical detailed descriptions across segments
    - Sequence Planning: 8-second segments with emotional/narrative progression
    - Negative Prompts: Describe desired state, avoid "no" or "don't" commands
    - Iterative Refinement: Analyze output, refine specific elements progressively
    - Motivated Direction: Every technical choice serves story/emotion

    🔥 ADVANCED TECHNIQUES:
    - Selfie-Style: "A selfie video of..." with visible arm for authenticity
    - Dialogue Timing: Perfect for 8-second segments, avoid rushed/gibberish speech
    - Character Emotion: Link physical movements to emotional states
    - Scene Transitions: Plan continuity between segments for longer narratives
    - Director Mindset: Think like filmmaker directing AI crew

    🎙️ CONTINUOUS DIALOGUE EXAMPLES - NO DEAD SPACE:
    - RAPID-FIRE: "Character says: 'This changed everything!' then immediately: 'I couldn't believe it!' followed by: 'Now I use it daily!' then: 'Everyone should try this!' ending with: 'It's absolutely incredible!'"
    - OVERLAPPING: "Narrator says: 'Meet Sarah' while Sarah says: 'I love this product' while background voice adds: 'Amazing results' with upbeat music playing"
    - CONVERSATIONAL: "Person A says: 'What's that?' Person B responds: 'It's amazing!' Person A: 'Tell me more!' Person B: 'It changed my life!' Person A: 'I need this now!'"
    - LAYERED AUDIO: "Excited customer says: 'This is incredible!' over energetic background music while crowd cheers and someone else shouts: 'I agree completely!'"
    - NO PAUSES: "Spokesperson says: 'Transform your life today' immediately followed by 'Don't wait another second' then 'Call now' then 'You won't regret it' with no silence between"
    - PRODUCT INTEGRATION: "Every line mentions the company: 'With [COMPANY] I saved money' then 'On [COMPANY] everything is easy' then '[COMPANY] changed everything' then 'I love [COMPANY] so much'"

    💫 CREATIVE VARIETY MANDATE:
    - AVOID REPETITIVE SCENARIOS: Don't default to the same creatures, settings, or situations
    - MIX GENRES: Combine different themes (sci-fi + comedy, horror + romance, etc.)
    - UNEXPECTED COMBINATIONS: Pair mundane products with epic scenarios
    - CULTURAL DIVERSITY: Use varied cultural references, not just Western tropes
    - TEMPORAL VARIETY: Mix modern, historical, futuristic, and timeless elements
    - SCALE VARIETY: From intimate personal moments to epic cosmic events

    💫 PROMPT THEORY APPROACH:
    - Macro Prompt: Establish atmosphere, lighting, cinematic style globally
    - Character Specificity: Novel-level detail - "woman with tired green eyes, scar above eyebrow"
    - Dialogue Integration: Intersperse speech with facial expressions and actions
    - Cinematic Language: Use professional film terminology for camera guidance
    - Emotional Journey: Clear understanding of character's emotional arc
    """

    # 2025 Best Practices Section with 16-Second Video Optimization + Veo-3 Framework
    practices_2025 = f"""
    *** 2025 AD CREATION BEST PRACTICES - OPTIMIZED FOR 16-SECOND FORMAT + VEO-3 ***
    CRITICAL: Apply these proven 2025 trends and Veo-3 optimization techniques:

    {veo3_framework}

    1. 3-SECOND HOOK RULE (CRITICAL FOR 16s): The first 3 seconds MUST grab attention immediately. Use:
       - Immediately recognizable visuals (familiar objects/situations)
       - Strong opening problem that resonates instantly
       - Visual that speaks for itself without explanation
       - Veo-3 Emotion Chain: Start with one emotion, transition to another in 3 seconds

    2. ABCD FRAMEWORK FOR 16-SECOND ADS + VEO-3:
       A - ATTENTION: Hook with Veo-3 gesture/emotion chains from second 1
       B - BRANDING: Early integration (5s) using Veo-3 audio generation
       C - CONNECTION: Veo-3 dialogue with emotional delivery + gesture linking
       D - DIRECTION: Clear CTA with Veo-3 motivated camera movement

    3. 16-SECOND VEO-3 STRUCTURE OPTIMIZATION:
       - Seconds 1-3: HOOK using Veo-3 emotion chaining techniques
       - Seconds 4-8: SETUP with cinematic camera movement keywords 
       - Seconds 9-13: TRANSFORMATION using gesture + emotion combinations
       - Seconds 14-16: CTA with motivated dolly/zoom for emphasis

    4. VEO-3 AUDIO INTEGRATION FOR ADS:
       - Dialogue Format: "Spokesperson says: 'Transform your business today'"
       - Emotional Delivery: "Excited customer exclaims" / "Expert confidently states"
       - Brand Audio: Specific SFX for product sounds, branded music cues
       - Avoid Subtitle Issues: Use "(no subtitles)" religiously in ad context

    5. VEO-3 CINEMATIC AD TECHNIQUES:
       - Product Reveals: Use "rack focus" from product to user reaction
       - Testimonials: "Over-the-shoulder" shots for authenticity
       - Action Sequences: "Tracking shot" following product in use
       - Emotional Moments: "Close-up" with "shallow depth of field"

    6. AUTHENTICITY WITH VEO-3 PHYSICS:
       - Real interactions between characters and products
       - Physics-accurate product demonstrations
       - Natural fabric/hair movement in testimonials
       - Believable environmental interactions

    7. VEO-3 CHARACTER CONSISTENCY FOR BRAND:
       - Identical spokesperson descriptions across segments
       - Consistent brand character personalities
       - Visual continuity for multi-part campaigns
       - Character reference sheets for ongoing use
    """

    prompt = f"""{ad_type_instructions}

{feedback_improvements}

{practices_2025}

{best_ads_str}

Based on this company information (from their website):
{company_info}

{product_info_str}

And the following creative direction from the user:
{creative_notes_str}

When writing the ad, avoid these topics, themes, or words: {avoid_str}

*** VEO-3 OPTIMIZED 16-SECOND AD CREATION FRAMEWORK ***
Create a 2025-optimized, ultra-short 16-second ad script using the complete Veo-3 framework above:

🎬 VEO-3 16-SECOND STRUCTURE:
Segment 1 (8 seconds): ATTENTION + BRANDING with Veo-3 emotion chains
- Seconds 1-3: HOOK using Veo-3 gesture/emotion chaining techniques + IMMEDIATE RAPID-FIRE DIALOGUE
- Seconds 4-5: BRAND INTRODUCTION with native audio generation + CONTINUOUS PRODUCT MENTIONS
- Seconds 6-8: SETUP with motivated camera movement and character development + NON-STOP TALKING

Segment 2 (8 seconds): CONNECTION + DIRECTION with Veo-3 cinematic mastery
- Seconds 9-11: TRANSFORMATION using gesture + emotion combinations + RAPID DIALOGUE WITH PRODUCT INTEGRATION
- Seconds 12-13: EMOTIONAL PAYOFF with physics-accurate interactions + MUSIC + VOICE + COMPANY MENTIONS
- Seconds 14-16: CLEAR CTA with motivated camera movement and audio reinforcement + CONSTANT PRODUCT TALK

🎭 VEO-3 OPTIMIZATION REQUIREMENTS:
- Apply emotion & gesture chaining: "Character starts [emotion], then [emotion], finally [emotion]"
- Use professional cinematic language: dolly in/out, tracking shot, close-up, over-the-shoulder
- Implement native audio generation: "Character says: 'exact words'" with (no subtitles)
- Include physics-accurate interactions and realistic movement
- Follow hierarchical structure: Primary → Secondary → Technical → Temporal
- Motivated directorial choices: Every camera move and technique serves the story

📝 ENHANCED OUTPUT REQUIREMENTS:
For each segment, provide these Veo-3 optimized elements:
- "scene_description": Detailed Veo-3 visual using cinematic language (NO logos)
- "prompt": Complete Veo-3 prompt with emotion chains, camera work, and [voiceover: ...] (NO logos)
- "voiceover_script": 8-second RAPID-FIRE dialogue using proper Veo-3 format with emotional delivery
- "mood": Emotional atmosphere with specific lighting/color references
- "camera": Professional camera movement with narrative motivation
- "veo3_optimization": Explanation of which Veo-3 techniques were applied
- "emotion_chain": Specific emotion/gesture sequence for this segment
- "audio_design": Detailed audio elements (dialogue, SFX, music) with Veo-3 formatting
- "hook_strength": Rate 1-10 with explanation (segment1 only)
- "abcd_elements": ABCD framework integration for this segment

🚀 CINEMATIC EXCELLENCE GUIDELINES:
- EVERY SECOND COUNTS: No wasted moments, every frame advances story
- MOBILE-FIRST: Bright, high-contrast visuals, tight framing for small screens
- AUDIO-VISUAL SYNC: Voice-over and visuals work together using Veo-3 native audio
- IMMEDIATE IMMERSION: Drop viewers into story from second 1 using emotion chains
- BRAND EARLY & OFTEN: Introduce within 5 seconds, maintain presence with audio
- HUMAN CONNECTION: Show real people experiencing product with physics accuracy
- CLEAR DIRECTION: Final 3 seconds have unmistakable CTA with motivated camera work
- RAPID-FIRE DIALOGUE: Pack 4-6 lines of dialogue into each 8-second segment
- CONSTANT PRODUCT MENTIONS: Company/product name mentioned 3-4 times per segment
- ZERO DEAD AIR: Continuous talking, music, or sound effects - NO SILENCE EVER
- OVERLAPPING AUDIO: Multiple voices, background music, and ambient sounds simultaneously

*** CRITICAL DIALOGUE REQUIREMENTS - ELIMINATE ALL DEAD SPACE ***
- PACK DIALOGUE: Each 8-second segment must have 4-6 rapid-fire lines
- PRODUCT INTEGRATION: Company name mentioned multiple times per segment
- NO PAUSES: Characters speak immediately after each other with no gaps
- OVERLAPPING VOICES: Multiple people can talk simultaneously
- BACKGROUND CHATTER: Add crowd voices, ambient conversations
- MUSIC + VOICE: Background music plays while people talk
- SOUND EFFECTS: Layer in relevant sounds while dialogue continues
- RAPID DELIVERY: Characters speak quickly and enthusiastically
- COMPANY OBSESSION: Every character is obsessed with mentioning the company

EXAMPLE RAPID-FIRE VOICEOVER STRUCTURE:
"Person says: 'I love [COMPANY]!' then immediately: 'It changed my life!' while background voice adds: '[COMPANY] is amazing!' then main person continues: 'Everyone needs [COMPANY]!' as music builds and crowd cheers: 'We love [COMPANY] too!'"

Format your response as valid JSON:
{{
    "segment1": {{
        "scene_description": "...",
        "prompt": "... [voiceover: ...]",
        "voiceover_script": "...",
        "mood": "...",
        "camera": "...",
        "veo3_optimization": "...",
        "emotion_chain": "...",
        "audio_design": "...",
        "hook_strength": {{"rating": X, "explanation": "..."}},
        "abcd_elements": "A: ... B: ... C: ... D: ..."
    }},
    "segment2": {{
        "scene_description": "...",
        "prompt": "... [voiceover: ...]",
        "voiceover_script": "...",
        "mood": "...",
        "camera": "...",
        "veo3_optimization": "...",
        "emotion_chain": "...",
        "audio_design": "...",
        "abcd_elements": "A: ... B: ... C: ... D: ..."
    }},
    "slogan": "...",
    "call_to_action": "...",
    "ad_strategy_2025": "Brief explanation of 2025 best practices applied",
    "veo3_framework_application": "Detailed explanation of Veo-3 optimization techniques used",
    "sixteen_second_optimization": "How this ad maximizes impact in the 16-second format",
    "feedback_integration": "How user feedback insights were applied to improve this ad"
}}

Do not include any text before or after the JSON. Only return the JSON object."""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000
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
        
        # If this was an "unhinged" request, automatically fallback to "high-energy" 
        if ad_type == "unhinged":
            print("Falling back from 'unhinged' to 'high-energy' ad type due to content policy")
            user_answers_fallback = user_answers.copy()
            user_answers_fallback['ad_type'] = 'high-energy'
            try:
                return generate_ad_script(company_info, user_answers_fallback, best_ads=best_ads)
            except Exception as fallback_error:
                raise ValueError(f"Both original and fallback ad generation failed. Original error: OpenAI refused request. Fallback error: {str(fallback_error)}")
        else:
            raise ValueError(f"OpenAI refused the request, likely due to content policy. Response: {repr(content)}")

    # Try to extract JSON from the response
    try:
        if not content:
            raise ValueError("OpenAI returned an empty response.")
        return json.loads(content)
    except Exception as e:
        import re
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception as e2:
                print("Failed to parse extracted JSON:", e2)
        print("Failed to parse OpenAI response as JSON:", e)
        raise ValueError("Failed to parse OpenAI response as JSON. Raw response: " + repr(content))

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
        
        # Load clips and inspect their properties
        clips = []
        for i, path in enumerate(video_paths):
            clip = mp.VideoFileClip(path)
            print(f"DEBUG: Clip {i+1} - Duration: {clip.duration:.2f}s, FPS: {clip.fps}, Audio: {clip.audio is not None}")
            clips.append(clip)
        
        # Ensure all clips have audio
        processed_clips = []
        for i, clip in enumerate(clips):
            if clip.audio is None:
                print(f"WARNING: Clip {i+1} has no audio, adding silent audio")
                # Add silent audio to match video duration
                from moviepy.audio.AudioClip import AudioClip
                silent_audio = AudioClip(lambda t: [0, 0], duration=clip.duration)
                clip = clip.set_audio(silent_audio)
            processed_clips.append(clip)
        
        # Apply audio cross-fading and normalization
        final_clips = []
        for i, clip in enumerate(processed_clips):
            # Normalize audio levels to prevent volume spikes
            if clip.audio is not None:
                # Apply audio normalization (prevent clipping and ensure consistent volume)
                clip = clip.audio_normalize()
            
            # Add slight fade-in/out to prevent audio pops
            if i == 0:
                # First clip: fade in at start, fade out at end for smooth transition
                clip = clip.audio_fadein(0.05).audio_fadeout(0.05)
            elif i == len(processed_clips) - 1:
                # Last clip: fade in at start, no fade out at end to prevent cutoff
                clip = clip.audio_fadein(0.05)
            else:
                # Middle clips: fade in and out for smooth transitions
                clip = clip.audio_fadein(0.05).audio_fadeout(0.05)
            
            final_clips.append(clip)
        
        print("DEBUG: Concatenating clips with improved audio handling")
        
        # Concatenate with method that handles audio transitions better
        final_clip = mp.concatenate_videoclips(final_clips, method="compose")
        
        # Ensure final clip doesn't cut off audio by adding tiny padding
        final_duration = final_clip.duration
        if final_clip.audio is not None:
            # Add 0.1 second padding to prevent audio cutoff
            final_clip = final_clip.subclip(0, final_duration + 0.1)
        
        print(f"DEBUG: Final clip duration: {final_clip.duration:.2f}s")
        
        # Write with optimized settings for better audio quality
        final_clip.write_videofile(
            output_path, 
            codec='libx264', 
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',  # Use high-quality temp audio
            remove_temp=True,  # Clean up temp files
            audio_bitrate="192k",  # Higher audio bitrate for better quality
            ffmpeg_params=['-avoid_negative_ts', 'make_zero']  # Fix audio sync issues
        )
        
        print("DEBUG: Video combination completed successfully")
        
        # Cleanup
        for clip in final_clips:
            clip.close()
        for clip in processed_clips:
            if clip not in final_clips:  # Avoid double-closing
                clip.close()
        for path in video_paths:
            if os.path.exists(path):
                os.remove(path)
        
        # Clean up temp directory if it exists and is empty
        temp_dir = os.path.dirname(video_paths[0])
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
        
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
    *** ADVANCED VEO-3 OPTIMIZATION FRAMEWORK ***
    CRITICAL: Apply these cutting-edge Veo-3 techniques for cinematic excellence:

    🎬 VEO-3 CORE PRINCIPLES:
    1. "PROMPT AS BLUEPRINT" - Your prompt is a detailed architectural plan for Veo-3
    2. CINEMATIC LANGUAGE - Veo-3 understands professional film terminology
    3. NATIVE AUDIO GENERATION - Dialogue, SFX, and music from single prompt
    4. PHYSICS SIMULATION - Realistic motion and interactions
    5. SEQUENCE UNDERSTANDING - "This then that" emotional/gesture chains
    6. CREATIVE DIVERSITY - Avoid repetitive scenarios, be unpredictable and varied

    🎭 EMOTION & GESTURE CHAINING (Veo-3 Specialty):
    - Use "this then that" sequences for complex emotional arcs
    - Chain emotions: "Starts calm, then bursts into laughter, suddenly stops with terror"
    - Chain gestures: "Spreads arms wide, brings hands to chest, points outward"
    - Combine gesture + emotion: "Turns head like hearing something, pauses, whips back fast, eyes dart"
    - Define start/stop points: "Begins composed, flash of violence, returns to calm"

    🎥 CINEMATIC CONTROL OPTIMIZATION:
    - Camera Motion Keywords: static shot, dolly in/out, pan left/right, tracking shot, crane shot, zoom in/out
    - Composition Control: close-up, medium shot, wide shot, over-the-shoulder, point-of-view (POV)
    - Lens Effects: shallow depth of field, rack focus, soft focus, macro lens, wide-angle lens
    - Motivated Movement: Camera moves serve narrative purpose, not arbitrary

    🎙️ AUDIO MASTERY (Veo-3's Breakthrough Feature):
    - Dialogue Format: "Character says: 'exact words'" (use colon, not quotes)
    - Emotional Delivery: "He confessed with trembling voice" / "She announced triumphantly"
    - Sound Effects: Be specific - "rhythmic clatter of train tracks" not "noise"
    - Music Description: "melancholic piano melody" / "driving electronic bassline"
    - Avoid Subtitles: Add "(no subtitles)" and use colon format
    - Background Audio: Specify explicitly to avoid unwanted studio audience
    - CONTINUOUS AUDIO: Ensure dialogue, music, or SFX fills every second - NO SILENCE
    - OVERLAPPING AUDIO: Layer dialogue with background music and ambient sounds
    - AUDIO TRANSITIONS: Smooth audio bridges between dialogue segments
    - PACING CONTROL: Use "rapid-fire dialogue" or "conversational pace" specifications
    - ELIMINATE DEAD AIR: Pack multiple lines of dialogue into each 8-second segment
    - RAPID-FIRE DELIVERY: Characters speak quickly without pauses between sentences
    - CONSTANT TALKING: Someone is always speaking - no awkward silence or blank space
    - PRODUCT INTEGRATION: Weave company/product mentions into every line of dialogue

    🎨 VISUAL ENHANCEMENT:
    - Style References: film noir, anime, documentary, Wes Anderson style, claymation
    - Lighting Control: chiaroscuro, golden hour, neon glow, candlelit
    - Color Palette: desaturated cool blues, warm orange tones, monochromatic
    - Physics Integration: Fabric movement, water flow, realistic interactions

    📝 HIERARCHICAL PROMPT STRUCTURE:
    1. Primary Elements: Main characters, core actions, setting
    2. Secondary Elements: Environmental details, background elements  
    3. Technical Specifications: Camera angles, lighting, audio
    4. Temporal Indicators: Scene duration, emotional progression

    ⚡ VEO-3 SPECIFIC OPTIMIZATIONS:
    - Character Consistency: Use identical detailed descriptions across segments
    - Sequence Planning: 8-second segments with emotional/narrative progression
    - Negative Prompts: Describe desired state, avoid "no" or "don't" commands
    - Iterative Refinement: Analyze output, refine specific elements progressively
    - Motivated Direction: Every technical choice serves story/emotion

    🔥 ADVANCED TECHNIQUES:
    - Selfie-Style: "A selfie video of..." with visible arm for authenticity
    - Dialogue Timing: Perfect for 8-second segments, avoid rushed/gibberish speech
    - Character Emotion: Link physical movements to emotional states
    - Scene Transitions: Plan continuity between segments for longer narratives
    - Director Mindset: Think like filmmaker directing AI crew

    🎙️ CONTINUOUS DIALOGUE EXAMPLES - NO DEAD SPACE:
    - RAPID-FIRE: "Character says: 'This changed everything!' then immediately: 'I couldn't believe it!' followed by: 'Now I use it daily!' then: 'Everyone should try this!' ending with: 'It's absolutely incredible!'"
    - OVERLAPPING: "Narrator says: 'Meet Sarah' while Sarah says: 'I love this product' while background voice adds: 'Amazing results' with upbeat music playing"
    - CONVERSATIONAL: "Person A says: 'What's that?' Person B responds: 'It's amazing!' Person A: 'Tell me more!' Person B: 'It changed my life!' Person A: 'I need this now!'"
    - LAYERED AUDIO: "Excited customer says: 'This is incredible!' over energetic background music while crowd cheers and someone else shouts: 'I agree completely!'"
    - NO PAUSES: "Spokesperson says: 'Transform your life today' immediately followed by 'Don't wait another second' then 'Call now' then 'You won't regret it' with no silence between"
    - PRODUCT INTEGRATION: "Every line mentions the company: 'With [COMPANY] I saved money' then 'On [COMPANY] everything is easy' then '[COMPANY] changed everything' then 'I love [COMPANY] so much'"

    💫 CREATIVE VARIETY MANDATE:
    - AVOID REPETITIVE SCENARIOS: Don't default to the same creatures, settings, or situations
    - MIX GENRES: Combine different themes (sci-fi + comedy, horror + romance, etc.)
    - UNEXPECTED COMBINATIONS: Pair mundane products with epic scenarios
    - CULTURAL DIVERSITY: Use varied cultural references, not just Western tropes
    - TEMPORAL VARIETY: Mix modern, historical, futuristic, and timeless elements
    - SCALE VARIETY: From intimate personal moments to epic cosmic events

    💫 PROMPT THEORY APPROACH:
    - Macro Prompt: Establish atmosphere, lighting, cinematic style globally
    - Character Specificity: Novel-level detail - "woman with tired green eyes, scar above eyebrow"
    - Dialogue Integration: Intersperse speech with facial expressions and actions
    - Cinematic Language: Use professional film terminology for camera guidance
    - Emotional Journey: Clear understanding of character's emotional arc
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
    
    for seg in ['segment1', 'segment2']:
        prompt = f"Can you improve this current script to be better fit for Veo3 generation for a 16-second Ad? Make it more engaging, cinematic, and effective using 2025 best practices and the ABCD framework (Attention, Branding, Connection, Direction).{improvement_guidelines_2025}{best_ads_str}\n\nCurrent segment script:\n{json.dumps(gpt_script[seg], indent=2)}\n\nImprove this script while maintaining the JSON format. Focus on:\n1. 16-SECOND OPTIMIZATION: Making every second count with no wasted moments\n2. ABCD FRAMEWORK: Ensuring proper Attention (hook), Branding (early presence), Connection (human elements), Direction (clear CTA)\n3. MOBILE-FIRST: Bright, high-contrast visuals with tight framing for small screens\n4. IMMEDIATE IMMERSION: Drop viewers into story from second 1\n5. ULTRA-SHORT STORYTELLING: Making it more visually compelling and better suited for 16-second video generation\n6. Applying 2025 trends: stronger hooks, authenticity, humor (if appropriate), emotional engagement\n7. Ensuring the visual and voiceover work together for maximum impact in limited time\n8. Making it feel more native to social platforms rather than traditional advertising\n\nFor segment1: Focus on ATTENTION + BRANDING (hook in 1-3s, brand intro 4-5s, setup 6-8s)\nFor segment2: Focus on CONNECTION + DIRECTION (transformation 9-11s, emotion 12-13s, CTA 14-16s)"
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-06-05:generateContent?key=" + GEMINI_API_KEY
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
            """Generate video with session-specific temporary files."""
            for retry in range(3):
                try:
                    video_path = generate_video_segment_with_session(ad_script[segment]['prompt'], i, session_id)
                    # Process the segment to improve audio quality
                    processed_path = process_video_segment(video_path, i)
                    return processed_path
                except Exception as e:
                    if "flagged as sensitive" in str(e).lower() or "E005" in str(e):
                        print(f"Sensitive content detected for {segment}, regenerating script (retry {retry+1})...")
                        # Regenerate script and try again
                        ad_script_new = generate_ad_script(company_info, user_answers, best_ads=best_ads)
                        ad_script[segment] = ad_script_new[segment]
                        continue
                    else:
                        raise
            raise Exception(f"Failed to generate {segment} after 3 retries due to sensitive content.")

        print("DEBUG: Starting parallel video generation with audio processing")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future1 = executor.submit(get_video_with_session, 'segment1', 1, session_id)
            future2 = executor.submit(get_video_with_session, 'segment2', 2, session_id)
            video_path1 = future1.result()
            video_path2 = future2.result()

        video_paths = [video_path1, video_path2]
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