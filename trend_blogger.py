# ==============================================================================
# AI TREND SYNTHESIS ENGINE
# ==============================================================================
# This script is the core of the automated content website. Its job is to:
# 1. Gather raw trend signals from Google Trends and Reddit.
# 2. Use a powerful AI to analyze these signals and synthesize high-level trends.
# 3. For each trend, command the AI to write an in-depth explanatory article.
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
# In this section, we securely load all our secret API keys and configure our clients.
# This code will fail with a helpful error if any key is missing.

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
    # If any key is missing, print a clear error message and stop the script.
    print(f"ERROR: A required environment variable is likely missing: {e}")
    exit()

# Initialize the Gemini model we want to use. 'gemini-1.5-flash-latest' is fast and powerful.
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# DYNAMIC PATHS: These ensure the script works on any computer (your Windows PC or the Linux GitHub robot).
# Get the absolute path of the directory where this script is located.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Intelligently join the script's path with the subfolders to create a full, correct path.
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
        # Prepare the parameters for our SerpApi request.
        params = {
            "engine": "google_trends_trending_now", # The specific SerpApi engine for trends.
            "frequency": "daily",                    # We want daily trends.
            "geo": "IN",                             # Geographical location: India.
            "api_key": serpapi_key                   # Our secret API key.
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Extract the list of search queries from the nested dictionary response.
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
            # Get the top 10 "hot" (trending) posts from each subreddit.
            for submission in subreddit.hot(limit=10):
                # Ignore posts pinned by moderators as they are usually announcements, not trends.
                if not submission.stickied:
                    raw_signals.append(submission.title)
        except Exception as e:
            print(f"    - Could not fetch from r/{sub}: {e}")

    if not raw_signals:
        print("  ❌ No raw signals gathered. Exiting.")
        return []

    # Step C: Use the AI to analyze the raw signals and synthesize the actual trends.
    print(f"  🤖 Sending {len(raw_signals)} raw signals to AI for synthesis...")
    # Join all the signals into one big block of text for the AI to analyze.
    signals_text = "\n".join(raw_signals)
    
    # This is our sophisticated "synthesis" prompt. We're asking the AI to act as an analyst.
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
        # Parse the AI's response: split the string by '|' and clean up any whitespace.
        synthesized_trends = [topic.strip() for topic in response.text.split('|')]
        print(f"  ✅ AI synthesized {len(synthesized_trends)} relevant trends.")
        return synthesized_trends
    except Exception as e:
        print(f"  ❌ AI synthesis failed: {e}")
        return []


# --- Part 3: The AI Writer ---
def generate_article(topic):
    """Generates an in-depth explanatory article for a given trend."""
    print(f"✍️  Generating article for trend: '{topic}'...")
    
    # This prompt asks the AI to act as an expert and write a detailed explanation of the trend.
    prompt = f"""
    Act as an expert analyst explaining a major trend to a curious audience. Your audience is familiar with the basics of tech, science, and gaming but wants a deeper understanding of what's happening.
    Write a clear, insightful article (around 500-600 words) explaining the trend: "{topic}".
    Your article must include:
    1.  An introduction that defines the trend and explains why it's significant right now.
    2.  2-3 body paragraphs, each exploring a key aspect of the trend (e.g., the key players, the technology involved, the potential impact).
    3.  A concluding paragraph that looks to the future of this trend.
    The tone should be authoritative but accessible. The final output should be in Markdown format.
    """
    try:
        response = model.generate_content(prompt)
        # Safety check: if the AI's response was blocked for safety reasons, return nothing.
        if response.prompt_feedback.block_reason:
            print(f"  ⚠️ Content blocked for trend '{topic}'. Reason: {response.prompt_feedback.block_reason}")
            return None
        return response.text
    except Exception as e:
        print(f"  ❌ Error generating article: {e}")
        return None


# --- Part 4: The Publisher's Assistant (ULTRA-ROBUST FINAL VERSION) ---
def save_for_hugo(topic, article_content):
    """
    Saves the article as a Markdown file with Hugo front matter.
    Includes a powerful sanitizer to create valid filenames for ALL operating systems.
    """
    print(f"💾 Saving file for '{topic}'...")

    # Sanitize the topic to create a valid, cross-platform-safe filename.
    sanitized_topic = topic.lower()
    # Use regex to replace any sequence of spaces or non-alphanumeric characters with a single hyphen.
    sanitized_topic = re.sub(r'[\s\W_]+', '-', sanitized_topic)
    # Remove any stray hyphens from the beginning or end.
    sanitized_topic = sanitized_topic.strip('-')
    # Limit the filename length to prevent errors and add the .md extension.
    filename = sanitized_topic[:100] + ".md"

    filepath = os.path.join(HUGO_CONTENT_PATH, filename)
    
    current_date = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # This is the metadata block (front matter) that goes at the top of every Hugo article.
    front_matter = f"""---
title: "Decoding the Trend: {topic.replace('"', "'")}"
date: {current_date}
draft: false
description: "An in-depth look at the emerging trend of {topic.replace('"', "'")} and what it means for the future."
tags: ["Trends", "{topic.split(' ')[0]}"]
---
"""
    
    full_content = front_matter + "\n" + article_content
    try:
        # Write the final content to the file, using UTF-8 encoding for broad character support.
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)
        print(f"  ✅ Successfully saved: {filepath}")
        return True
    except Exception as e:
        print(f"  ❌ Error saving file: {e}")
        return False


# --- Part 5: The Main Execution Loop ---
# This is the part of the script that runs when you execute `python trend_blogger.py`.
if __name__ == "__main__":
    print("\n🚀 Starting the AI Trend Synthesis Engine...")
    
    # Load the list of topics we've already written about to avoid duplicates.
    try:
        with open(PROCESSED_LOG_FILE, 'r') as f:
            processed_topics = set(f.read().splitlines())
    except FileNotFoundError:
        processed_topics = set() # If the file doesn't exist yet, start with an empty set.
    
    # Call our main function to get the list of trends.
    trending_topics = get_and_synthesize_topics()
    
    if not trending_topics:
        print("No new trends to process after synthesis. Exiting.")
        exit()

    new_topics_found = 0
    # Loop through each synthesized trend.
    for topic in trending_topics:
        # Process the topic only if it's new and not an empty string.
        if topic not in processed_topics and topic:
            new_topics_found += 1
            article = generate_article(topic)
            if article:
                if save_for_hugo(topic, article):
                    # If the article was saved successfully, add the topic to our log file.
                    with open(PROCESSED_LOG_FILE, 'a') as f:
                        f.write(topic + '\n')
            
            # Pause between each article to be respectful of the APIs and avoid rate limits.
            print("--- Pausing for 20 seconds ---")
            time.sleep(20)
    
    if new_topics_found == 0:
        print("✅ No new trends to report. All synthesized trends have been processed.")

    print(" ciclo de trabajo completado.")

