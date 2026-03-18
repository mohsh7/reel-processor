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
