import uuid
from dataclasses import dataclass
import random
import abc
import queue
import threading
import time
from datetime import datetime, timedelta
from typing import Literal

CHECK_ORDER_DELAY = 2

OrderRequestBody = tuple[str, datetime]
DeliveryProvider = Literal["Uklon", "Uber"]
OrderDeliveryStatus = Literal["ongoing", "finished"]

storage = {
    "delivery": {},  # id: [provider, status]
    "users": [],
    "dishes": [
        {
            "id": 1,
            "name": "Salad",
            "value": 1099,
            "restaurant": "Silpo",
        },
        {
            "id": 2,
            "name": "Soda",
            "value": 199,
            "restaurant": "Silpo",
        },
        {
            "id": 3,
            "name": "Pizza",
            "value": 599,
            "restaurant": "Kvadrat",
        },
    ],
    # ...
}


@dataclass
class DeliveryOrder:
    order_name: str
    number: uuid.UUID | None = None


class DeliveryService(abc.ABC):
    def __init__(self, order: DeliveryOrder):
        self._order: DeliveryOrder = order

    @abc.abstractmethod
    def ship(self) -> None:
        """resolve the order with concrete provider"""

    @classmethod
    def _process_delivery(cls) -> None:
        """background process"""

        print("DELIVERY PROCESSING...")

        while True:
            # if not (delivery_orders := storage["delivery"]):
            #     time.sleep(1)
            #     continue
            # else:

            filtered = {k: v for k, v in storage["delivery"].items() if v[1] == "ongoing"}

            # for order_id, value in filtered.items():
            # orders_to_remove: set[uuid.UUID] = set()

            for order_id, value in filtered.items():
                if value[1] == "finished":
                    print(f"\n\t🚚 Order {order_id} is delivered by {value[0]}")
                    # orders_to_remove.add(order_id)

            # for order_id in orders_to_remove:
            #     del storage["delivery"][order_id]
            #     print(f"\n\t❌ REMOVED {order_id} from storage")

            time.sleep(CHECK_ORDER_DELAY)

    def _ship(self, delay: float):

        def _callback():
            time.sleep(delay)
            storage["delivery"][self._order.number] = (
                self.__class__.__name__, "finished"
            )
            print(f"🚚 DELIVERED {self._order}")

        thread = threading.Thread(target=_callback)
        thread.start()


class Uklon(DeliveryService):
    def ship(self) -> None:
        provider_name = self.__class__.__name__

        self._order.number = uuid.uuid4()
        storage["delivery"][self._order.number] = [provider_name, "ongoing"]
        delay: float = random.randint(1, 3)

        print(f"\n\t🚚 {provider_name} Shipping {self._order} with {delay} delay")
        self._ship(delay)


class Uber(DeliveryService):
    def ship(self) -> None:
        provider_name = self.__class__.__name__

        self._order.number = uuid.uuid4()
        storage["delivery"][self._order.number] = [provider_name, "ongoing"]
        delay: float = random.randint(3, 5)
        print(f"\n\t🚚 {provider_name} Shipping {self._order} with {delay} delay")
        self._ship(delay)


class Scheduler:
    def __init__(self):
        self.orders: queue.Queue[OrderRequestBody] = queue.Queue()

    @staticmethod
    def _service_dispatcher() -> type[DeliveryService]:
        random_provider: DeliveryProvider = random.choice(("Uklon", "Uber"))

        match random_provider:
            case "Uklon":
                return Uklon
            case "Uber":
                return Uber
            # case _:
            #     raise Exception("Not recognized delivery provider")

    def ship_order(self, order_name: str) -> None:
        ConcreteDeliveryService: type[DeliveryService] = self._service_dispatcher()
        instance = ConcreteDeliveryService(order=DeliveryOrder(order_name=order_name))
        instance.ship()

    def add_order(self, order: OrderRequestBody) -> None:
        self.orders.put(order)
        print(f"\n\t{order[0]} ADDED FOR PROCESSING")

    def process_orders(self) -> None:
        print("ORDERS PROCESSING...")

        while True:
            order = self.orders.get(True)

            time_to_wait = order[1] - datetime.now()

            if time_to_wait.total_seconds() > 0:
                self.orders.put(order)
                time.sleep(0.5)
            else:
                self.ship_order(order[0])
                # print(f"\n\t{order[0]} SENT TO SHIPPING DEPARTMENT")


def main():
    scheduler = Scheduler()
    process_orders_thread = threading.Thread(
        target=scheduler.process_orders, daemon=True
    )
    process_delivery_thread = threading.Thread(
        target=DeliveryService._process_delivery, daemon=True
    )

    process_orders_thread.start()
    process_delivery_thread.start()

    # user input:
    # A 5 (in 5 days)
    # B 3 (in 3 days)
    while True:
        order_details = input("Enter order details: ")
        data = order_details.split(" ")
        order_name = data[0]
        delay = datetime.now() + timedelta(seconds=int(data[1]))
        scheduler.add_order(order=(order_name, delay))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        raise SystemExit(0)