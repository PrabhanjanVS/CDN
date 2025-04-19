# redisplayer.py
import re
import urllib.parse
import redis
from flask import Response, render_template
import threading
from redispython import store_video_in_redis

NGINX_URL = "http://localhost:8081/videos/"

redis_client = redis.StrictRedis(
    host="host.docker.internal",
    port=6379,
    db=0,
    username="default",
    password="user",
    decode_responses=False
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
        return None

    video_chunks = get_video_chunks(video_name)
    return b"".join(video_chunks) if video_chunks else None

# ✅ This is the callable function you import in app.py
def stream_video(video_name):
    safe_video_name = urllib.parse.unquote(video_name)
    video_data = generate_video_stream(video_name)

    if video_data:
        return Response(video_data, content_type="video/mp4")
    else:
        # Start background store-to-redis thread
        threading.Thread(target=store_video_in_redis, args=(video_name,)).start()
        #safe_video_name = urllib.parse.unquote(video_name)
        #print(f"[DEBUG] Final video URL: {NGINX_URL}{safe_video_name}")  # Add this
        return render_template("watch.html", video_url=f"{NGINX_URL}{video_name}")
