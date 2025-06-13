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
            import os
            proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
            original_values = {}
            for var in proxy_vars:
                if var in os.environ:
                    original_values[var] = os.environ[var]
                    client_info['steps'].append(f'Found proxy var {var}: {os.environ[var][:20]}...')
                    del os.environ[var]
            
            client_info['steps'].append('Cleared proxy environment variables')
            
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
    """
    client = get_openai_client()
    if client is None:
        raise Exception("OpenAI client not available. Please check API key configuration.")
        
    creative_notes = []
    if user_answers.get('product'):
        creative_notes.append(f"Main product/service to promote: {user_answers['product']}")
    if user_answers.get('mood'):
        creative_notes.append(f"Desired mood/vibe: {user_answers['mood']}")
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
            "Make this ad hilarious and memorable. Use clever jokes, visual gags, comedic timing, and unexpected punchlines to make the viewer laugh."
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
            "Make this ad feel like a genuine testimonial. Use authentic voices, real stories, and social proof to build trust and credibility."
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
            "Make this ad focus on social proof. Show real people, testimonials, and evidence of popularity or trust."
        )
    elif ad_type == "pop culture reference":
        ad_type_instructions = (
            "Make this ad packed with pop culture references, memes, and trending topics. Make it feel current, relevant, and shareable."
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

    prompt = f"""{ad_type_instructions}\n{best_ads_str}\nBased on this company information (from their website):\n{company_info}\n\nAnd the following creative direction from the user:\n{creative_notes_str}\n\nWhen writing the ad, avoid these topics, themes, or words: {avoid_str}\n\nCreate a cinematic, story-driven, and entertaining 16-second ad script divided into two 8-second scenes (setup and transformation), inspired by the best practices and styles seen in top-performing ads and tutorials such as:\n- https://www.youtube.com/watch?v=5Pc0hzKkOvE (ad creation tutorial)\n- https://www.youtube.com/watch?v=09n73rbMyiw (ad compilation)\n- https://www.youtube.com/watch?v=-QMftwmyW-A (AI-generated ad example)\n\nGuidelines:\n- Scene 1: Start with a dramatic hook, viral moment, or relatable problem.\n- Scene 2: Show the transformation, solution, or benefit in a visually dynamic, unexpected, or emotionally powerful way. You must include an outro at the end of the second scene that shows the company's name and logo.\n- Make the ad visually entertaining, cinematic, and story-driven.\n- Use camera movement, mood, and cinematic language.\n- Each scene should be visually distinct but flow together as a story.\n- Focus on benefits and transformation, not just features.\n- Avoid on-screen text.\n- Try to add a creative element to the ad, such as a pop culture reference, meme, twist ending, or a viral-worthy moment. Use humor, surprise, or emotion if appropriate.\n- Try to make the ad feel like a movie trailer, with a story and a hook.\n- IMPORTANT: A creative, memorable slogan is mandatory. If the user hasn't provided one, create a short, bold, catchy, and viral-worthy slogan for the company or product.\n- IMPORTANT: A bold, memorable, and actionable call-to-action (CTA) is also mandatory. If the user hasn't provided one, create a strong call-to-action line that drives viewers to take action immediately.\n\nIMPORTANT: For each segment, provide:\n- "scene_description": a cinematic visual description for Veo-3 (do NOT mention or describe any logos)\n- "prompt": a concise Veo-3 prompt that includes a simple voiceover instruction, e.g., [voiceover: ...] (do NOT mention or describe any logos)\n- "voiceover_script": a short, compelling line to be spoken as a voiceover\n- "mood": the emotional tone and atmosphere of the scene\n- "camera": specific camera movements and techniques to use\n\nFormat your response as valid JSON:\n{{\n    "segment1": {{\n        "scene_description": "...",\n        "prompt": "... [voiceover: ...]",\n        "voiceover_script": "...",\n        "mood": "...",\n        "camera": "..."\n    }},\n    "segment2": {{\n        "scene_description": "...",\n        "prompt": "... [voiceover: ...]",\n        "voiceover_script": "...",\n        "mood": "...",\n        "camera": "..."\n    }},\n    "slogan": "...",\n    "call_to_action": "..."\n}}\nDo not include any text before or after the JSON. Only return the JSON object.\n"""

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

def improve_script_with_gemini(company_info, user_answers, gpt_script):
    """Send each segment to Gemini separately to improve for Veo3."""
    import copy
    improved_script = copy.deepcopy(gpt_script)
    for seg in ['segment1', 'segment2']:
        prompt = f"Can you improve this current script to be better fit for Veo3 generation for an Ad?\n\nSegment script:\n{json.dumps(gpt_script[seg], indent=2)}"
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
        company_name = slugify(company_url.split('//')[-1].split('/')[0])
        report_path = os.path.join(output_dir, f'{company_name}_report.txt')
        generate_company_report(company_info, report_path)
        report_url = f'/static/generated/{os.path.basename(report_path)}'
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
                    "Make this ad hilarious and memorable. Use clever jokes, visual gags, comedic timing, and unexpected punchlines to make the viewer laugh."
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
                    "Make this ad feel like a genuine testimonial. Use authentic voices, real stories, and social proof to build trust and credibility."
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
                    "Make this ad focus on social proof. Show real people, testimonials, and evidence of popularity or trust."
                )
            elif ad_type == "pop culture reference":
                ad_type_instructions = (
                    "Make this ad packed with pop culture references, memes, and trending topics. Make it feel current, relevant, and shareable."
                )
            # For brevity, you can refactor ad_type_instructions logic into a function and reuse here
            # For now, just call generate_ad_script to get the prompt structure, but don't use GPT-4
            prompt_template = generate_ad_script(company_info, user_answers, best_ads=best_ads)
            # For Gemini, we want to generate each segment separately
            gemini_script = {}
            for seg in ['segment1', 'segment2']:
                segment_prompt = f"{ad_type_instructions}\nBased on this company information (from their website):\n{company_info}\n\nAnd the following creative direction from the user:\n{user_answers}\n\nIMPORTANT: For this segment, provide:\n- 'scene_description': a cinematic visual description for Veo-3 (do NOT mention or describe any logos)\n- 'prompt': a concise Veo-3 prompt that includes a simple voiceover instruction, e.g., [voiceover: ...] (do NOT mention or describe any logos)\n- 'voiceover_script': a short, compelling line to be spoken as a voiceover\n- 'mood': the emotional tone and atmosphere of the scene\n- 'camera': specific camera movements and techniques to use\n\nFormat your response as valid JSON. Only return the JSON object."
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
                ad_script = improve_script_with_gemini(company_info, user_answers, ad_script)
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
        output_path = os.path.join(output_dir, f'{company_name}_ad.mp4')
        final_video_path = combine_videos(video_paths, output_path)
        print("Final video path:", final_video_path)
        # Check if file exists
        if not os.path.exists(final_video_path):
            print(f"ERROR: Video file does not exist at {final_video_path}")
            return jsonify({'error': 'Video file was not created.'}), 500
        else:
            print(f"Video file exists at {final_video_path}")
        video_url = f'/static/generated/{os.path.basename(final_video_path)}'
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