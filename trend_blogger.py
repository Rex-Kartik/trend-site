# ==============================================================================
# AI TREND SYNTHESIS ENGINE
# ==============================================================================
# This script is the core of the automated content website. Its job is to:
# 1. Gather raw trend signals from Google Trends (via SerpApi) and Reddit.
# 2. Use a powerful AI to analyze these signals and synthesize high-level trends.
# 3. For each trend, command the AI to write an in-depth article and relevant SEO tags.
# 4. Save these articles in a format ready for the Hugo website to publish.
# ==============================================================================

# --- Required Imports ---
# Import all the libraries and tools we will need to run our script.

import google.generativeai as genai  # The library to talk to the Gemini AI.
import os                            # Used to access environment variables and file system paths.
import time                          # Used to make the script pause between API calls.
import datetime                      # Used to get the current date for our articles.
import re                            # The "Regular Expressions" library, for powerful text manipulation.
import praw                          # The official library for interacting with the Reddit API.
from serpapi import GoogleSearch     # The official library for the SerpApi service.


# --- Part 1: Configuration & Secure Setup ---
# In this section, we securely load all our secret API keys from the environment
# (provided by GitHub Actions secrets) and configure our service clients.

try:
    # Configure the Gemini AI client using the key from GitHub Secrets.
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    
    # Configure the Reddit client (PRAW) using the keys from GitHub Secrets.
    # The 'check_for_async=False' is required for this library to work in a standard script.
    reddit = praw.Reddit(
        client_id=os.environ.get("REDDIT_CLIENT_ID"),
        client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
        user_agent=os.environ.get("REDDIT_USER_AGENT"),
        check_for_async=False
    )

    # Get the SerpApi key from GitHub Secrets. We will use it later.
    serpapi_key = os.environ.get("SERPAPI_API_KEY")
    if not serpapi_key:
        raise ValueError("SERPAPI_API_KEY environment variable not set.")

except Exception as e:
    # If any key is missing, the script will stop with a clear error message.
    print(f"ERROR: A required environment variable is likely missing: {e}")
    exit()

# THIS IS THE CHANGE: Initialize the specific Gemini model you requested.
model = genai.GenerativeModel('gemini-2.5-flash')

# DYNAMIC PATHS: These ensure the script works on any computer (your Windows PC or the Linux GitHub robot).
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HUGO_CONTENT_PATH = os.path.join(SCRIPT_DIR, "content", "posts")
PROCESSED_LOG_FILE = os.path.join(SCRIPT_DIR, "processed_topics.txt")


