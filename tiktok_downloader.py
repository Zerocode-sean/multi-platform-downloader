import requests
import re
import os
from urllib.parse import quote
import threading

try:
    import yt_dlp
except ImportError:  # Lazy import notice
    yt_dlp = None

DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
if not os.path.isdir(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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

def test_connection():
    """Test internet connection"""
    try:
        response = requests.get("https://www.google.com", timeout=5)
        return response.status_code == 200
    except:
        return False

def download_tiktok_video():
    """Download TikTok video with improved error handling"""
    
    # Check internet connection first
    if not test_connection():
        print("❌ No internet connection detected. Please check your network.")
        return
    
    url = input("Enter TikTok video URL: ").strip()
    
    # Validate URL
    if not url or "tiktok.com" not in url:
        print("❌ Please enter a valid TikTok URL")
        return
    
    print(f"🔍 Processing URL: {url}")
    
    # Try multiple APIs with different approaches
    success = False
    
    # Method 1: Try tikwm API
    try:
        print("📡 Trying TikWM API...")
        api_url = f"https://www.tikwm.com/api/?url={quote(url)}"
        response = requests.get(api_url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 0 and 'data' in data:
                video_data = data['data']
                if 'play' in video_data:
                    video_url = video_data['play']
                    title = video_data.get('title', 'tiktok_video')
                    
                    print(f"✅ Video found: {title}")
                    success = download_video_file(video_url, title)
                    if success:
                        return
        
        print("❌ TikWM API failed")
    except Exception as e:
        print(f"❌ TikWM API error: {str(e)}")
    
    # Method 2: Alternative approach
    try:
        print("📡 Trying alternative method...")
        # This is a placeholder for other methods
        print("❌ Alternative methods not available")
    except Exception as e:
        print(f"❌ Alternative method error: {str(e)}")
    
    if not success:
        print("\n❌ Download failed. Possible reasons:")
        print("• The video might be private or restricted")
        print("• TikTok has updated their API")
        print("• Network or firewall blocking the request")
        print("• The downloader services are temporarily down")
        print("\n💡 Try these alternatives:")
        print("• Use online TikTok downloaders (ssstik.io, tikmate.online)")
        print("• Use browser extensions")
        print("• Try different TikTok downloader apps")

def download_video_file(video_url, title):
    """Download the actual video file"""
    try:
        print("⬇️ Downloading video...")
        response = requests.get(video_url, timeout=30, stream=True)
        
        if response.status_code == 200:
            # Clean filename
            filename = re.sub(r'[<>:"/\\|?*]', '', title)[:50] + '.mp4'
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r📥 Progress: {percent:.1f}%", end='', flush=True)
            
            print(f"\n✅ Video downloaded successfully: {filename}")
            print(f"📂 File size: {os.path.getsize(filename) / (1024*1024):.1f} MB")
            return True
        else:
            print(f"❌ Failed to download video (HTTP {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ Download error: {str(e)}")
        return False

def get_video_info():
    """Get TikTok video information"""
    url_or_id = input("Enter TikTok video URL or ID: ").strip()
    
    if "tiktok.com" in url_or_id:
        video_id = extract_video_id(url_or_id)
        if video_id:
            print(f"📝 Extracted video ID: {video_id}")
        else:
            print("❌ Could not extract video ID from URL")
            return
    else:
        video_id = url_or_id
    
    print("ℹ️ Note: Video info feature requires TikTok's official API access")
    print("This is typically restricted. Consider using the download feature instead.")

def ensure_yt_dlp():
    if yt_dlp is None:
        print("❌ Missing dependency: yt-dlp")
        print("➡ Install with: pip install yt-dlp")
        return False
    return True

def sanitize_filename(name: str, ext: str):
    cleaned = re.sub(r'[<>:"/\\|?*]', '', name).strip() or 'output'
    return (cleaned[:60] + ext)

def ytdlp_progress_hook(d):
    if d.get('status') == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
        downloaded = d.get('downloaded_bytes', 0)
        if total:
            percent = downloaded / total * 100
            print(f"\r📥 Progress: {percent:5.1f}%", end='', flush=True)
    elif d.get('status') == 'finished':
        print("\n✅ Download finished. Processing...")

def download_youtube():
    if not ensure_yt_dlp():
        return
    if not test_connection():
        print("❌ No internet connection.")
        return
    url = input("Enter YouTube video/playlist URL: ").strip()
    if not url or not any(k in url for k in ["youtube.com", "youtu.be"]):
        print("❌ Invalid YouTube URL.")
        return
    print("Select format:\n 1. Best video+audio (mp4)\n 2. Audio only (mp3)")
    choice = input("Choose (1/2): ").strip()
    is_audio = (choice == '2')
    out_tmpl = os.path.join(DOWNLOAD_DIR, '%(title).60s.%(ext)s')
    ydl_opts = {
        'outtmpl': out_tmpl,
        'progress_hooks': [ytdlp_progress_hook],
        'restrictfilenames': False,
        'ignoreerrors': True,
        'nopart': True,
        'noprogress': False,
        'quiet': True,
        'no_warnings': True,
    }
    if is_audio:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}
            ]
        })
    else:
        ydl_opts.update({'format': 'bv*+ba/best'})
    try:
        print("🚀 Starting YouTube download...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        if info:
            if isinstance(info, dict) and info.get('_type') == 'playlist':
                print(f"✅ Playlist processed. Items: {len(info.get('entries') or [])}")
            else:
                print("✅ Download complete.")
        else:
            print("❌ Nothing downloaded.")
    except Exception as e:
        print(f"❌ YouTube download failed: {e}")


def download_instagram():
    if not ensure_yt_dlp():
        return
    if not test_connection():
        print("❌ No internet connection.")
        return
    url = input("Enter Instagram post/reel URL: ").strip()
    if not url or "instagram.com" not in url:
        print("❌ Invalid Instagram URL.")
        return
    print("ℹ️ Public content only. Private / login-required media will fail.")
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title).60s.%(ext)s'),
        'progress_hooks': [ytdlp_progress_hook],
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'nocheckcertificate': True,
        'format': 'mp4/best'
    }
    try:
        print("🚀 Starting Instagram download...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        if info:
            print("✅ Instagram media downloaded.")
        else:
            print("❌ Download failed.")
    except Exception as e:
        print(f"❌ Instagram download failed: {e}")

# GUI SUPPORT

def launch_gui():
    """Launch a Tkinter based GUI for multi-platform downloading."""
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        print("❌ Tkinter not available. Install/enable it to use the GUI.")
        return
    if not os.path.isdir(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    root = tk.Tk()
    root.title("Multi Platform Downloader")
    root.geometry("760x540")

    style = ttk.Style()
    try:
        style.theme_use('clam')
    except Exception:
        pass

    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True, padx=6, pady=6)

    # Shared log widget
    def make_log(parent):
        text = tk.Text(parent, height=12, wrap='word', bg='#1e1e1e', fg='#dcdcdc')
        text.configure(font=('Consolas', 9))
        text.pack(fill='both', expand=True, padx=4, pady=4)
        return text

    def append(log_widget, msg):
        log_widget.after(0, lambda: (log_widget.insert('end', msg + '\n'), log_widget.see('end')))

    # ---- TikTok TAB ----
    tiktok_frame = ttk.Frame(notebook)
    notebook.add(tiktok_frame, text='TikTok')

    tk.Label(tiktok_frame, text="TikTok Video URL:").pack(anchor='w', padx=6, pady=(6,2))
    tiktok_url_var = tk.StringVar()
    tk.Entry(tiktok_frame, textvariable=tiktok_url_var, width=90).pack(anchor='w', padx=6)
    tiktok_status = tk.StringVar(value='Idle')
    tk.Label(tiktok_frame, textvariable=tiktok_status, foreground='#888').pack(anchor='w', padx=6, pady=4)
    tiktok_log = make_log(tiktok_frame)

    def tiktok_worker(url):
        append(tiktok_log, f"▶ Starting TikTok download: {url}")
        # Reuse existing logic but adapted
        if not url or 'tiktok.com' not in url:
            append(tiktok_log, '❌ Invalid TikTok URL')
            tiktok_status.set('Error')
            return
        api_url = f"https://www.tikwm.com/api/?url={quote(url)}"
        try:
            r = requests.get(api_url, timeout=15)
            if r.status_code == 200:
                j = r.json()
                data = j.get('data') or {}
                play = data.get('play')
                title = data.get('title','tiktok_video')
                if play:
                    append(tiktok_log, f"✅ Found: {title}")
                    ok = download_video_file(play, title)
                    if ok:
                        append(tiktok_log, '✅ Download complete')
                        tiktok_status.set('Done')
                        return
                append(tiktok_log, '❌ Video URL not in response')
            else:
                append(tiktok_log, f"❌ HTTP {r.status_code}")
        except Exception as e:
            append(tiktok_log, f"❌ Error: {e}")
        tiktok_status.set('Failed')

    def start_tiktok():
        if not test_connection():
            messagebox.showerror('Network', 'No internet connection.')
            return
        tiktok_status.set('Working...')
        threading.Thread(target=tiktok_worker, args=(tiktok_url_var.get().strip(),), daemon=True).start()

    ttk.Button(tiktok_frame, text='Download TikTok', command=start_tiktok).pack(padx=6, pady=6, anchor='w')

    # ---- YouTube TAB ----
    youtube_frame = ttk.Frame(notebook)
    notebook.add(youtube_frame, text='YouTube')

    yt_url_var = tk.StringVar()
    tk.Label(youtube_frame, text="YouTube URL (video / playlist):").pack(anchor='w', padx=6, pady=(6,2))
    tk.Entry(youtube_frame, textvariable=yt_url_var, width=90).pack(anchor='w', padx=6)

    tk.Label(youtube_frame, text="Format:").pack(anchor='w', padx=6, pady=(6,2))
    yt_format_var = tk.StringVar(value='Best (<=1080p)')
    yt_formats = ['Best (<=1080p)', '720p', 'Audio MP3']
    ttk.Combobox(youtube_frame, values=yt_formats, textvariable=yt_format_var, state='readonly', width=20).pack(anchor='w', padx=6)

    yt_status = tk.StringVar(value='Idle')
    tk.Label(youtube_frame, textvariable=yt_status, foreground='#888').pack(anchor='w', padx=6, pady=4)
    yt_log = make_log(youtube_frame)

    def youtube_worker(url, fmt_choice):
        append(yt_log, f"▶ Starting YouTube download: {url}")
        if not ensure_yt_dlp():
            append(yt_log, '❌ yt-dlp not installed')
            yt_status.set('Missing yt-dlp')
            return
        if not url or not any(k in url for k in ['youtube.com','youtu.be']):
            append(yt_log, '❌ Invalid YouTube URL')
            yt_status.set('Error')
            return
        import yt_dlp
        out_tmpl = os.path.join(DOWNLOAD_DIR, '%(title).60s.%(ext)s')
        base_opts = {
            'outtmpl': out_tmpl,
            'progress_hooks': [lambda d: yt_progress(d)],
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'restrictfilenames': False,
            'noprogress': False,
        }
        if fmt_choice.startswith('Best'):
            base_opts['format'] = 'bv*[height<=1080]+ba/best[height<=1080]'
        elif fmt_choice == '720p':
            base_opts['format'] = 'bv*[height<=720]+ba/best[height<=720]'
        else:  # Audio MP3
            base_opts['format'] = 'bestaudio/best'
            base_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'
            }]
        try:
            with yt_dlp.YoutubeDL(base_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            if info:
                if isinstance(info, dict) and info.get('_type') == 'playlist':
                    append(yt_log, f"✅ Playlist processed. Items: {len(info.get('entries') or [])}")
                else:
                    append(yt_log, '✅ Download complete')
                yt_status.set('Done')
            else:
                append(yt_log, '❌ Nothing downloaded')
                yt_status.set('Failed')
        except Exception as e:
            append(yt_log, f"❌ Error: {e}")
            yt_status.set('Failed')

    def yt_progress(d):
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            done = d.get('downloaded_bytes', 0)
            pct = (done/total*100) if total else 0
            yt_status.set(f'Downloading {pct:4.1f}%')
        elif d.get('status') == 'finished':
            yt_status.set('Processing...')

    def start_youtube():
        if not test_connection():
            messagebox.showerror('Network', 'No internet connection.')
            return
        yt_status.set('Starting...')
        threading.Thread(target=youtube_worker, args=(yt_url_var.get().strip(), yt_format_var.get()), daemon=True).start()

    ttk.Button(youtube_frame, text='Download YouTube', command=start_youtube).pack(anchor='w', padx=6, pady=6)

    # ---- Instagram TAB ----
    insta_frame = ttk.Frame(notebook)
    notebook.add(insta_frame, text='Instagram')

    insta_url_var = tk.StringVar()
    tk.Label(insta_frame, text="Instagram Reel/Post URL:").pack(anchor='w', padx=6, pady=(6,2))
    tk.Entry(insta_frame, textvariable=insta_url_var, width=90).pack(anchor='w', padx=6)
    insta_status = tk.StringVar(value='Idle')
    tk.Label(insta_frame, textvariable=insta_status, foreground='#888').pack(anchor='w', padx=6, pady=4)
    insta_log = make_log(insta_frame)

    def insta_worker(url):
        append(insta_log, f"▶ Starting Instagram download: {url}")
        if not ensure_yt_dlp():
            append(insta_log, '❌ yt-dlp not installed')
            insta_status.set('Missing yt-dlp')
            return
        if 'instagram.com' not in url:
            append(insta_log, '❌ Invalid Instagram URL')
            insta_status.set('Error')
            return
        import yt_dlp
        opts = {
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title).60s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'progress_hooks': [lambda d: insta_progress(d)],
            'format': 'mp4/best'
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            if info:
                append(insta_log, '✅ Download complete')
                insta_status.set('Done')
            else:
                append(insta_log, '❌ Nothing downloaded')
                insta_status.set('Failed')
        except Exception as e:
            append(insta_log, f"❌ Error: {e}")
            insta_status.set('Failed')

    def insta_progress(d):
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            done = d.get('downloaded_bytes', 0)
            pct = (done/total*100) if total else 0
            insta_status.set(f'Downloading {pct:4.1f}%')
        elif d.get('status') == 'finished':
            insta_status.set('Processing...')

    def start_insta():
        if not test_connection():
            messagebox.showerror('Network', 'No internet connection.')
            return
        insta_status.set('Starting...')
        threading.Thread(target=insta_worker, args=(insta_url_var.get().strip(),), daemon=True).start()

    ttk.Button(insta_frame, text='Download Instagram', command=start_insta).pack(anchor='w', padx=6, pady=6)

    # ---- About TAB ----
    about = ttk.Frame(notebook)
    notebook.add(about, text='About')
    tk.Label(about, text="Multi Platform Downloader", font=('Segoe UI', 14, 'bold')).pack(pady=10)
    tk.Label(about, text="Supports: TikTok, YouTube (video/audio), Instagram", justify='center').pack()
    tk.Label(about, text="Downloads saved to: \n" + DOWNLOAD_DIR, justify='center', fg='#4caf50').pack(pady=8)
    tk.Label(about, text="yt-dlp required for YouTube/Instagram.").pack(pady=4)

    root.mainloop()

# Extend existing main menu to include GUI option

def main():
    print("🎬 Multi Platform Downloader")
    print("=" * 34)
    print("1. Download TikTok video")
    print("2. Download YouTube (video/audio)")
    print("3. Download Instagram media")
    print("4. Get TikTok video info (limited)")
    print("5. Exit")
    print("6. Launch GUI")
    
    while True:
        choice = input("\n👉 Choose an option (1-6): ").strip()
        if choice == '1':
            download_tiktok_video()
            break
        elif choice == '2':
            download_youtube()
            break
        elif choice == '3':
            download_instagram()
            break
        elif choice == '4':
            get_video_info()
            break
        elif choice == '5':
            print("👋 Goodbye!")
            break
        elif choice == '6':
            launch_gui()
            break
        else:
            print("❌ Invalid choice. Enter 1-6.")

if __name__ == "__main__":
    main()
