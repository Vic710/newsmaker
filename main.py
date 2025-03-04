import os
import shutil
from news import main as news_main
from ppt import main as ppt_main

PPT_FILE = "final_presentation.pptx"
NEWS_FOLDER = "news_files"  # Assuming this folder stores fetched articles

def run_pipeline():
    print("Starting full pipeline...")

    # Step 1: Fetch and process news articles.
    news_articles = news_main()
    if not news_articles:
        print("No news articles were processed.")
        return None

    # Step 2: Build the PowerPoint presentation using processed articles.
    ppt_file = ppt_main()
    print(f"Pipeline complete. Generated presentation: {ppt_file}")

    # Step 3: Delete the news files folder
    if os.path.exists(NEWS_FOLDER):
        shutil.rmtree(NEWS_FOLDER)  # Delete the entire folder
        print(f"Deleted {NEWS_FOLDER} folder.")

    # Step 4: Delete the PPT file after uploading (handled in drive_upload.py)
    
    return ppt_file

if __name__ == "__main__":
    run_pipeline()
