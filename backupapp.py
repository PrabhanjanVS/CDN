from flask import Flask, render_template_string, Response
import requests
import xml.etree.ElementTree as ET
import redis
import urllib
import re
import threading
import os

# Flask app
app = Flask(__name__)

# =============================
# Redis + Config setup
# =============================
NGINX_URL = os.getenv('NGINX_URL', 'http://storage-video-prab.s3.amazonaws.com/')
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_USER = os.getenv('REDIS_USER', 'default')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'user')

CHUNK_SIZE = 1024 * 1024  # 1MB

redis_client = redis.StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    username=REDIS_USER,
    password=REDIS_PASSWORD,
    decode_responses=False
)

# =============================
# Helper functions
# =============================
def slugify(name):
    base, ext = name.rsplit(".", 1)
    base = re.sub(r'\W+', '_', base)
    return f"{base}.{ext}"


def store_video_in_redis(video_name):
    """Fetch video from S3 and cache it into Redis"""
    safe_video_name = urllib.parse.unquote(video_name)
    clean_name = slugify(safe_video_name)
    url = f"{NGINX_URL}{safe_video_name}"

    try:
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            print(f"[!] Failed to fetch video: {url}")
            return

        chunk_index = 0
        chunk_hash_key = f"video:{clean_name}:chunks"

        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:
                redis_client.hset(chunk_hash_key, str(chunk_index), chunk)
                print(f"[+] Stored chunk {chunk_index} in Redis ({chunk_hash_key})")
                chunk_index += 1

        meta_key = f"video:{clean_name}:meta"
        redis_client.hset(meta_key, mapping={
            "total_chunks": chunk_index,
            "original_name": safe_video_name,
            "end_marker": "true"
        })

        print(f"[✓] Stored {safe_video_name} in Redis ({chunk_index} chunks).")

    except Exception as e:
        print(f"[!] Error storing {safe_video_name} in Redis: {e}")


# =============================
# Routes
# =============================

@app.route('/')
def list_s3_files():
    """List available videos from S3"""
    s3_api = "http://storage-video-prab.s3.amazonaws.com/"
    try:
        response = requests.get(s3_api)
        response.raise_for_status()
    except Exception as e:
        return f"<h3>❌ Failed to fetch S3 listing: {e}</h3>"

    try:
        root = ET.fromstring(response.content)
        ns = {'s3': 'http://s3.amazonaws.com/doc/2006-03-01/'}

        files = []
        for item in root.findall('s3:Contents', ns):
            key = item.find('s3:Key', ns).text
            size = int(item.find('s3:Size', ns).text)
            if key.lower().endswith(('.mp4', '.mkv', '.mov', '.webm', '.mp3', '.wav')):
                files.append({
                    'name': key,
                    'size': f"{size / (1024*1024):.2f} MB"
                })

        html = """
        <html>
        <head>
            <title>S3 Media</title>
            <style>
                body { font-family: Arial; margin: 20px; }
                ul { list-style-type: none; padding: 0; }
                li { margin: 8px 0; }
                a { color: #007BFF; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h2>🎥 S3 Media Files</h2>
            <ul>
            {% for f in files %}
                <li><a href="/watch/{{ f.name | urlencode }}">{{ f.name }}</a> — {{ f.size }}</li>
            {% endfor %}
            </ul>
        </body>
        </html>
        """
        return render_template_string(html, files=files)
    except Exception as e:
        return f"<h3>❌ Error parsing XML: {e}</h3>"


@app.route("/watch/<path:video_name>")
def watch(video_name):
    """Watch page for a single video"""
    return render_template_string("""
    <html>
    <head>
        <title>Now Watching: {{ video_name }}</title>
        <style>
            body { font-family: Arial; text-align: center; margin-top: 40px; }
            video { width: 80%%; height: auto; border: 2px solid #333; border-radius: 12px; }
            a { display: inline-block; margin-top: 20px; text-decoration: none; color: #007BFF; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h2>🎬 Now Playing: {{ video_name }}</h2>
        <video controls autoplay>
            <source src="/stream/{{ video_name }}" type="video/mp4">
        </video>
        <br>
        <a href="/">⬅ Back to list</a>
    </body>
    </html>
    """, video_name=video_name)


@app.route("/stream/<path:video_name>")
def stream(video_name):
    """Stream video and cache chunks into Redis as they are sent."""
    safe_video_name = urllib.parse.unquote(video_name)
    clean_name = slugify(safe_video_name)
    url = f"{NGINX_URL}{safe_video_name}"

    try:
        req = requests.get(url, stream=True)
        req.raise_for_status()
    except Exception as e:
        return f"<h3>❌ Failed to stream video: {e}</h3>"

    chunk_hash_key = f"video:{clean_name}:chunks"
    meta_key = f"video:{clean_name}:meta"

    def generate():
        chunk_index = 0
        try:
            for chunk in req.iter_content(CHUNK_SIZE):
                if chunk:
                    # Send to browser
                    yield chunk
                    # Cache to Redis (non-blocking enough for small chunks)
                    redis_client.hset(chunk_hash_key, str(chunk_index), chunk)
                    chunk_index += 1
            redis_client.hset(meta_key, mapping={
                "total_chunks": chunk_index,
                "original_name": safe_video_name,
                "end_marker": "true"
            })
            print(f"[✓] Cached {safe_video_name} ({chunk_index} chunks)")
        except Exception as e:
            print(f"[!] Streaming interrupted: {e}")

    return Response(
        generate(),
        content_type=req.headers.get('Content-Type', 'video/mp4'),
        headers={'Cache-Control': 'no-cache'}
    )


# =============================
# Run Flask
# =============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

