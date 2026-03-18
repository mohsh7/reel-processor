FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg curl && \
    pip install yt-dlp flask boto3 && \
    apt-get clean

WORKDIR /app
COPY app.py .
COPY cookies.txt .

EXPOSE 8080
CMD ["python", "app.py"]
```

**Now here's exactly what to do next — step by step:**

**Step A — Create a GitHub repo (5 mins)**
Go to github.com → New repository → name it `reel-processor` → create it. Upload both files (`app.py` and `Dockerfile`). For `cookies.txt` — export your Instagram browser cookies using the "Get cookies.txt LOCALLY" Chrome extension, save as `cookies.txt` and upload that too.

**Step B — Deploy on Railway (5 mins)**
Back in Railway → your empty project → "Add Service" → "GitHub Repo" → connect your `reel-processor` repo. Railway auto-detects the Dockerfile and builds it.

**Step C — Add environment variables in Railway**
Click your service → Variables → add these:
```
R2_ENDPOINT = https://[your-account-id].r2.cloudflarestorage.com
R2_ACCESS_KEY = [from Cloudflare R2 dashboard]
R2_SECRET_KEY = [from Cloudflare R2 dashboard]
R2_BUCKET = reels
