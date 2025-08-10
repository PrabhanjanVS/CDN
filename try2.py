import re
import urllib.parse
import redis
from flask import Response, render_template
import threading
from redispython import store_video_in_redis
from flask import redirect
import os  

# Get environment variables with fallback defaults
NGINX_URL = os.getenv('NGINX_URL', 'http://nginx-server:80/')
REDIS_HOST = 'redis'  # or '10.107.191.117' if testing with IP
REDIS_PORT = 6379
REDIS_USER = 'default'
REDIS_PASSWORD = 'user'

CHUNK_SIZE = 1024 * 1024  # 1MB

# Redis client setup with environment variables
redis_client = redis.StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    username=REDIS_USER,
    password=REDIS_PASSWORD,
    decode_responses=False  # Binary chunks
)

def slugify(name):
    base, ext = name.rsplit(".", 1)
    base = re.sub(r'\W+', '_', base)
    return f"{base}.{ext}"

def is_video_fully_stored(slug):
    meta_key = f"video:{slug}:meta"
    total_chunks = redis_client.hget(meta_key, "total_chunks")

    if not total_chunks:
        return False

    try:
        total_chunks = int(total_chunks)
    except ValueError:
        return False

    chunk_hash_key = f"video:{slug}:chunks"
    actual_chunks = redis_client.hlen(chunk_hash_key)

    return actual_chunks == total_chunks

def get_video_chunks(video_name):
    clean_name = slugify(urllib.parse.unquote(video_name))
    chunk_hash_key = f"video:{clean_name}:chunks"
    
    chunk_keys = redis_client.hkeys(chunk_hash_key)
    sorted_chunk_keys = sorted(chunk_keys, key=lambda x: int(x))

    video_chunks = []
    for chunk_key in sorted_chunk_keys:
        chunk_data = redis_client.hget(chunk_hash_key, chunk_key)
        if chunk_data:
            video_chunks.append(chunk_data)
        else:
            print(f"[!] Chunk {chunk_key} not found.")
    
    return video_chunks

def generate_video_stream(video_name):
    clean_name = slugify(urllib.parse.unquote(video_name))

    if not is_video_fully_stored(clean_name):
        return None #render_template("watch.html", video_url=f"{NGINX_URL}{video_name}")

    video_chunks = get_video_chunks(video_name)
    return b"".join(video_chunks) if video_chunks else None

#  This is the callable function you import in app.py
def stream_video(video_name):
    safe_video_name = urllib.parse.unquote(urllib.parse.unquote(video_name))
    #safe_video_name = urllib.parse.unquote(video_name)
    video_data = generate_video_stream(video_name)

    if video_data:
        return Response(video_data, content_type="video/mp4")
    else:
        # Start background store-to-redis thread
        threading.Thread(target=store_video_in_redis, args=(video_name,)).start()
        #safe_video_name = urllib.parse.unquote(video_name)
        print(f"[DEBUG] Final video URL: {NGINX_URL}{safe_video_name}")  # Add this
        #return render_template("watch.html", video_url=f"/stream/{video_name}")
        #return redirect(f"{NGINX_URL}{safe_video_name}")
        return None


def stream(video_name):
    # Internal cluster URL (never exposed to client)
    internal_url = f"http://nginx-server:80/{video_name}"
    
    # Stream with chunked encoding
    req = requests.get(internal_url, stream=True)
    return Response(
        req.iter_content(chunk_size=1024*1024),  # 1MB chunks
        content_type=req.headers['Content-Type'],
        headers={
            'X-Proxy': 'Flask',  # Debug header
            'Cache-Control': 'no-cache'
        }
    )
