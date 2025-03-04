from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import shutil
import time
import threading

PPT_FILE = "final_presentation.pptx"
FOLDER_ID = "13RdnPfkku4aZDP6pm822E0JKy6DKtllR"

def authenticate_drive():
    # Scopes for Google Drive API
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    # Load the service account credentials
    credentials = service_account.Credentials.from_service_account_file(
        'service_credentials.json', 
        scopes=SCOPES
    )
    
    # Build and return the Drive service
    return build('drive', 'v3', credentials=credentials)

def upload_to_drive():
    # Authenticate and get Drive service
    service = authenticate_drive()
    
    # Check if file exists
    if not os.path.exists(PPT_FILE):
        return None, "Presentation file not found."
    
    print("Uploading to Google Drive...")
    
    # Prepare file metadata and media
    file_metadata = {
        'name': PPT_FILE,
        'parents': [FOLDER_ID]
    }
    media = MediaFileUpload(
        PPT_FILE, 
        mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
    )
    
    # Upload file
    file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id'
    ).execute()
    
    # Make file publicly accessible
    service.permissions().create(
        fileId=file['id'],
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()
    
    # Generate Google Slides link
    slides_link = f"https://docs.google.com/presentation/d/{file['id']}"
    
    print(f"Uploaded! Link: {slides_link}")
    
    # Auto-delete after 5 minutes (in a separate thread)
    def delete_after_delay(service, file_id, delay=300):
        time.sleep(delay)
        service.files().delete(fileId=file_id).execute()
        print("Deleted file from Drive.")
    
    threading.Thread(
        target=delete_after_delay, 
        args=(service, file['id'])
    ).start()
    
    return slides_link, None

if __name__ == "__main__":
    try:
        link, error = upload_to_drive()
        if error:
            print("Error:", error)
        else:
            print("Google Slides Link:", link)
            # if os.path.exists(PPT_FILE):
            #     shutil.rmtree(PPT_FILE)
    except Exception as e:
        print(f"Unhandled error: {e}")