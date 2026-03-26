import yt_dlp
import requests
import os
import time

# ==========================================
# 1. CONFIGURATION
# ==========================================
BUNNY_STORAGE_ZONE = "your-storage-zone-name"
BUNNY_API_KEY = "your-storage-zone-password"
BUNNY_REGION = "" # e.g., "ny.", "sg.", or leave blank

DOWNLOAD_DIR = "downloads"
DELAY_SECONDS = 10 # IMPORTANT: Keep a delay so YouTube doesn't block your VPS IP

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ==========================================
# 2. BUNNY.NET UPLOADER
# ==========================================
def upload_to_bunny(file_path):
    filename = os.path.basename(file_path)
    url = f"https://{BUNNY_REGION}storage.bunnycdn.com/{BUNNY_STORAGE_ZONE}/{filename}"
    headers = {
        "AccessKey": BUNNY_API_KEY,
        "Content-Type": "application/octet-stream"
    }
    
    print(f"☁️  Uploading '{filename}' to Bunny.net...")
    try:
        with open(file_path, 'rb') as file_data:
            response = requests.put(url, headers=headers, data=file_data)
        if response.status_code == 201:
            print("✅ Successfully uploaded to Bunny.net!")
            return True
        else:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

# ==========================================
# 3. MAIN BULK PROCESSOR
# ==========================================
def process_bulk_target(target_url):
    print(f"\n🔍 Scanning target: {target_url}...")
    print("⏳ This might take a moment for large channels or playlists...\n")
    
    # 1. Extract all URLs without downloading
    extract_opts = {'extract_flat': True, 'quiet': True}
    video_urls = []
    
    with yt_dlp.YoutubeDL(extract_opts) as ydl:
        info = ydl.extract_info(target_url, download=False)
        
        if 'entries' in info:
            for entry in info['entries']:
                if entry and entry.get('url'):
                    video_urls.append(entry['url'])
            print(f"✅ Found {len(video_urls)} videos to process.")
        else:
            video_urls.append(info.get('url') or info.get('webpage_url'))
            print("✅ Found 1 video.")

    # 2. Download Settings
    ydl_opts = {
        'format': 'bestaudio/best',        
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',            
        'writethumbnail': True,            
        'postprocessors': [
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'},
            {'key': 'FFmpegMetadata', 'add_metadata': True, 'add_chapters': True},
            {'key': 'EmbedThumbnail'}
        ],
        'prefer_ffmpeg': True,
        # 'cookiefile': 'cookies.txt', # <-- UNCOMMENT THIS IF YOUTUBE BLOCKS YOUR VPS IP
        'ignoreerrors': True, # Skips deleted/private videos instead of crashing the script
    }

    # 3. Process the loop
    print("\n🚀 Starting bulk operations...\n")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for index, url in enumerate(video_urls):
            print(f"\n--- [File {index + 1} of {len(video_urls)}] ---")
            
            try:
                dl_info = ydl.extract_info(url, download=True)
                
                # If ignoreerrors is True, dl_info might be None for skipped videos
                if dl_info is None:
                    continue
                    
                if 'requested_downloads' in dl_info:
                    final_path = dl_info['requested_downloads'][0]['filepath']
                else:
                    final_path = os.path.splitext(ydl.prepare_filename(dl_info))[0] + '.mp3'
                
                # Upload and Clean up
                if upload_to_bunny(final_path):
                    os.remove(final_path)
                    print(f"🗑️  Cleaned up local file: {final_path}")
                else:
                    print(f"⚠️  Kept local file due to upload failure: {final_path}")
                    
            except Exception as e:
                print(f"❌ Failed to process {url}: {e}")
            
            # Rate limit delay
            if index < len(video_urls) - 1:
                print(f"⏳ Waiting {DELAY_SECONDS} seconds before the next download...")
                time.sleep(DELAY_SECONDS)

if __name__ == "__main__":
    target = input("Enter the YouTube Channel, Playlist, or Video URL: ")
    process_bulk_target(target.strip())
    print("\n🎉 Bulk processing complete!")
