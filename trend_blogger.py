# ==============================================================================
# AI TREND SYNTHESIS ENGINE (API SUBMISSION VERSION)
# ==============================================================================
# This is the final version of the content engine. Its job is to:
# 1. Gather and synthesize trends from Google and Reddit.
# 2. Generate an article and tags using the Gemini AI.
# 3. Submit the finished article to the live Trend Nexus FastAPI backend.
# ==============================================================================

# --- Required Imports ---
import google.generativeai as genai
import os
import time
import re
import praw
from serpapi import GoogleSearch
import requests # We will use this to make HTTP requests to our API

# --- Part 1: Configuration & Secure Setup ---
try:
    # Configure all the service clients using environment variables
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    reddit = praw.Reddit(
        client_id=os.environ.get("REDDIT_CLIENT_ID"),
        client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
        user_agent=os.environ.get("REDDIT_USER_AGENT"),
        check_for_async=False
    )
    serpapi_key = os.environ.get("SERPAPI_API_KEY")
    # Get the base URL for our own API from the environment variables
    api_base_url = os.environ.get("API_BASE_URL")
    if not all([serpapi_key, api_base_url]):
        raise ValueError("One or more critical environment variables are missing.")

except Exception as e:
    print(f"ERROR: Configuration failed: {e}")
    exit()

model = genai.GenerativeModel('gemini-1.5-flash')
PROCESSED_LOG_FILE = "processed_topics.txt" # This still runs locally in the Action


# --- Part 2: Topic Curation Engine (No Changes) ---
def get_and_synthesize_topics():
    # This entire function is unchanged. Its logic is perfect.
    print("🧠 Starting trend synthesis engine...")
    # ... (rest of the function is the same as your previous version)
    raw_signals = []
    print("  📈 Gathering signals from Google Trends via SerpApi...")
    try:
        params = {"engine": "google_trends_trending_now", "frequency": "daily", "geo": "IN", "api_key": serpapi_key}
        search = GoogleSearch(params)
        results = search.get_dict()
        trending_searches = results.get('trending_stories', [])
        for story in trending_searches:
            raw_signals.extend(story.get('searches', []))
    except Exception as e:
        print(f"    - Could not fetch from SerpApi: {e}")
    print("  💬 Gathering signals from Reddit...")
    subreddits = ['technology', 'science', 'gaming']
    for sub in subreddits:
        try:
            subreddit = reddit.subreddit(sub)
            for submission in subreddit.hot(limit=10):
                if not submission.stickied:
                    raw_signals.append(submission.title)
        except Exception as e:
            print(f"    - Could not fetch from r/{sub}: {e}")
    if not raw_signals:
        print("  ❌ No raw signals gathered. Exiting.")
        return []
    print(f"  🤖 Sending {len(raw_signals)} raw signals to AI for synthesis...")
    signals_text = "\n".join(raw_signals)
    prompt = """
    Act as a professional trend analyst... (rest of your prompt)
    """
    try:
        response = model.generate_content(prompt)
        synthesized_trends = [topic.strip() for topic in response.text.split('|')]
        print(f"  ✅ AI synthesized {len(synthesized_trends)} relevant trends.")
        return synthesized_trends
    except Exception as e:
        print(f"  ❌ AI synthesis failed: {e}")
        return []


# --- Part 3: AI Writer & Tagger (No Changes) ---
def generate_article_and_tags(topic):
    # This function is also unchanged.
    print(f"✍️  Generating article and tags for: '{topic}'...")
    # ... (rest of the function is the same as your previous version)
    prompt = """
    You have two tasks... (rest of your prompt)
    """
    try:
        response = model.generate_content(prompt)
        if response.prompt_feedback.block_reason:
            return None
        parts = response.text.split("\ntags:")
        content = parts[0].strip()
        tags = ["trends"]
        if len(parts) > 1:
            tags = [tag.strip() for tag in parts[1].split(',')]
        return {"content": content, "tags": tags}
    except Exception as e:
        print(f"  ❌ Error generating article and tags: {e}")
        return None

# --- Part 4: The NEW API Publisher ---
# This function replaces the old 'save_for_hugo' function.
def post_article_to_api(topic, article_data):
    """
    Submits the newly generated article to the live Trend Nexus FastAPI backend.
    """
    print(f"📡 Submitting article '{topic}' to the API...")
    
    # The URL for the specific endpoint we want to send data to.
    api_url = f"{api_base_url}/posts"
    
    # The data payload. The keys ('topic', 'content', 'tags') MUST match
    # the keys in our Pydantic 'PostInput' model in the FastAPI app.
    payload = {
        "topic": topic,
        "content": article_data["content"],
        "tags": article_data["tags"]
    }
    
    try:
        # Use the 'requests' library to send an HTTP POST request.
        # 'json=payload' automatically formats our data and sets the correct headers.
        response = requests.post(api_url, json=payload, timeout=30)
        
        # This will raise an error if the API returned a bad status (like 404 or 500).
        response.raise_for_status()
        
        print(f"  ✅ Successfully submitted article. API responded with status {response.status_code}.")
        return True

    except requests.exceptions.RequestException as e:
        print(f"  ❌ Error submitting article to API: {e}")
        return False


# --- Part 5: The Main Execution Loop (Upgraded) ---
if __name__ == "__main__":
    print("\n🚀 Starting the AI Trend Synthesis Engine (API Mode)...")
    
    # We still use the local processed_topics.txt to avoid re-processing trends in the same run.
    try:
        with open(PROCESSED_LOG_FILE, 'r') as f:
            processed_topics = set(f.read().splitlines())
    except FileNotFoundError:
        processed_topics = set()
    
    trending_topics = get_and_synthesize_topics()
    
    if not trending_topics:
        print("No new trends to process after synthesis. Exiting.")
        exit()

    new_topics_found = 0
    for topic in trending_topics:
        if topic not in processed_topics and topic:
            new_topics_found += 1
            article_data = generate_article_and_tags(topic)
            if article_data and article_data['content']:
                # THIS IS THE MAIN CHANGE: We call the new API publisher function.
                if post_article_to_api(topic, article_data):
                    # If the API submission was successful, we log the topic as processed.
                    with open(PROCESSED_LOG_FILE, 'a') as f:
                        f.write(topic + '\n')
            
            print("--- Pausing for 20 seconds ---")
            time.sleep(20)
    
    if new_topics_found == 0:
        print("✅ No new trends to report. All synthesized trends have been processed.")

    print(" ciclo de trabajo completado.")

