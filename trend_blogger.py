# --- Required Imports ---
import google.generativeai as genai
import os
import time
import datetime
import requests
import xml.etree.ElementTree as ET
import re

# --- Part 1: Configuration & Setup ---
try:
    # Securely get the API key from environment variables.
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=api_key)
except ValueError as e:
    print(e)
    exit()

# Use the latest stable and fast model from Google.
model = genai.GenerativeModel('gemini-2.5-flash')

# DYNAMIC PATHS: These will work on ANY computer (your local PC or the GitHub robot).
# This gets the directory where the script itself is located.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# This intelligently joins the paths, using the correct slashes ('\' or '/') for the OS.
HUGO_CONTENT_PATH = os.path.join(SCRIPT_DIR, "content", "posts")
PROCESSED_LOG_FILE = os.path.join(SCRIPT_DIR, "processed_topics.txt")


# --- Part 2: The Intelligent Topic Curation Engine ---
def get_and_filter_topics():
    """
    Fetches headlines from multiple niche RSS feeds and uses an AI to select
    the most relevant trending topics.
    """
    print("🧠 Starting topic curation engine...")
    
    # Step A: Gather Intelligence from Multiple Specialized Sources
    source_urls = {
        "Technology": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0JXVnVMVWRDR2dKSlRpZ0FQAQ?hl=en-IN&gl=IN&ceid=IN:en",
        "Science": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y1RjU0JXVnVMVWRDR2dKSlRpZ0FQAQ?hl=en-IN&gl=IN&ceid=IN:en",
        # We use a reliable industry source for gaming news.
        "Gaming": "https://www.gamespot.com/feeds/news"
    }
    
    raw_headlines = []
    print("  📰 Gathering headlines from sources...")
    for category, url in source_urls.items():
        try:
            response = requests.get(url, timeout=10) # Added a timeout for safety
            response.raise_for_status()
            root = ET.fromstring(response.content)
            for item in root.findall('./channel/item'):
                title = item.find('title').text
                if title:
                    raw_headlines.append(title.strip())
        except Exception as e:
            print(f"    - Could not fetch from {category}: {e}")

    if not raw_headlines:
        print("  ❌ No headlines gathered. Exiting.")
        return []

    # Step B: Use AI to Identify and Filter the Best Topics
    print(f"  🤖 Sending {len(raw_headlines)} headlines to AI for filtering...")
    
    headlines_text = "\n".join(raw_headlines)
    
    prompt = f"""
    Act as a senior editor for a tech, science, and gaming news website.
    From the following list of raw news headlines, identify the most significant and interesting
    trending TOPICS. A topic is a specific product, event, or discovery (e.g., "iPhone 20 Launch",
    "James Webb Telescope Discovery", "New Elden Ring DLC").

    Do not just repeat the headlines. Extract the core subject.
    Filter out minor stories, political news, and anything not directly related to technology,
    science, or video games.

    Return only a list of the top 10 most important topics, separated by a pipe character '|' and 
    not anything else like 'Here are the top 10 most significant and interesting trending topics from the raw news headlines:'.

    Example Output: iPhone 20 Launch|James Webb Telescope Discovery|New Elden Ring DLC

    --- HEADLINES ---
    {headlines_text}
    """
    
    try:
        response = model.generate_content(prompt)
        # Parse the response: split the string by '|' and clean up any whitespace
        filtered_topics = [topic.strip() for topic in response.text.split('|')]
        print(f"  ✅ AI selected {len(filtered_topics)} relevant topics.")
        return filtered_topics
    except Exception as e:
        print(f"  ❌ AI filtering failed: {e}")
        return []


# --- Part 3: The AI Writer ---
def generate_article(topic):
    """Generates a news-style explanatory article for a given trending topic."""
    print(f"✍️  Generating article for: '{topic}'...")
    prompt = f"""
    Act as a neutral and objective news explainer. Your audience is the general public
    who has just heard about "{topic}" and wants to understand what it is.
    Write a concise, easy-to-understand article (around 400-500 words) explaining the topic: "{topic}".
    Your article must include:
    1.  A direct and clear introduction explaining the topic.
    2.  2-3 key bullet points providing the most important facts.
    3.  A brief paragraph on the background or significance.
    4.  A concluding sentence summarizing its importance.
    The tone should be informative and factual. The final output should be in Markdown format.
    """
    try:
        response = model.generate_content(prompt)
        if response.prompt_feedback.block_reason:
            print(f"  ⚠️ Content blocked for topic '{topic}'. Reason: {response.prompt_feedback.block_reason}")
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
    # 1. Convert to lowercase
    sanitized_topic = topic.lower()
    # 2. Replace spaces and all non-alphanumeric characters with a hyphen
    sanitized_topic = re.sub(r'[\s\W_]+', '-', sanitized_topic)
    # 3. Remove any leading or trailing hyphens that might result
    sanitized_topic = sanitized_topic.strip('-')
    # 4. Truncate to a reasonable length to prevent "filename too long" errors
    filename = sanitized_topic[:100] + ".md"

    filepath = os.path.join(HUGO_CONTENT_PATH, filename)
    
    current_date = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Use the original, human-readable topic for the title.
    # Replace any double quotes in the title to prevent breaking the TOML format.
    front_matter = f"""---
title: "Explaining the Trend: {topic.replace('"', "'")}"
date: {current_date}
draft: false
description: "A quick, clear explanation of the trending topic: {topic.replace('"', "'")}"
tags: ["Trending", "{topic.split(' ')[0]}"]
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
    print("\n🚀 Starting the AI Curation Blogger...")
    
    try:
        with open(PROCESSED_LOG_FILE, 'r') as f:
            processed_topics = set(f.read().splitlines())
    except FileNotFoundError:
        processed_topics = set()
    
    # The main change is calling our new function here
    trending_topics = get_and_filter_topics()
    
    if not trending_topics:
        print("No new topics to process after filtering. Exiting.")
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
            
            print("--- Pausing for 15 seconds ---")
            time.sleep(15)
    
    if new_topics_found == 0:
        print("✅ No new topics to report. Everything is up to date.")

    print(" ciclo de trabajo completado.")

