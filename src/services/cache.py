import json

import redis

from src.conf.config import settings

r = redis.Redis(host=settings.redis_host, port=settings.redis_port, db=0, decode_responses=True)

USER_TTL_SECONDS = 900


def _key(email: str) -> str:
    return f"user:{email}"


def get_cached_user(email: str) -> dict | None:
    try:
        data = r.get(_key(email))
        return json.loads(data) if data else None
    except redis.RedisError:
        return None


def set_cached_user(user) -> None:
    try:
        payload = {"id": user.id, "email": user.email, "confirmed": user.confirmed, "avatar": user.avatar}
        r.set(_key(user.email), json.dumps(payload), ex=USER_TTL_SECONDS)
    except redis.RedisError:
        pass


def invalidate_user(email: str) -> None:
    try:
        r.delete(_key(email))
    except redis.RedisError:
        pass