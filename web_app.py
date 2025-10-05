import os
import re
import asyncio
import threading
import uuid
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

app = FastAPI(title="Multi Platform Downloader")
BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

YOUTUBE_RE = re.compile(r"(youtu.be/|youtube.com)")
TIKTOK_RE = re.compile(r"tiktok.com")
INSTAGRAM_RE = re.compile(r"instagram.com")

# -------- Utility ---------

def get_basic_headers():
    return {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}

# -------- Extract preview metadata ---------
async def get_tiktok_preview(url: str) -> Optional[dict]:
    try:
        api = f"https://www.tikwm.com/api/?url={url}"
        r = requests.get(api, headers=get_basic_headers(), timeout=12)
        if r.status_code == 200:
            j = r.json()
            if j.get('code') == 0:
                d = j.get('data', {})
                # Duration may be provided as 'duration'
                return {
                    'title': d.get('title') or 'TikTok Video',
                    'thumbnail': d.get('cover') or d.get('origin_cover'),
                    'preview_url': d.get('play'),
                    'embed_url': None,
                    'video_type': 'video',
                    'platform': 'tiktok',
                    'duration': d.get('duration'),
                    'filesize': d.get('size') or d.get('download_addr_size')
                }
    except Exception:
        pass
    return None

# Enhance YouTube info to support iframe embed fallback and pick a progressive preview URL
async def get_ytdlp_info(url: str) -> Optional[dict]:
    if yt_dlp is None:
        return None
    loop = asyncio.get_event_loop()
    def extract():
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception:
            return None
    info = await loop.run_in_executor(None, extract)
    if not info:
        return None
    if info.get('_type') == 'playlist':
        first = next((e for e in info.get('entries') or [] if e), None)
        base = first or {}
    else:
        base = info
    video_id = base.get('id')
    # Always force iframe for reliability (CORS / signature / adaptive issues)
    progressive_url = None
    thumb = base.get('thumbnail')
    if not thumb and base.get('thumbnails'):
        try:
            thumb = sorted([t for t in base['thumbnails'] if isinstance(t, dict)], key=lambda x: x.get('width', 0), reverse=True)[0].get('url')
        except Exception:
            thumb = None
    duration = base.get('duration')
    filesize = base.get('filesize') or base.get('filesize_approx')
    return {
        'title': base.get('title') or 'Video',
        'thumbnail': thumb,
        'preview_url': progressive_url,
        'embed_url': f"https://www.youtube.com/embed/{video_id}" if video_id else None,
        'video_type': 'iframe',
        'platform': 'youtube',
        'duration': duration,
        'filesize': filesize
    }

async def get_instagram_info(url: str) -> Optional[dict]:
    return await get_ytdlp_info(url)

async def detect_and_preview(url: str) -> Optional[dict]:
    if TIKTOK_RE.search(url):
        return await get_tiktok_preview(url)
    if YOUTUBE_RE.search(url) or INSTAGRAM_RE.search(url):
        return await get_ytdlp_info(url)
    return None

# -------- Routes ---------
@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('index.html', {"request": request, 'preview': None, 'url': ''})

@app.post('/preview', response_class=HTMLResponse)
async def preview(request: Request, url: str = Form(...)):
    meta = await detect_and_preview(url.strip())
    return templates.TemplateResponse('index.html', {"request": request, 'preview': meta, 'url': url.strip()})

