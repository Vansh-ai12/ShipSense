import os
import redis

redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,   # agent ids come back as str, not bytes
)