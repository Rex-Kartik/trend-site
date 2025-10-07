import google.generativeai as genai
import os
import time
import datetime
import requests
import xml.etree.ElementTree as ET

# --- Part 1: Configuration & Setup ---
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=api_key)
except ValueError as e:
    print(e)
    exit()

model = genai.GenerativeModel('gemini-pro')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HUGO_CONTENT_PATH = os.path.join(SCRIPT_DIR, "content", "posts")

PROCESSED_LOG_FILE = os.path.join(SCRIPT_DIR, "processed_topics.txt")

# --- Part 2: The Trend Spotter (Upgraded to RSS) ---
def get_trending_topics(country_code='IN'):
    """
    Fetches the top daily search trends from Google's official RSS feed.
    This method is more reliable than unofficial libraries.
    """
    print("📈 Fetching trending topics from Google Trends RSS feed...")
    # This is the public URL for the Indian daily trends RSS feed.
    RSS_URL = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={country_code}"

    try:
        # Use the 'requests' library to get the content from the URL.
        response = requests.get(RSS_URL)
        # Raise an error if the request was not successful (e.g., 404, 500).
        response.raise_for_status()

        # Parse the response content, which is in XML format.
        root = ET.fromstring(response.content)

        topics = []
        # The structure of an RSS feed is a 'channel' with multiple 'item' tags.
        # We loop through each 'item' to find its 'title'.
        for item in root.findall('./channel/item'):
            title = item.find('title').text
            if title:
                topics.append(title)

        if not topics:
            print("  ⚠️ No topics found in the RSS feed.")
            return []

        print(f"  ✅ Found {len(topics)} topics.")
        return topics

    except requests.exceptions.RequestException as e:
        print(f"  ❌ Error fetching RSS feed: {e}")
        return []
    except ET.ParseError as e:
        print(f"  ❌ Error parsing XML from RSS feed: {e}")
        return []

# --- Part 3: The AI Writer ---
def generate_article(topic):
    """Generates a news-style explanatory article for a given trending topic."""
    print(f"🤖 Generating article for: '{topic}'...")
    
    # This prompt is engineered to be more journalistic
    prompt = f"""
    Act as a neutral and objective news explainer. Your audience is the general public
    who has just heard about "{topic}" and wants to understand what it is.

    Write a concise, easy-to-understand article (around 400-500 words) explaining the topic: "{topic}".

    Your article must include:
    1.  A direct and clear introduction explaining what "{topic}" is and why it's trending.
    2.  2-3 key bullet points providing the most important facts or context.
    3.  A brief paragraph on the background or history of the topic.
    4.  A concluding sentence summarizing its significance.

    Do not use sensational language. The tone should be informative and factual.
    The final output should be a single block of text in Markdown format.
    """
    try:
        response = model.generate_content(prompt)
        # Add basic content moderation
        if response.prompt_feedback.block_reason:
            print(f"  ⚠️ Content blocked for topic '{topic}'. Reason: {response.prompt_feedback.block_reason}")
            return None
        return response.text
    except Exception as e:
        print(f"  ❌ Error generating article: {e}")
        return None

# --- Part 4: The Publisher's Assistant ---
def save_for_hugo(topic, article_content):
    """Saves the article as a Markdown file with Hugo front matter."""
    print(f"💾 Saving file for '{topic}'...")
    
    # Create a URL-friendly filename
    filename = topic.lower().replace(' ', '-').replace("'", "") + ".md"
    filepath = os.path.join(HUGO_CONTENT_PATH, filename)
    
    current_date = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    front_matter = f"""---
title: "Understanding the Trend: What is {topic}?"
date: {current_date}
draft: true
description: "A quick, clear explanation of why '{topic}' is trending. Learn the key facts and background behind today's top search."
tags: ["Trending", "News", "{topic.split(' ')[0]}"]
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
    print("\n🚀 Starting the Automated Trend Blogger...")

    # Load already processed topics to avoid duplicates
    try:
        with open(PROCESSED_LOG_FILE, 'r') as f:
            processed_topics = set(f.read().splitlines())
    except FileNotFoundError:
        processed_topics = set()
    
    trending_topics = get_trending_topics()
    
    if not trending_topics:
        print("No topics to process. Exiting.")
        exit()

    new_topics_found = 0
    for topic in trending_topics:
        if topic not in processed_topics:
            new_topics_found += 1
            article = generate_article(topic)
            if article:
                if save_for_hugo(topic, article):
                    # Log the topic as processed only if it was saved successfully
                    with open(PROCESSED_LOG_FILE, 'a') as f:
                        f.write(topic + '\n')
            
            print("--- Pausing for 15 seconds ---")
            time.sleep(15) # A longer delay for this more intensive process
    
    if new_topics_found == 0:
        print("✅ No new trends to report. Everything is up to date.")

    print(" ciclo de trabajo completado.")
