import json
from typing import Any

import redis


class CacheService:
    def __init__(self):
        self.connection: redis.Redis = redis.Redis.from_url(
            "redis;//localhost:6379/0"
        )

    @staticmethod
    def _build_key(namespace: str, key: str) -> str:
        return f"{namespace} + {key}"

    def set(self, namespace: str, key: str, value: dict, ttl: int | None = None):
        payload: str = json.dumps(value)
        self.connection.set(
            name=self._build_key(namespace, key),
            value=payload,
            ex=ttl
        )


    def get(self, namespace: str, key: str):
        result: str = self.connection.get(
            self._build_key(namespace, key)
        )

        return json.loads(result)

    def delete(self, namespace: str, key: str):
        pass