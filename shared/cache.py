from typing import Any


class CacheService:
    def __init__(self):
        self.connection = ...

    def build_key(self, namespace: str, key: str) -> str:
        return f"{namespace} + {key}"

    def set(self, namespace: str, key: str, value: Any, ttl: int | None = None):
        pass

    def get(self, namespace: str, key: str):
        pass

    def delete(self, namespace: str, key: str):
        pass