# --- Part 2: The Intelligent Topic Curation Engine ---
def get_and_synthesize_topics():
    """
    Gathers raw signals from Google Trends and Reddit, then uses an AI to
    synthesize them into high-level, relevant trend topics.
    """
    print("🧠 Starting trend synthesis engine...")
    raw_signals = [] # An empty list to store all the data we gather.

    # Step A: Gather Google Trends Signals via the reliable SerpApi.
    print("  📈 Gathering signals from Google Trends via SerpApi...")
    try:
        params = {
            "engine": "google_trends_trending_now",
            "frequency": "daily",
            "geo": "IN",
            "api_key": serpapi_key
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        trending_searches = results.get('trending_stories', [])
        for story in trending_searches:
            raw_signals.extend(story.get('searches', []))
    except Exception as e:
        print(f"    - Could not fetch from SerpApi: {e}")
    
    # Step B: Gather Reddit Signals from relevant communities.
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

    # Step C: Use the AI to analyze the raw signals and synthesize the actual trends.
    print(f"  🤖 Sending {len(raw_signals)} raw signals to AI for synthesis...")
    signals_text = "\n".join(raw_signals)
    
    prompt = f"""
    Act as a professional trend analyst for a website focused on technology, science, and gaming.
    Based on the following list of raw Google search queries and Reddit discussion titles, your task is to identify and synthesize the 5 most significant, high-level TRENDS.

    A trend is a broader topic, not just a single news event. For example, if you see signals like 'Nvidia RTX 5090 price', 'AMD RDNA 5 release date', and 'Intel Battlemage specs', the underlying trend is "The Next Generation of GPUs".

    Filter out all noise, celebrity gossip, politics, and minor news. Focus only on genuinely interesting trends in tech, science, or gaming.
    Return a list of the top 5 most important trends, separated by a pipe character '|'.

    Example Output: The Next Generation of GPUs|Breakthroughs in AI Drug Discovery|The Rise of Indie Game Development

    --- RAW SIGNALS ---
    {signals_text}
    """
    
    try:
        response = model.generate_content(prompt)
        synthesized_trends = [topic.strip() for topic in response.text.split('|')]
        print(f"  ✅ AI synthesized {len(synthesized_trends)} relevant trends.")
        return synthesized_trends
    except Exception as e:
        print(f"  ❌ AI synthesis failed: {e}")
        return []


# --- Part 3: The AI Writer & Tagger ---
def generate_article_and_tags(topic):
    """
    Generates an article AND a list of relevant SEO tags for the given topic.
    Returns a dictionary containing 'content' and 'tags'.
    """
    print(f"✍️  Generating article and tags for: '{topic}'...")
    prompt = f"""
    You have two tasks.

    TASK 1: Act as an expert analyst explaining a major trend to a curious audience. Write a clear, insightful article (around 500-600 words) explaining the trend: "{topic}". The article should include an introduction, 2-3 body paragraphs, and a future-looking conclusion.

    TASK 2: Based on the article you just wrote, generate 3 to 4 relevant, single-word, lowercase tags that are useful for SEO. The first tag should always be 'trends'.

    First, write the complete article. Then, on a new line after the article, write 'tags:' followed by the comma-separated tags.

    --- EXAMPLE ---
    [Full Article Text Here]
    ...
    ...
    tags: trends,ai,discovery,research
    """
    try:
        response = model.generate_content(prompt)
        if response.prompt_feedback.block_reason:
            print(f"  ⚠️ Content blocked for trend '{topic}'.")
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


# --- Part 4: The Publisher's Assistant ---
def save_for_hugo(topic, article_data):
    """
    Saves the article to a file, using the content and tags from the article_data dictionary.
    Includes robust filename sanitization.
    """
    print(f"💾 Saving file for '{topic}'...")

    sanitized_topic = topic.lower()
    sanitized_topic = re.sub(r'[\s\W_]+', '-', sanitized_topic)
    sanitized_topic = sanitized_topic.strip('-')
    filename = sanitized_topic[:100] + ".md"
    filepath = os.path.join(HUGO_CONTENT_PATH, filename)
    
    current_date = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    tags_formatted = str(article_data['tags']).replace("'", '"')

    front_matter = f"""---
title: "Decoding the Trend: {topic.replace('"', "'")}"
date: {current_date}
draft: false
description: "An in-depth look at the emerging trend of {topic.replace('"', "'")} and what it means for the future."
tags: {tags_formatted}
---
"""
    
    full_content = front_matter + "\n" + article_data['content']
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)
        print(f"  ✅ Successfully saved: {filepath}")
        return True
    except Exception as e:
        print(f"  ❌ Error saving file: {e}")
        return False


# --- Part 5: The Main Execution Loop ---
if __name__ == "__main__":
    print("\n🚀 Starting the AI Trend Synthesis Engine...")
    
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
                if save_for_hugo(topic, article_data):
                    with open(PROCESSED_LOG_FILE, 'a') as f:
                        f.write(topic + '\n')
            
            print("--- Pausing for 20 seconds ---")
            time.sleep(20)
    
    if new_topics_found == 0:
        print("✅ No new trends to report. All synthesized trends have been processed.")

    print(" ciclo de trabajo completado.")