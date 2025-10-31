import redis
import requests
import urllib.parse
import re
import os

# Get environment variables with fallback defaults
NGINX_URL = os.getenv('NGINX_URL', 'http://storage-video-prab.s3.amazonaws.com/')
REDIS_HOST = 'redis-cache'  # Change to 'redis' if using Docker
REDIS_PORT = 6379
REDIS_USER = 'default'
REDIS_PASSWORD = 'user'# Set to your password if needed

CHUNK_SIZE = 1024 * 1024  # 1MB

# Redis client setup with error handling
try:
    redis_client = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=0,
        username=REDIS_USER,
        password=REDIS_PASSWORD,
        decode_responses=False  # Binary chunks
    )
    redis_client.ping()
    print("[✓] Redis connection successful in redispython")
except redis.ConnectionError:
    print("[!] Redis connection failed in redispython")
    redis_client = None

def slugify(name):
    base, ext = name.rsplit(".", 1)
    base = re.sub(r'\W+', '_', base)
    return f"{base}.{ext}"

def store_video_in_redis(video_name):
    if not redis_client:
        print("[!] Redis not available, skipping storage")
        return
        
    safe_video_name = urllib.parse.unquote(video_name)
    clean_name = slugify(safe_video_name)

    url = f"{NGINX_URL}{safe_video_name}"
    print(f"[+] Starting to store video: {url}")

    try:
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            print(f"[!] Failed to fetch video: {url} - Status: {response.status_code}")
            return

        chunk_index = 0
        chunk_hash_key = f"video:{clean_name}:chunks"

        # Clear any existing data
        redis_client.delete(chunk_hash_key)
        meta_key = f"video:{clean_name}:meta"
        redis_client.delete(meta_key)

        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:
                redis_client.hset(chunk_hash_key, str(chunk_index), chunk)
                if chunk_index % 10 == 0:  # Log every 10 chunks
                    print(f"[+] Stored chunk {chunk_index} for {clean_name}")
                chunk_index += 1

        # Store metadata
        redis_client.hset(meta_key, mapping={
            "total_chunks": chunk_index,
            "original_name": safe_video_name,
            "content_type": response.headers.get('Content-Type', 'video/mp4')
        })

        print(f"[✓] Successfully stored {safe_video_name} as {clean_name} ({chunk_index} chunks)")

    except Exception as e:
        print(f"[!] Error while fetching {safe_video_name}: {e}")
