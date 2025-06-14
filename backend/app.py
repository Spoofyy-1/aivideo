import os
import json
import requests
import tempfile
import shutil
import concurrent.futures
import numpy as np
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

def get_openai_client():
    """Get a fresh OpenAI client instance to avoid environment interference."""
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

def research_company(url):
    """Research company using ChatGPT and web scraping."""
    try:
        client = get_openai_client()
        if client is None:
            return "Error: OpenAI client not available. Please check API key configuration."
            
        # Scrape website content
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = soup.get_text()[:4000]  # Limit content length
        
        # Use ChatGPT to analyze company
        prompt = f"""Analyze this company based on their website content and provide key information:
        Website content: {text_content}
        
        Please provide:
        1. Company's main product/service
        2. Target audience
        3. Unique selling points
        4. Brand voice and style
        5. Key benefits for customers
        6. List up to 5 main products or services (as a JSON array of strings, or an empty array if not found)
        7. List any topics, themes, or words that should be avoided in marketing or advertising for this company (as a JSON array of strings, or an empty array if not found)
        """
        
        # Use modern OpenAI API syntax
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Error researching company: {str(e)}"

def extract_products_services(research_text):
    """Extract a list of products/services from the research_company output using OpenAI."""
    client = get_openai_client()
    if client is None:
        return []
        
    prompt = f"""Extract up to 5 main products or services from the following company research. Return only a JSON array of strings. If none are found, return an empty array.\n\n{research_text}"""
    
    response = client.chat.completions.create(
        model="gpt-4o",
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
        model="gpt-4o",
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
    else:
        return 'A broad audience interested in this industry.'

def generate_ad_script(company_info, user_answers, best_ads=None):
    """
    Generate a cinematic, story-driven, and entertaining ad script with two 8-second segments, plus a creative slogan and a call-to-action line.
    Updated for 2025 best practices: authenticity, 3-second hooks, humor comeback, educational content.
    """
    client = get_openai_client()
    if client is None:
        raise Exception("OpenAI client not available. Please check API key configuration.")
        
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
    industry = user_answers.get('industry', '')
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
            "Make this ad wild, unpredictable, and attention-grabbing. Use surreal humor, unexpected twists, and viral-worthy moments. "
            "Break conventions, use meme energy, and surprise the viewer at every turn. Think of the most unhinged, meme-worthy ads you've seen online."
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
            "Make this ad designed for virality. Use meme formats, trending topics, pop culture references, and shareable moments to maximize engagement."
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
    # ... add more types as needed ...

    avoid_topics = extract_avoid_topics(company_info)
    avoid_str = ", ".join(avoid_topics) if avoid_topics else "None"

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

{practices_2025}

{best_ads_str}

Based on this company information (from their website):
{company_info}

And the following creative direction from the user:
{creative_notes_str}

When writing the ad, avoid these topics, themes, or words: {avoid_str}

*** VEO-3 OPTIMIZED 16-SECOND AD CREATION FRAMEWORK ***
Create a 2025-optimized, ultra-short 16-second ad script using the complete Veo-3 framework above:

🎬 VEO-3 16-SECOND STRUCTURE:
Segment 1 (8 seconds): ATTENTION + BRANDING with Veo-3 emotion chains
- Seconds 1-3: HOOK using Veo-3 gesture/emotion chaining techniques
- Seconds 4-5: BRAND INTRODUCTION with native audio generation
- Seconds 6-8: SETUP with motivated camera movement and character development

Segment 2 (8 seconds): CONNECTION + DIRECTION with Veo-3 cinematic mastery
- Seconds 9-11: TRANSFORMATION using gesture + emotion combinations
- Seconds 12-13: EMOTIONAL PAYOFF with physics-accurate interactions
- Seconds 14-16: CLEAR CTA with motivated camera movement and audio reinforcement

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
- "voiceover_script": 8-second dialogue using proper Veo-3 format with emotional delivery
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
    "sixteen_second_optimization": "How this ad maximizes impact in the 16-second format"
}}

Do not include any text before or after the JSON. Only return the JSON object."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.choices[0].message.content.strip()
    print("OpenAI raw response:", repr(content))  # Debug print

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

def combine_videos(video_paths, output_path):
    """Combine video segments into final ad."""
    try:
        clips = [mp.VideoFileClip(path) for path in video_paths]
        final_clip = mp.concatenate_videoclips(clips)
        final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac')
        
        # Cleanup
        for clip in clips:
            clip.close()
        for path in video_paths:
            os.remove(path)
        os.rmdir(os.path.dirname(video_paths[0]))
        
        return output_path
    except Exception as e:
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
            f.write(company_info)
        return output_path
    except Exception as e:
        raise Exception(f"Error generating company report: {str(e)}")

