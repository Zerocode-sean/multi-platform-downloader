# Multi Platform Video Downloader

FastAPI-based web app to preview and download videos (and audio) from TikTok, YouTube, and Instagram. Features progressive preview, background job queue with progress, cancellation, and Docker + CI scaffolding.

## Features
- Auto platform detection & preview (title, thumbnail, duration, approximate size)
- Embedded YouTube iframe preview for reliability
- TikTok (TikWM API), YouTube & Instagram via `yt-dlp`
- Download formats: Best (<=1080p), 720p, Audio (MP3)
- Background job system (start / status / file fetch)
- Progress bar with periodic polling
- Graceful cancellation (states: canceling -> canceled) + auto refresh
- MIME / extension detection & error handling
- Modern responsive dark UI (Vanilla JS + CSS)
- Dockerfile & Jenkins pipeline for CI/CD

## Roadmap
- WebSocket progress updates
- Batch URL input
- Persistent download history (SQLite + Alembic)
- Rate limiting + basic auth/API key
- Light/Dark theme toggle
- Resume / partial cleanup
- Metrics endpoint (Prometheus) & structured logging

## Stack
| Layer    | Tech |
|----------|------|
| Backend  | FastAPI, yt-dlp, requests |
| Frontend | Plain JS, Jinja2 template, CSS |
| Runtime  | Uvicorn |
| CI/CD    | Jenkinsfile (example), Docker |

## Structure
```
web_app.py            # FastAPI app (routes, job system)
templates/index.html  # UI template
static/style.css      # Styles
downloads/            # Output files (ignored in Git)
requirements.txt      # Dependencies
Dockerfile            # Container definition
Jenkinsfile           # Jenkins pipeline
.env.example          # Sample environment variables
```

## Local Development
```bash
python -m venv .venv
# PowerShell
. .venv/Scripts/Activate.ps1
# or bash
source .venv/bin/activate

pip install -r requirements.txt
uvicorn web_app:app --reload --host 127.0.0.1 --port 8000
# Open http://127.0.0.1:8000/
```
Optional: install ffmpeg for higher quality merging & audio extraction.

## Environment Variables
| Name | Default | Purpose |
|------|---------|---------|
| PORT | 8000 | App port (Docker) |
| LOG_LEVEL | info | Future logging level |
| BASIC_AUTH_USER | (unset) | Planned auth user |
| BASIC_AUTH_PASS | (unset) | Planned auth pass |

Copy `.env.example` to `.env` and adjust.

## Docker Usage
```bash
docker build -t mp-downloader:dev .
docker run --rm -p 8000:8000 mp-downloader:dev
```
Override port:
```bash
docker run -e PORT=9000 -p 9000:9000 mp-downloader:dev
```

### docker-compose (sample)
```yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    volumes:
      - ./downloads:/app/downloads
    environment:
      - PORT=8000
```

## Jenkins Pipeline (Summary)
Stages: Checkout -> Setup Python -> Lint (ruff) -> (Tests) -> Build Image -> Smoke Test -> (Push)

Smoke test curls the root page to ensure container starts.

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET    | /                     | Main UI |
| GET    | /api/preview?url=...  | JSON preview metadata |
| POST   | /api/start_download   | Start a job (form: url, format) |
| GET    | /api/job/{id}         | Job status |
| POST   | /api/job/{id}/cancel  | Request cancel |
| GET    | /api/job/{id}/file    | Download result file |

(Planned) `/health`, `/metrics`.

## Job States
`queued` -> `downloading` -> (`processing`) -> `finished`
`canceling` -> `canceled`
`error` -> terminal with error field

## Adding WebSockets (Planned Outline)
1. Add `/ws` endpoint using `WebSocket` from FastAPI.
2. Client opens socket after job start and listens for JSON progress events.
3. Server pushes percentage & speed updates from hook instead of polling.
4. Fallback to current polling if WS unavailable.

## Rate Limiting (Future Example)
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
@app.get('/')
@limiter.limit('30/minute')
async def index(...):
    ...
```

## Troubleshooting
| Issue | Solution |
|-------|----------|
| Blank page | Ensure server logs show startup; open `/docs` to verify | 
| Cancel delayed | Large segment download; wait for next yt-dlp hook callback | 
| Missing MP3 | Install ffmpeg | 
| 403/429 errors | Retry later; update User-Agent | 
| Slow downloads | Network/geo throttling; try different format |

## Security Notes
- Virtual env & artifacts ignored via `.gitignore`
- If secrets accidentally committed, rotate and purge history (`git filter-repo`)
- Planned: auth & rate limiting before public deployment

## Contributing
1. Fork & branch
2. Create tests (pytest) for new features
3. Lint: `ruff check .`
4. PR with clear description

## License
MIT (add LICENSE file if required).

## Disclaimer
For educational / personal use. Respect platform Terms of Service.
