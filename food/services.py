from dataclasses import dataclass, field, asdict
from time import sleep

from django.db.models import QuerySet
from mypy.types import names

from config import celery_app

from shared.cache import CacheService
from .enums import OrderStatus
from .mapper import RESTAURANT_EXTERNAL_TO_INTERNAL
from .models import Order, Restaurant, OrderItem
from .providers import silpo, kfc


@dataclass
class TrackingOrder:
    restaurants: dict = field(default_factory=dict)
    delivery: dict = field(default_factory=dict)

def all_orders_cooked(order_id):
    cache = CacheService()
    tracking_order = TrackingOrder(
        **cache.get(namespace="orders", key=str(order_id))
    )
    print(f"Checking if all orders are cooked: {tracking_order.restaurants}")

    results = all(
        payload["status"] == OrderStatus.COOKED
        for _, payload in tracking_order.restaurants.items()
    )

    return results

@celery_app.task(queue="default")
def order_in_silpo(order_id: int, items: QuerySet[OrderItem]):
    client = silpo.Client()
    cache = CacheService()
    restaurant = Restaurant.objects.get(name="Silpo")

    def get_internal_status(status: silpo.OrderStatus) -> OrderStatus:
        return RESTAURANT_EXTERNAL_TO_INTERNAL["silpo"][status]

    cooked = False
    while not cooked:
        sleep(1)

        tracking_order = TrackingOrder(
            **cache.get(namespace="orders", key=str(order_id))
        )

        silpo_order = tracking_order.restaurants.get(str(restaurant.pk))

        if not silpo_order:
            raise ValueError(f"No Silpo in orders processing")

        print(f"Current Silpo order status: {silpo['status']}")

        if not silpo_order["external_id"]:
            response: silpo.OrderResponse = client.create_order(
                silpo.OrderRequestBody(
                    order=[
                        silpo.OrderItem(dish=item.dish.name, quantity=item.quantity)
                        for item in items
                    ]
                )
            )
            internal_status : OrderStatus = get_internal_status(response.status)

            tracking_order.restaurants[str(restaurant.pk)] = {
                "external_id": response.id,
                "status": internal_status,
            }

            cache.set(namespace="orders", key=str(order_id), value=asdict(tracking_order))
        else:

            response = client.get_order(str(silpo_order["external_id"]))
            internal_status = get_internal_status(response.status)
            print(f"Tracking for Silpo Order with HTTP GET api/orders. Status: {internal_status}")

            if silpo_order["status"] != internal_status:
                tracking_order.restaurants[str(restaurant.pk)]["status"] = internal_status
                print(f"Silpo order status changed to {internal_status}")
                cache.set(
                    namespace="orders",
                    key=str(order_id),
                    value=asdict(tracking_order)
                )
                if internal_status == OrderStatus.COOKING:
                    Order.objects.filter(id=order_id).update(status=OrderStatus.COOKING)

            if internal_status == OrderStatus.COOKED:
                print("Order is cooked")
                cooked = True

                if all_orders_cooked(order_id)
                    cache.set(
                        namespace="orders",
                        key=str(order_id),
                        value=asdict(tracking_order)
                    )

@celery_app.task(queue="high_priority")
def order_in_kfc(order_id: int, items):
    client = kfc.Client()
    cache = CacheService()
    restaurant = Restaurant.objects.get(name="KFC")

    tracking_order = TrackingOrder(
        **cache.get(namespace="orders", key=str(order_id))
    )

    tracking_order.restaurants[str(restaurant.pk)] = {
        "external_id": "MOCK",
        "status": OrderStatus.COOKED,
    }

    print(f"Created MOCKED KFC Order. External ID: 'MOCK', Status: COOKED")

    cache.set(namespace="orders", key=str(order_id), value=asdict(tracking_order))

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
                order_in_silpo.delay(order.pk, items)
            case "kfc":
                order_in_kfc.delay(order.pk, items)
            case _:
                raise ValueError(f"Restaurant {restaurant.name} is not available for processing")
    return
