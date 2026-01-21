from dataclasses import dataclass, field, asdict

from shared.cache import CacheService
from .enums import OrderStatus
from .models import Order


@dataclass
class TrackingOrder:
    restaurants: dict = field(default_factory=dict)
    delivery: dict = field(default_factory=dict)

def order_in_silpo(order_id: int, items):
    pass

def order_in_kfc(order_id: int, items):
    pass

def build_request_body():
    pass

def schedule_order(order: Order):
    cache = CacheService()
    tracking_order = TrackingOrder()

    items_by_restaurant = order.items_by_restaurant()
    for restaurant, items in items_by_restaurant.items():
        tracking_order.restaurants[str(restaurant.pk)] = {
            "external_id": None,
            "status": OrderStatus.NOT_STARTED,
            "request_body": build_request_body(restaurant, items)
        }

    cache.set(
        namespace="orders",
        key=str(order.pk),
        value=asdict(tracking_order)
    )

    for restaurant, items in items_by_restaurant.items():
        match restaurant.name.lower():
            case "silpo":
                order_in_silpo(order.pk, items)
            case "kfc":
                order_in_kfc(order.pk, items)

    return
