import redis
from app.config import settings

redis_client = redis.from_url(settings.get_redis_url(), decode_responses=True)


def get_redis():
    return redis_client
