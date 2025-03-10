import os
import json
import time
import re
import requests
import random
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
if not GNEWS_API_KEY:
    raise ValueError("GNEWS_API_KEY not found in .env file")

# Set up Gemini API keys (cyclic)
gemini_keys_str = os.getenv("GEMINI_API_KEYS")
if gemini_keys_str:
    gemini_keys = [key.strip() for key in gemini_keys_str.split(",") if key.strip()]
else:
    single_key = os.getenv("GEMINI_API_KEY")
    if not single_key:
        raise ValueError("No Gemini API key found in environment")
    gemini_keys = [single_key]

# Initialize gemini_index (starting at 1 as per your snippet)
gemini_index = 1
def get_next_gemini_key():
    global gemini_index
    key = gemini_keys[gemini_index]
    gemini_index = (gemini_index + 1) % len(gemini_keys)
    return key

# Configure Gemini with the first key
genai.configure(api_key=get_next_gemini_key())
model = genai.GenerativeModel('gemini-1.5-pro')

# Set up paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(SCRIPT_DIR, "news_files")
os.makedirs(SAVE_DIR, exist_ok=True)

# Build GNews API URL (using GNews as before)
GNEWS_URL = f"https://gnews.io/api/v4/search?q=business+technology&lang=en&max=10&from=24h&expand=content&apikey={GNEWS_API_KEY}"

def fetch_news_from_gnews():
    """Fetch news articles using GNews API and map them to our format."""
    print("Fetching news from GNews API...")
    try:
        response = requests.get(GNEWS_URL, timeout=15)
        if response.status_code != 200:
            print(f"Error fetching news: Status code {response.status_code}")
            return []
        data = response.json()
        articles = data.get("articles", [])
        news_data = []
        for art in articles:
            news_data.append({
                "title": art.get("title", "No title"),
                "source": art.get("source", {}).get("name", "No source"),
                "time": art.get("publishedAt", "No time"),
                "link": art.get("url", "No link"),
                # Use full content if available; otherwise fallback to description.
                "content": art.get("content") or art.get("description", "No description"),
                "image": art.get("image")  # Image URL provided by GNews.
            })
        print(f"Fetched {len(news_data)} articles from GNews API.")
        with open(os.path.join(SAVE_DIR, "all_news.json"), "w", encoding="utf-8") as f:
            json.dump(news_data, f, indent=2)
        return news_data
    except Exception as e:
        print(f"Exception fetching news from GNews API: {e}")
        return []

def select_top_articles_with_gemini(news_data, top_n=10):
    """
    Uses Gemini to select the top relevant articles from the fetched news list.
    Returns exactly top_n articles (based on Gemini's selection).
    """
    if not news_data:
        print("No news data to process")
        return []
    print(f"Asking Gemini to select top {top_n} articles from {len(news_data)} articles...")
    prompt = f"""
You are an expert business and technology news curator. I have fetched {len(news_data)} news articles and need you to select the {top_n} most relevant, impactful, and interesting articles about business technology.

Criteria:
1. Focus on significant technological innovations, major business deals, or industry-transforming news.
2. Prefer articles from reputable sources.
3. Prioritize diversity in topics.
4. Select articles that are timely with long-term impact.
5. Avoid duplicate or overly similar topics.

Here are the articles (with title, source, and description):

{json.dumps([{"title": item["title"], "source": item["source"], "description": item["content"], "link": item["link"]} for item in news_data], indent=2)}

Select exactly {top_n} articles and provide your answer strictly as a JSON array of objects with the following keys:
{{
    "index": <the index of the article in the original list>,
    "reason": "<brief explanation of why you selected this article>"
}}

Return only the JSON array, with no additional text.
"""
    try:
        response = model.generate_content(prompt)
        response_text = response.text
        json_start = response_text.find('[')
        json_end = response_text.rfind(']') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            selected_indices = json.loads(json_str)
            selected_articles = []
            for selection in selected_indices:
                idx = selection.get("index")
                if isinstance(idx, int) and 0 <= idx < len(news_data):
                    article = news_data[idx]
                    article["selection_reason"] = selection.get("reason", "Selected by AI")
                    selected_articles.append(article)
            print(f"Gemini selected {len(selected_articles)} articles")
            with open(os.path.join(SAVE_DIR, "selected_news.json"), "w", encoding="utf-8") as f:
                json.dump(selected_articles, f, indent=2)
            return selected_articles
        else:
            print("Could not extract valid JSON from Gemini response")
            print(f"Raw response: {response_text}")
            return news_data[:top_n]
    except Exception as e:
        print(f"Error during Gemini article selection: {e}")
        return news_data[:top_n]

def download_image(image_url, save_path):
    """Downloads an image from a URL and saves it as a JPG, with retries on failure."""
    max_retries = 2  # Number of retries
    attempt = 0
    while attempt <= max_retries:
        try:
            response = requests.get(image_url, stream=True, timeout=15)
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content))
                image = image.convert("RGB")
                image.save(save_path, "JPEG")
                print(f"Downloaded image: {save_path}")
                return  # Success, exit function
            else:
                print(f"Attempt {attempt+1}: Failed to download image (status {response.status_code}): {image_url}")
        except Exception as e:
            print(f"Attempt {attempt+1}: Error downloading image: {image_url} - {e}")
        attempt += 1
        if attempt <= max_retries:
            print("Retrying in 2 seconds...")
            time.sleep(2)
    print(f"Failed to download image after {max_retries + 1} attempts: {image_url}")

