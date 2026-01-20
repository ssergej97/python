from dataclasses import dataclass, field, asdict

from shared.cache import CacheService
from .models import Order


@dataclass
class TrackingOrder:
    restaurants: dict = field(default_factory=dict)
    delivery: dict = field(default_factory=dict)

def silpo_ordering():
    pass

def kfc_ordering():
    pass

def schedule_order(order: Order):
    cache = CacheService()
    tracking_order = TrackingOrder()