@app.post('/download')
async def download(request: Request, url: str = Form(...), format: str = Form('best')):
    url = url.strip()
    if not url:
        return HTMLResponse("<h3>Invalid URL</h3>", status_code=400)

    platform = 'generic'
    if TIKTOK_RE.search(url):
        platform = 'tiktok'
    elif YOUTUBE_RE.search(url):
        platform = 'youtube'
    elif INSTAGRAM_RE.search(url):
        platform = 'instagram'

    filename_base = re.sub(r'[^a-zA-Z0-9_-]+', '_', url)[:40] or 'video'
    temp_path = DOWNLOAD_DIR / f"{filename_base}.temp"

    if TIKTOK_RE.search(url):
        meta = await get_tiktok_preview(url)
        if not meta or not meta.get('preview_url'):
            return HTMLResponse("<h3>Failed to fetch TikTok video.</h3>", status_code=502)
        video_url = meta['preview_url']
        try:
            r = requests.get(video_url, stream=True, headers=get_basic_headers(), timeout=20)
        except Exception:
            return HTMLResponse("<h3>Upstream TikTok stream error.</h3>", status_code=502)
        if r.status_code != 200:
            return HTMLResponse(f"<h3>TikTok stream HTTP {r.status_code}</h3>", status_code=502)
        def tstream():
            with open(temp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        yield chunk
            final_path = DOWNLOAD_DIR / f"{filename_base}.mp4"
            os.replace(temp_path, final_path)
        return StreamingResponse(
            tstream(),
            media_type='video/mp4',
            headers={'Content-Disposition': f'attachment; filename="{filename_base}.mp4"'
        })

    if yt_dlp is None:
        return HTMLResponse("<h3>yt-dlp not installed on server.</h3>", status_code=500)

    quality_map = {
        'best': 'bv*[height<=1080]+ba/best[height<=1080]',
        '720p': 'bv*[height<=720]+ba/best[height<=720]',
        'audio': 'bestaudio/best'
    }
    ydl_opts = {
        'format': quality_map.get(format, 'best'),
        'quiet': True,
        'no_warnings': True,
        'outtmpl': str(DOWNLOAD_DIR / f"{filename_base}.%(ext)s"),
    }
    if format == 'audio':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'
        }]

    loop = asyncio.get_event_loop()
    def run_download():
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
            # Detect produced file
            for ext in ['mp4','mkv','webm','mp3','m4a','wav']:
                p = DOWNLOAD_DIR / f"{filename_base}.{ext}"
                if p.exists():
                    return p, ext
        except Exception:
            return None, None
        return None, None

    file_path, ext = await loop.run_in_executor(None, run_download)
    if not file_path:
        return HTMLResponse("<h3>Download failed.</h3>", status_code=502)

    mime_map = {
        'mp4': 'video/mp4',
        'mkv': 'video/x-matroska',
        'webm': 'video/webm',
        'mp3': 'audio/mpeg',
        'm4a': 'audio/mp4',
        'wav': 'audio/wav'
    }
    media_type = mime_map.get(ext, 'application/octet-stream')

    def file_iter():
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(8192)
                if not data:
                    break
                yield data

    return StreamingResponse(
        file_iter(),
        media_type=media_type,
        headers={'Content-Disposition': f'attachment; filename="{file_path.name}"'}
    )

@app.get('/api/preview')
async def api_preview(url: str):
    meta = await detect_and_preview(url.strip()) if url else None
    ok = meta is not None
    return { 'ok': ok, 'preview': meta }

JOBS: Dict[str, Dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()
# Cancellation helper
def job_canceled(job_id: str) -> bool:
    with JOBS_LOCK:
        j = JOBS.get(job_id)
        return bool(j and j.get('cancel'))
# Utility to safely update job
def update_job(job_id: str, **fields):
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(fields)

# Add helper to detect ffmpeg
FFMPEG_AVAILABLE = shutil.which('ffmpeg') is not None

# Background download runner using yt-dlp
def run_download_job(job_id: str, url: str, fmt: str, filename_base: str):
    job = JOBS.get(job_id)
    if not job:
        return
    if yt_dlp is None:
        update_job(job_id, status='error', error='yt-dlp not installed')
        return

    # Respect cancellation before starting heavy work
    if job_canceled(job_id):
        update_job(job_id, status='canceled', error='Canceled before start')
        return

    # Build format string depending on user choice and ffmpeg availability
    # If ffmpeg missing, force a progressive stream (single file including audio+video)
    progressive_selector = 'best[ext=mp4][acodec!=none][vcodec!=none][height<=720]/best[acodec!=none][vcodec!=none]'  # safer
    quality_map = {
        'best': 'bv*[height<=1080]+ba/best[height<=1080]' if FFMPEG_AVAILABLE else progressive_selector,
        '720p': 'bv*[height<=720]+ba/best[height<=720]' if FFMPEG_AVAILABLE else progressive_selector,
        'audio': 'bestaudio/best'
    }

    outtmpl = str(DOWNLOAD_DIR / f"{filename_base}.%(ext)s")

    def hook(d):
        if job_canceled(job_id):
            raise Exception('Canceled by user')
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes') or 0
            percent = (downloaded / total * 100) if total else None
            update_job(job_id,
                       status='downloading',
                       downloaded=downloaded,
                       total=total,
                       percent=percent,
                       speed=d.get('speed'),
                       eta=d.get('eta'))
        elif d.get('status') == 'finished':
            update_job(job_id, status='processing')

    ydl_opts = {
        'format': quality_map.get(fmt, progressive_selector),
        'quiet': True,
        'no_warnings': True,
        'outtmpl': outtmpl,
        'progress_hooks': [hook],
        'merge_output_format': 'mp4' if FFMPEG_AVAILABLE else None
    }

    # Only add postprocessor if ffmpeg present and audio requested
    if fmt == 'audio':
        if FFMPEG_AVAILABLE:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'
            }]
        else:
            # Try to pick an existing audio format (no conversion)
            ydl_opts['format'] = 'bestaudio[ext=mp3]/bestaudio[ext=m4a]/bestaudio'

    produced_file = None
    produced_ext = None
    primary_error = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
    except Exception as e:
        primary_error = str(e)
        if 'Canceled by user' in primary_error:
            update_job(job_id, status='canceled', error='Canceled')
            return
        update_job(job_id, note='primary_failed', status='retrying')

    preferred_exts = ['mp4', 'mp3', 'm4a', 'webm', 'mkv', 'wav']
    if not primary_error:
        for ext in preferred_exts:
            cand = DOWNLOAD_DIR / f"{filename_base}.{ext}"
            if cand.exists():
                produced_file = cand
                produced_ext = ext
                break
        if not produced_file:
            for p in DOWNLOAD_DIR.glob(f"{filename_base}*"):
                if p.is_file() and p.suffix.replace('.', '') in preferred_exts:
                    produced_file = p
                    produced_ext = p.suffix.replace('.', '')
                    break

    # Fallback attempt only if primary failed or file missing
    if not produced_file:
        if job_canceled(job_id):
            update_job(job_id, status='canceled', error='Canceled')
            return
        fallback_fmt = progressive_selector if fmt != 'audio' else ('bestaudio[ext=mp3]/bestaudio[ext=m4a]/bestaudio')
        fallback_out = str(DOWNLOAD_DIR / f"{filename_base}_fb.%(ext)s")
        fb_opts = {
            'format': fallback_fmt,
            'quiet': True,
            'no_warnings': True,
            'outtmpl': fallback_out,
            'progress_hooks': [hook]
        }
        if fmt == 'audio' and FFMPEG_AVAILABLE:
            fb_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'
            }]
        try:
            with yt_dlp.YoutubeDL(fb_opts) as ydl:
                if job_canceled(job_id):
                    update_job(job_id, status='canceled', error='Canceled')
                    return
                ydl.extract_info(url, download=True)
        except Exception as e2:
            if job_canceled(job_id):
                update_job(job_id, status='canceled', error='Canceled')
                return
            if not primary_error:
                primary_error = str(e2)
        if job_canceled(job_id):
            update_job(job_id, status='canceled', error='Canceled')
            return
        for ext in preferred_exts:
            cand = DOWNLOAD_DIR / f"{filename_base}_fb.{ext}"
            if cand.exists():
                produced_file = cand
                produced_ext = ext
                break

    if job_canceled(job_id):
        update_job(job_id, status='canceled', error='Canceled')
        # Optional cleanup of partials
        for p in DOWNLOAD_DIR.glob(f"{filename_base}*"):
            try:
                p.unlink()
            except Exception:
                pass
        return

    if not produced_file:
        update_job(job_id, status='error', error=primary_error or 'No file produced (progressive format unavailable)')
        return

    size = produced_file.stat().st_size
    update_job(job_id, status='finished', file=str(produced_file), ext=produced_ext, size=size)

