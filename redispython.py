import redis
import requests
import urllib
import re
import os  # For environment variables

# Get environment variables with fallback defaults
NGINX_URL = os.getenv('NGINX_URL', 'http://nginx-service:80/videos/')
REDIS_HOST = os.getenv('REDIS_HOST', 'redis-service')  # Kubernetes service name
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))  # Convert to int
REDIS_USER = os.getenv('REDIS_USER', 'default')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'user')

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

def store_video_in_redis(video_name):
    safe_video_name = urllib.parse.unquote(video_name)
    clean_name = slugify(safe_video_name)  # Sanitized version for Redis key

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
                print(f"[+] Stored chunk {chunk_index} in hash {chunk_hash_key}")
                chunk_index += 1

        # Metadata for total chunk count and original name
        meta_key = f"video:{clean_name}:meta"
        redis_client.hset(meta_key, mapping={
            "total_chunks": chunk_index,
            "original_name": safe_video_name,  # Original name stored for display
            "end_marker": "true"  # End marker indicating the video is complete
        })

        print(f"[✓] Stored {safe_video_name} as {clean_name} ({chunk_index} chunks)")

    except Exception as e:
        print(f"[!] Error while fetching {safe_video_name}: {e}")