def generate_summary_with_gemini(article_title, article_content):
    """
    Uses Gemini to generate a detailed summary of the article content.
    The prompt instructs Gemini to generate a summary in 3-5 sentences (each on a new line),
    inserting periods only at true sentence breaks and preserving abbreviations.
    
    If an error is detected during summarization, the function will choose an alternative key
    (from indices 0 to 2, excluding the current key) and retry up to 3 times.
    """
    prompt = f"""
Please summarize the following article content for a presentation slide.
Article Title: "{article_title}"
Instructions:
1. Provide a concise, informative summary in 3-5 sentences. Each sentence should start on a new line.
2. Insert a period (".") only at the true end of each sentence (or when a new line is needed), and do not insert extra periods within abbreviations (e.g., "a.m.", "p.m.", "U.K.", "U.S.", etc.).
3. Also provide one short key takeaway that captures the main point.
4. Optionally, suggest an improved title if needed.

Article Content:
{article_content[:10000]}

Return your answer strictly as a JSON object with the following keys:
{{
    "summary": "Your summary here, with each sentence on a new line and periods only at sentence breaks.",
    "key_takeaway": "Your key takeaway here, with abbreviations intact.",
    "title": "Your suggested title (or repeat the original if no change is needed)"
}}

Return only the JSON object without any additional text.
"""
    max_attempts = 3
    attempt = 0
    tried_keys = set()
    while attempt < max_attempts:
        try:
            current_key = get_next_gemini_key()
            # Ensure we choose a key from the first 3 keys (indices 0-2) that isn't already tried
            if current_key in tried_keys:
                alternatives = [k for idx, k in enumerate(gemini_keys[:3]) if k not in tried_keys]
                if alternatives:
                    current_key = random.choice(alternatives)
            tried_keys.add(current_key)
            genai.configure(api_key=current_key)
            model = genai.GenerativeModel('gemini-1.5-pro')
            response = model.generate_content(prompt)
            response_text = response.text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                summary_data = json.loads(json_str)
                # Check if the summary indicates an error (you can customize this condition)
                if summary_data.get("summary", "").strip().lower().startswith("error"):
                    print(f"Attempt {attempt+1}: Gemini returned an error summary for '{article_title}'")
                    attempt += 1
                    continue
                return summary_data
            else:
                print(f"Attempt {attempt+1}: Could not extract valid JSON from Gemini response for '{article_title}'")
                attempt += 1
        except Exception as e:
            print(f"Attempt {attempt+1}: Error during Gemini summarization for '{article_title}': {e}")
            attempt += 1
    return {"summary": "Error in summary generation", "key_takeaway": "Error", "title": article_title}

def main():
    print("Step 1: Fetching news articles from GNews API...")
    news_data = fetch_news_from_gnews()
    if not news_data:
        print("No articles fetched. Exiting.")
        return

    # Save all fetched articles to all_news.json
    print("Saving all fetched articles to all_news.json")
    with open(os.path.join(SAVE_DIR, "all_news.json"), "w", encoding="utf-8") as f:
        json.dump(news_data, f, indent=2)

    # Step 2: Use Gemini to select the top 10 articles from the fetched 10 (or fewer)
    print("\nStep 2: Selecting the top 10 articles using Gemini...")
    selected_articles = select_top_articles_with_gemini(news_data, top_n=10)

    final_articles = []
    # Process each selected article
    for i, article in enumerate(selected_articles):
        title = article["title"]
        content = article.get("content", "")
        url = article["link"]
        image_url = article.get("image")

        print(f"\nProcessing selected article {i+1}: {title}")

        # Generate summary using Gemini
        gemini_summary = generate_summary_with_gemini(title, content)
        summary_text = gemini_summary.get("summary", "No summary available")
        key_takeaway = gemini_summary.get("key_takeaway", "No key takeaway available")
        new_title = gemini_summary.get("title", title)

        # Download the article image using the image link from GNews
        image_save_path = os.path.join(SAVE_DIR, f"image_{i}.jpg")
        if image_url:
            download_image(image_url, image_save_path)
        else:
            print(f"No image URL provided for article {i+1}: {title}")

        final_article = {
            "title": new_title,
            "summary": summary_text,
            "key_takeaway": key_takeaway,
            "original_title": title,
            "source": article["source"],
            "link": url,
            "image": image_save_path  # Local path for ppt.py
        }
        final_articles.append(final_article)
        time.sleep(1)

    # Save the final processed articles for ppt.py
    with open(os.path.join(SAVE_DIR, "final_news.json"), "w", encoding="utf-8") as f:
        json.dump(final_articles, f, indent=2)

    print(f"\nProcess complete! Saved {len(final_articles)} processed articles to {os.path.join(SAVE_DIR, 'final_news.json')}")
    return final_articles

if __name__ == "__main__":
    main()
