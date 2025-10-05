import requests
import re

def extract_video_id(url):
    """Extract video ID from TikTok URL"""
    patterns = [
        r'/video/(\d+)',
        r'vm\.tiktok\.com/([a-zA-Z0-9]+)',
        r'vt\.tiktok\.com/([a-zA-Z0-9]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_tik_info(tik):
    url = f"https://api.tiktokv.com/aweme/v1/aweme/detail/?aweme_id={tik}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if 'aweme_detail' in data:
            aweme_detail = data['aweme_detail']
            video_url = aweme_detail['video']['play_addr']['url_list'][0]
            description = aweme_detail['desc']
            author_name = aweme_detail['author']['nickname']
            return {
                "video_url": video_url,
                "description": description,
                "author_name": author_name
            }
        else:
            return {"error": "Invalid TikTok ID or video not found."}
    else:
        return {"error": f"Failed to fetch data, status code: {response.status_code}"}
    
def download_tiktok_video_no_watermark():
    url = input("Enter TikTok video URL: ").strip()
    
    # Validate that it's a TikTok URL
    if "tiktok.com" not in url:
        print("❌ Please enter a valid TikTok URL (must contain 'tiktok.com')")
        return
    
    # List of alternative APIs to try
    apis = [
        f"https://api.tikwm.com/v1/video/info?url={url}",
        f"https://api.tiktokv.com/v1/download?url={url}",
        f"https://tikdownload.org/api/v1/download?url={url}"
    ]
    
    for i, api_url in enumerate(apis, 1):
        try:
            print(f"Trying API {i}...")
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"API {i} response received successfully")
                
                # Try different response formats from different APIs
                video_url = None
                if 'data' in data and 'url' in data['data']:
                    video_url = data['data']['url']
                elif 'data' in data and 'play' in data['data']:
                    video_url = data['data']['play']
                elif 'video_url' in data:
                    video_url = data['video_url']
                elif 'download_url' in data:
                    video_url = data['download_url']
                
                if video_url:
                    print("Video URL (No Watermark):", video_url)
                    
                    try:
                        with open("tiktok_video.mp4", "wb") as file:
                            video_response = requests.get(video_url, timeout=30)
                            file.write(video_response.content)
                        print("Video downloaded successfully as tiktok_video.mp4")
                        return
                    except Exception as download_error:
                        print(f"Failed to download video: {download_error}")
                        continue
                else:
                    print(f"API {i}: Video URL not found in response")
                    continue
            else:
                print(f"API {i}: HTTP Error {response.status_code}")
                continue
                
        except requests.exceptions.ConnectionError as e:
            print(f"API {i}: Connection failed - {e}")
            continue
        except requests.exceptions.Timeout:
            print(f"API {i}: Request timed out")
            continue
        except requests.exceptions.RequestException as e:
            print(f"API {i}: Request failed - {e}")
            continue
        except Exception as e:
            print(f"API {i}: Unexpected error - {e}")
            continue
    
    print("\n❌ All APIs failed. This could be due to:")
    print("1. Network connectivity issues")
    print("2. TikTok URL format not supported")
    print("3. APIs are temporarily down")
    print("4. Video may be private or restricted")
    print("\n💡 Alternative solutions:")
    print("- Try using online TikTok downloaders in your browser")
    print("- Use browser extensions for downloading TikTok videos")
    print("- Try different TikTok downloader tools")

if __name__ == "__main__":
    print("🎵 TikTok Video Tool 🎵")
    print("1. Get TikTok video info")
    print("2. Download TikTok video (no watermark)")
    
    choice = input("Choose an option (1 or 2): ").strip()
    
    if choice == "1":
        url_or_id = input("Enter TikTok video URL or ID: ").strip()
        
        # Try to extract ID from URL if it's a URL
        if "tiktok.com" in url_or_id:
            video_id = extract_video_id(url_or_id)
            if video_id:
                print(f"Extracted video ID: {video_id}")
                info = get_tik_info(video_id)
            else:
                print("Could not extract video ID from URL")
                info = {"error": "Invalid URL format"}
        else:
            # Assume it's already a video ID
            info = get_tik_info(url_or_id)
        
        print("\n📊 Video Info:")
        for key, value in info.items():
            print(f"{key}: {value}")
            
    elif choice == "2":
        download_tiktok_video_no_watermark()
    else:
        print("❌ Invalid choice. Please run the script again and choose 1 or 2.")