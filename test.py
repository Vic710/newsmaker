import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
if not GNEWS_API_KEY:
    raise ValueError("GNEWS_API_KEY not found in .env file")

# Set up paths
SAVE_DIR = os.path.join(os.getcwd(), "news_files")
os.makedirs(SAVE_DIR, exist_ok=True)
ALL_NEWS_JSON = os.path.join(SAVE_DIR, "all_news.json")

# Build GNews API URL with expand=content to get full article content (if available)
# Query: "business technology news"
GNEWS_URL = f"https://gnews.io/api/v4/search?q=business+technology+news&lang=en&max=20&from=24h&expand=content&apikey={GNEWS_API_KEY}"

def fetch_news():
    print("Fetching news from GNews API...")
    try:
        response = requests.get(GNEWS_URL, timeout=15)
        if response.status_code != 200:
            print(f"Error fetching news: Status code {response.status_code}")
            return []
        data = response.json()
        articles = data.get("articles", [])
        print(f"Fetched {len(articles)} articles from GNews API.")
        return articles
    except Exception as e:
        print(f"Exception fetching news: {e}")
        return []

def main():
    articles = fetch_news()
    with open(ALL_NEWS_JSON, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2)
    print(f"Saved articles to {ALL_NEWS_JSON}")

if __name__ == "__main__":
    main()
