from flask import Flask, request, jsonify
import subprocess, os, boto3, uuid

app = Flask(__name__)

R2_ENDPOINT = os.environ['R2_ENDPOINT']
R2_ACCESS_KEY = os.environ['R2_ACCESS_KEY']
R2_SECRET_KEY = os.environ['R2_SECRET_KEY']
R2_BUCKET = os.environ['R2_BUCKET']

s3 = boto3.client('s3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    region_name='auto'
)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/process', methods=['POST'])
def process():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    job_id = str(uuid.uuid4())[:8]
    video_path = f'/tmp/{job_id}.mp4'
    frames_dir = f'/tmp/{job_id}_frames'
    os.makedirs(frames_dir, exist_ok=True)

    try:
        # Step 1 — download with yt-dlp
        subprocess.run([
            'yt-dlp',
            '--cookies', '/app/cookies.txt',
            '--merge-output-format', 'mp4',
            '-o', video_path,
            url
        ], check=True, capture_output=True)

        # Step 2 — extract frames with scene detection
        subprocess.run([
            'ffmpeg', '-i', video_path,
            '-filter:v', "select='gt(scene,0.3)'",
            '-f', 'image2',
            '-vframes', '5',
            f'{frames_dir}/frame-%03d.jpg'
        ], check=True, capture_output=True)

        # Step 3 — resize each frame to 512x512 and upload to R2
        frame_urls = []
        for fname in sorted(os.listdir(frames_dir)):
            if not fname.endswith('.jpg'):
                continue

            fpath = f'{frames_dir}/{fname}'
            resized = fpath.replace('.jpg', '_sm.jpg')

            subprocess.run([
                'ffmpeg', '-i', fpath,
                '-vf', 'scale=512:512',
                resized
            ], check=True, capture_output=True)

            key = f'frames/{job_id}/{fname}'
            s3.upload_file(
                resized, R2_BUCKET, key,
                ExtraArgs={'ContentType': 'image/jpeg'}
            )

            frame_urls.append(
                f'{R2_ENDPOINT}/{R2_BUCKET}/{key}'
            )

        # Step 4 — upload video to R2
        video_key = f'videos/{job_id}.mp4'
        s3.upload_file(
            video_path, R2_BUCKET, video_key,
            ExtraArgs={'ContentType': 'video/mp4'}
        )

        return jsonify({
            'job_id': job_id,
            'frame_urls': frame_urls,
            'video_url': f'{R2_ENDPOINT}/{R2_BUCKET}/{video_key}',
            'status': 'success'
        })

    except subprocess.CalledProcessError as e:
        return jsonify({
            'error': str(e),
            'stderr': e.stderr.decode() if e.stderr else '',
            'status': 'failed'
        }), 500

    finally:
        # Cleanup tmp files
        if os.path.exists(video_path):
            os.remove(video_path)
        for f in os.listdir(frames_dir):
            os.remove(f'{frames_dir}/{f}')
        os.rmdir(frames_dir)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
