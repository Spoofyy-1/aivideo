import os
import sys
import replicate
from dotenv import load_dotenv

def generate_video(prompt):
    """
    Generate a video using Google's Veo-3 model.
    
    Args:
        prompt (str): The text prompt to generate the video from
        
    Returns:
        str: URL to the generated video
    """
    # Load environment variables
    load_dotenv()
    
    # Check for API key
    if not os.getenv("REPLICATE_API_TOKEN"):
        raise ValueError("REPLICATE_API_TOKEN not found in environment variables")
    
    # Run the model
    output = replicate.run(
        "google/veo-3",
        input={
            "prompt": prompt,
            # Add any additional parameters as needed
            # "num_frames": 24,  # Example parameter
            # "fps": 8,         # Example parameter
        }
    )
    
    return output

def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_video.py 'Your text prompt here'")
        sys.exit(1)
    
    prompt = sys.argv[1]
    try:
        video_url = generate_video(prompt)
        print(f"Video generated successfully!")
        print(f"Video URL: {video_url}")
    except Exception as e:
        print(f"Error generating video: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 