def improve_script_with_gemini(company_info, user_answers, gpt_script, best_ads=None):
    """Send each segment to Gemini separately to improve for Veo3 with 2025 best practices."""
    import copy
    improved_script = copy.deepcopy(gpt_script)
    
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

    3. VEO-3 CINEMATIC ENHANCEMENT:
       - Camera Motivation: Every camera move serves the story - "dolly in as tension builds"
       - Composition Precision: Use professional terms - "over-the-shoulder shot" / "extreme close-up"
       - Lens Effects: Add focus techniques - "rack focus from product to satisfied user"
       - Lighting Specificity: "chiaroscuro lighting" / "golden hour warmth" / "neon glow"

    4. 16-SECOND ABCD OPTIMIZATION:
       - A: Strengthen 3-second hook with Veo-3 emotion chaining
       - B: Earlier brand integration using Veo-3 audio generation
       - C: Deeper connection through Veo-3 dialogue + gesture linking
       - D: Clearer direction with motivated camera movement

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
    try:
        print("DEBUG: Generate route called")
        print("Received request to /generate")
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
        
        # Generate company report
        output_dir = 'static/generated'
        os.makedirs(output_dir, exist_ok=True)
        
        # Add timestamp to make files unique and prevent overwriting
        import time
        timestamp = str(int(time.time()))
        company_name = slugify(company_url.split('//')[-1].split('/')[0])
        unique_name = f"{company_name}_{timestamp}"
        
        report_path = os.path.join(output_dir, f'{unique_name}_report.txt')
        generate_company_report(company_info, report_path)
        report_url = f'/download/report/{os.path.basename(report_path)}'
        print(f"Returning report_url: {report_url}")
        
        # Retrieve top best ads for inspiration
        user_text = f"Company info: {company_info}\nUser wants: {json.dumps(user_answers)}"
        best_ads = get_top_best_ads(user_text)
        
        ai_model = user_answers.get('ai_model', 'Best (Recommended)').lower()
        if ai_model == 'gemini':
            # Use Gemini only for both segments
            def gemini_generate_segment(segment_prompt):
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-06-05:generateContent?key=" + GEMINI_API_KEY
                headers = {"Content-Type": "application/json"}
                data = {"contents": [{"parts": [{"text": segment_prompt}]}]}
                response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                import re
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                else:
                    raise Exception("Gemini did not return valid JSON. Raw response: " + repr(text))
            # Build prompts for each segment
            ad_type = user_answers.get('ad_type', '').lower()
            
            # Normalize ad_type to handle frontend formatting (Gemini path)
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
                    "Make this ad wild, unpredictable, and attention-grabbing. Use surreal humor, unexpected twists, and viral-worthy moments. "
                    "Break conventions, use meme energy, and surprise the viewer at every turn. Think of the most unhinged, meme-worthy ads you've seen online."
                )
            elif ad_type == "informative":
                ad_type_instructions = (
                    "Make this ad clear, concise, and focused on delivering key information. Use a trustworthy tone, clear visuals, and step-by-step explanations."
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
                    "Make this ad designed for virality. Use meme formats, trending topics, pop culture references, and shareable moments to maximize engagement."
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
            # For Gemini, we want to generate each segment separately
            gemini_script = {}
            
            # Build best ads inspiration string for Gemini with Veo-3 optimization
            best_ads_str = ""
            if best_ads:
                best_ads_str = f"Here are some of the best, most creative, and viral ad scripts and creative principles in history to use as inspiration (be bold, surprising, and memorable!):\n{veo3_framework}\n\n"
                for ad in best_ads:
                    scene_desc = ""
                    if 'scene_descriptions' in ad:
                        scene_desc = f"\nScene 1: {ad['scene_descriptions']['segment1']['visual']} (Mood: {ad['scene_descriptions']['segment1']['mood']}, Camera: {ad['scene_descriptions']['segment1']['camera']})\n"
                        scene_desc += f"Scene 2: {ad['scene_descriptions']['segment2']['visual']} (Mood: {ad['scene_descriptions']['segment2']['mood']}, Camera: {ad['scene_descriptions']['segment2']['camera']})"
                    best_ads_str += f"- {ad['title']}: {ad['script']} (Principle: {ad['principle']}, Slogan: {ad.get('slogan', '')}, Call to Action: {ad.get('call_to_action', '')}){scene_desc}\n"
            
            for seg in ['segment1', 'segment2']:
                segment_prompt = f"""{ad_type_instructions}

{veo3_framework}

Based on this company information (from their website):
{company_info}

And the following creative direction from the user:
{user_answers}

*** VEO-3 OPTIMIZED 16-SECOND AD GENERATION ***
Apply the complete Veo-3 framework above for cinematic excellence:

🎬 SEGMENT REQUIREMENTS ({seg}):
- Use Veo-3 emotion & gesture chaining techniques
- Apply professional cinematic language (camera movements, compositions)
- Integrate native audio generation (dialogue with colons, specific SFX, music)
- Implement physics-accurate interactions and realistic movement
- Follow hierarchical prompt structure (Primary → Secondary → Technical → Temporal)

🎭 FOR THIS SEGMENT, PROVIDE:
- 'scene_description': Detailed Veo-3 visual description using cinematic language (NO logos)
- 'prompt': Complete Veo-3 prompt with emotion chains, camera work, and audio using [voiceover: ...] format (NO logos)
- 'voiceover_script': Compelling 8-second dialogue using proper Veo-3 format
- 'mood': Emotional atmosphere with specific lighting/color references
- 'camera': Professional camera movement with narrative motivation
- 'veo3_optimization': Explanation of which Veo-3 techniques were applied
- 'emotion_chain': Specific emotion/gesture sequence for this segment
- 'audio_design': Detailed audio elements (dialogue, SFX, music) with Veo-3 formatting

{best_ads_str}

CRITICAL: Apply Veo-3's "this then that" sequencing, motivated camera work, professional audio formatting with colons, and physics-accurate interactions. Make every technical choice serve the story and emotional arc.

Format your response as valid JSON. Only return the JSON object."""
                gemini_script[seg] = gemini_generate_segment(segment_prompt)
            # Slogan and CTA: generate with Gemini as well
            slogan_cta_prompt = f"Based on the above, generate a creative, memorable slogan and a bold, actionable call-to-action for this ad. Format as JSON: {{'slogan': '...', 'call_to_action': '...'}}. Only return the JSON object."
            slogan_cta = gemini_generate_segment(slogan_cta_prompt)
            gemini_script['slogan'] = slogan_cta['slogan']
            gemini_script['call_to_action'] = slogan_cta['call_to_action']
            ad_script = gemini_script
        else:
            # Default: Use GPT-4 + Gemini improvement flow
            ad_script = generate_ad_script(company_info, user_answers, best_ads=best_ads)
            print("Ad script (GPT):", ad_script)
            try:
                ad_script = improve_script_with_gemini(company_info, user_answers, ad_script, best_ads=best_ads)
                print("Ad script (Gemini improved):", ad_script)
            except Exception as e:
                print("Gemini improvement failed, using GPT script. Error:", e)
        
        # Generate video segments in parallel, with retry on sensitive content
        def get_video(segment, i):
            for retry in range(3):
                try:
                    return generate_video_segment(ad_script[segment]['prompt'], i)
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

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future1 = executor.submit(get_video, 'segment1', 1)
            future2 = executor.submit(get_video, 'segment2', 2)
            video_path1 = future1.result()
            video_path2 = future2.result()

        video_paths = [video_path1, video_path2]
        
        # Combine videos
        output_path = os.path.join(output_dir, f'{unique_name}_ad.mp4')
        final_video_path = combine_videos(video_paths, output_path)
        print("Final video path:", final_video_path)
        # Check if file exists
        if not os.path.exists(final_video_path):
            print(f"ERROR: Video file does not exist at {final_video_path}")
            return jsonify({'error': 'Video file was not created.'}), 500
        else:
            print(f"Video file exists at {final_video_path}")
        video_url = f'/download/video/{os.path.basename(final_video_path)}'
        print(f"Returning video_url: {video_url}")
        return jsonify({
            'status': 'success',
            'video_url': video_url,
            'report_url': report_url,
            'script': ad_script
        })
        
    except Exception as e:
        print(f"ERROR in generate route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

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

@app.route('/download/video/<filename>')
def download_video(filename):
    try:
        print(f"DEBUG: Download video route called for {filename}")
        return send_from_directory('static/generated', filename, as_attachment=True)
    except Exception as e:
        print(f"ERROR in download_video route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/download/report/<filename>')
def download_report(filename):
    return send_from_directory('static/generated', filename, as_attachment=True)

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
                    model="gpt-4o-mini",
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
                model="gpt-4o-mini",
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

if __name__ == '__main__':
    try:
        print("DEBUG: Starting main execution...")
        print("DEBUG: About to call ensure_best_ads_embedded()")
        ensure_best_ads_embedded()
        print("DEBUG: ensure_best_ads_embedded() completed")
        
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