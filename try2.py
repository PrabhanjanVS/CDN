import re
import urllib.parse
import redis
from flask import Response, render_template
import threading
from redispython import store_video_in_redis

# Get environment variables with fallback defaults
REDIS_HOST = 'redis'  # Change to 'redis' if using Docker
REDIS_PORT = 6379
REDIS_USER = 'default'
REDIS_PASSWORD = None  # Set to your password if needed

CHUNK_SIZE = 1024 * 1024  # 1MB

# Redis client setup with error handling
try:
    redis_client = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=0,
        username=REDIS_USER,
        password=REDIS_PASSWORD,
        decode_responses=False,  # Binary chunks
        socket_connect_timeout=5
    )
    # Test connection
    redis_client.ping()
    print("[✓] Redis connection successful")
except redis.ConnectionError:
    print("[!] Redis connection failed - continuing without Redis")
    redis_client = None

def slugify(name):
    base, ext = name.rsplit(".", 1)
    base = re.sub(r'\W+', '_', base)
    return f"{base}.{ext}"

def is_video_fully_stored(slug):
    if not redis_client:
        return False
        
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
    if not redis_client:
        return []
        
    clean_name = slugify(urllib.parse.unquote(video_name))
    chunk_hash_key = f"video:{clean_name}:chunks"
    
    chunk_keys = redis_client.hkeys(chunk_hash_key)
    sorted_chunk_keys = sorted(chunk_keys, key=lambda x: int(x.decode() if isinstance(x, bytes) else x))

    video_chunks = []
    for chunk_key in sorted_chunk_keys:
        chunk_data = redis_client.hget(chunk_hash_key, chunk_key)
        if chunk_data:
            video_chunks.append(chunk_data)
        else:
            print(f"[!] Chunk {chunk_key} not found.")
    
    return video_chunks

def generate_video_stream(video_name):
    if not redis_client:
        return None
        
    clean_name = slugify(urllib.parse.unquote(video_name))

    if not is_video_fully_stored(clean_name):
        return None

    video_chunks = get_video_chunks(video_name)
    return b"".join(video_chunks) if video_chunks else None

def stream_video(video_name):
    safe_video_name = urllib.parse.unquote(video_name)
    
    # Check if video is in Redis
    video_data = generate_video_stream(video_name)

    if video_data:
        # Video found in Redis - stream it directly
        return Response(video_data, content_type="video/mp4")
    else:
        # Video not in Redis - start background storage and return HTML page
        if redis_client:  # Only store in Redis if Redis is available
            threading.Thread(target=store_video_in_redis, args=(video_name,), daemon=True).start()
        # Return None to indicate video not in Redis
        return None
