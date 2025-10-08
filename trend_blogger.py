# --- Required Imports ---
import google.generativeai as genai
import os
import time
import datetime
import re
import praw
from pytrends.request import TrendReq

# --- Part 1: Configuration & Setup ---
try:
    # Securely configure the Gemini AI client
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    
    # Securely configure the Reddit client (PRAW)
    reddit = praw.Reddit(
        client_id=os.environ.get("REDDIT_CLIENT_ID"),
        client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
        user_agent=os.environ.get("REDDIT_USER_AGENT"),
        check_for_async=False # Necessary for use in a synchronous script
    )
except Exception as e:
    print(f"ERROR: A required environment variable is likely missing: {e}")
    exit()

# Use the latest stable and fast model from Google
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# DYNAMIC PATHS: These will work on ANY computer (your local PC or the GitHub robot).
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
    raw_signals = []

    # Step A: Gather Google Trends Signals
    print("  📈 Gathering signals from Google Trends...")
    try:
        pytrends = TrendReq(hl='en-US', tz=330) # IST
        # Fetch trending searches in India
        trending_df = pytrends.trending_searches(pn='india')
        raw_signals.extend(trending_df[0].tolist())
    except Exception as e:
        print(f"    - Could not fetch from Google Trends: {e}")
    
    # Step B: Gather Reddit Signals
    print("  💬 Gathering signals from Reddit...")
    subreddits = ['technology', 'science', 'gaming']
    for sub in subreddits:
        try:
            # Get the top 10 'hot' posts from the subreddit
            subreddit = reddit.subreddit(sub)
            for submission in subreddit.hot(limit=10):
                if not submission.stickied: # Ignore moderator-pinned posts
                    raw_signals.append(submission.title)
        except Exception as e:
            print(f"    - Could not fetch from r/{sub}: {e}")

    if not raw_signals:
        print("  ❌ No raw signals gathered. Exiting.")
        return []

    # Step C: Use AI to Synthesize Trends from Signals
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
        # Parse the response: split the string by '|' and clean up any whitespace
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

    # Sanitize the topic to create a valid filename
    sanitized_topic = topic.lower()
    # Replace spaces and all non-alphanumeric characters with a hyphen
    sanitized_topic = re.sub(r'[\s\W_]+', '-', sanitized_topic)
    # Remove any leading or trailing hyphens that might result
    sanitized_topic = sanitized_topic.strip('-')
    # Truncate to a reasonable length to prevent "filename too long" errors
    filename = sanitized_topic[:100] + ".md"

    filepath = os.path.join(HUGO_CONTENT_PATH, filename)
    
    current_date = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Use the original, human-readable topic for the title.
    # Replace any double quotes in the title to prevent breaking the TOML format.
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
    
    # Call our new, intelligent synthesis function
    trending_topics = get_and_synthesize_topics()
    
    if not trending_topics:
        print("No new trends to process after synthesis. Exiting.")
        exit()

    new_topics_found = 0
    for topic in trending_topics:
        # Also check if the topic is not an empty string
        if topic not in processed_topics and topic:
            new_topics_found += 1
            article = generate_article(topic)
            if article:
                if save_for_hugo(topic, article):
                    with open(PROCESSED_LOG_FILE, 'a') as f:
                        f.write(topic + '\n')
            
            # A longer pause for a more intensive process
            print("--- Pausing for 20 seconds ---")
            time.sleep(20)
    
    if new_topics_found == 0:
        print("✅ No new trends to report. All synthesized trends have been processed.")

    print(" ciclo de trabajo completado.")

