import os
import redis
import requests
import sys

REDIS_HOST = os.getenv("REDIS_HOST", "redis-cache")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_USER = os.getenv("REDIS_USER", "default")
REDIS_PASS = os.getenv("REDIS_PASS", "user")

def get_redis_client():
    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            username=REDIS_USER,
            password=REDIS_PASS,
            decode_responses=False
        )
        r.ping()
        print(f"✅ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        return r
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        sys.exit(1)

