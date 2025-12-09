import feedparser
import os
import requests
import datetime

# --- Configuration ---
RSS_URL = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
API_URL = "https://api.perplexity.ai/chat/completions"

def get_top_trend():
    """Fetches the #1 trending topic from Google RSS."""
    print("Fetching trends...")
    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        # Get the first (top) trend
        top_trend = feed.entries
        topic = top_trend.title
        # Trends RSS often includes traffic info, helpful for context
        traffic = getattr(top_trend, 'ht_approx_traffic', 'N/A')
        print(f"Top Trend found: {topic} ({traffic} searches)")
        return topic
    return None

def generate_article(topic):
    """Uses Perplexity to research and write an article."""
    print(f"Querying Perplexity for: {topic}...")
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # We use the 'sonar' model which has internet access
    payload = {
        "model": "sonar", 
        "messages":
    }
    
    response = requests.post(API_URL, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()['choices']['message']['content']
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def update_html_file(article_html, topic):
    """Updates index.html with the new article."""
    print("Building website...")
    
    today = datetime.date.today().strftime("%B %d, %Y")
    
    # Simple HTML Template
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Daily Trend: {topic}</title>
        <style>
            body {{ font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
            h1 {{ color: #333; }}
           .date {{ color: #666; font-style: italic; }}
           .footer {{ margin-top: 50px; font-size: 0.8em; color: #888; }}
        </style>
    </head>
    <body>
        <div class="date">Trend for {today}</div>
        {article_html}
        <div class="footer">Automated by Perplexity API & GitHub Actions</div>
    </body>
    </html>
    """
    
    with open("index.html", "w") as f:
        f.write(full_html)
    print("index.html updated successfully.")

if __name__ == "__main__":
    if not PERPLEXITY_API_KEY:
        print("Error: PERPLEXITY_API_KEY not found.")
        exit(1)

    trend = get_top_trend()
    if trend:
        content = generate_article(trend)
        if content:
            update_html_file(content, trend)