@app.post('/api/start_download')
async def api_start_download(url: str = Form(...), format: str = Form('best')):
    url = url.strip()
    if not url:
        return {'ok': False, 'error': 'Empty URL'}
    # Construct filename base using uuid for uniqueness
    safe_base = re.sub(r'[^a-zA-Z0-9_-]+', '_', url)[:30] or 'video'
    job_id = uuid.uuid4().hex
    with JOBS_LOCK:
        JOBS[job_id] = {
            'id': job_id,
            'url': url,
            'format': format,
            'status': 'queued',
            'percent': 0,
            'downloaded': 0,
            'total': None,
            'speed': None,
            'eta': None,
            'file': None,
            'ext': None,
            'size': None,
            'error': None,
            'cancel': False
        }
    threading.Thread(target=run_download_job, args=(job_id, url, format, f"{safe_base}_{job_id[:6]}"), daemon=True).start()
    return {'ok': True, 'job_id': job_id}

@app.get('/api/job/{job_id}')
async def api_job_status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return {'ok': False, 'error': 'Job not found'}
        return {'ok': True, 'job': job}

@app.get('/api/job/{job_id}/file')
async def api_job_file(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job or job.get('status') != 'finished' or not job.get('file'):
        return HTMLResponse('<h3>File not ready</h3>', status_code=404)
    path = Path(job['file'])
    if not path.exists():
        return HTMLResponse('<h3>File missing</h3>', status_code=404)
    mime_map = {
        'mp4': 'video/mp4',
        'mkv': 'video/x-matroska',
        'webm': 'video/webm',
        'mp3': 'audio/mpeg',
        'm4a': 'audio/mp4',
        'wav': 'audio/wav'
    }
    media_type = mime_map.get(job.get('ext'), 'application/octet-stream')
    def streamer():
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk
    return StreamingResponse(streamer(), media_type=media_type, headers={'Content-Disposition': f'attachment; filename="{path.name}"'})

@app.post('/api/job/{job_id}/cancel')
async def api_job_cancel(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return {'ok': False, 'error': 'Job not found'}
        if job.get('status') in ('finished','error','canceled'):
            return {'ok': False, 'error': 'Job not active'}
        # Mark cancel intent; do not immediately mark as canceled to avoid race with worker finishing & overriding
        job['cancel'] = True
        if job.get('status') not in ('canceled','finished','error'):
            job['status'] = 'canceling'
    return {'ok': True, 'status': 'canceling'}

