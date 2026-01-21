from django.db import models
from django.db.models import QuerySet

from .enums import OrderStatus
from django.conf import settings

class Restaurant(models.Model):
    class Meta:
        db_table = "restaurants"

    name = models.CharField(max_length=255, null=False)
    address = models.TextField(null=False)

    def __str__(self):
        return f"{self.name}"

class Dish(models.Model):
    class Meta:
        db_table = "dishes"

    name = models.CharField(max_length=255, null=False)
    price = models.IntegerField()
    restaurant = models.ForeignKey(
        "Restaurant",
        on_delete=models.CASCADE,
        related_name="dishes"
    )

    def __str__(self):
        return f"{self.name}"

class Order(models.Model):
    class Meta:
        db_table = "orders"

    status = models.CharField(
        max_length=50,
        choices=OrderStatus.choices(),
        default=OrderStatus.NOT_STARTED
        )

    delivery_provider = models.CharField(max_length=20, null=True, blank=True)
    total = models.PositiveIntegerField(null=True)
    eta = models.DateField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f"[{self.pk}] {self.status} for {self.user.email}"

    def items_by_restaurant(self) -> dict["Restaurant", QuerySet["OrderItem"]]:
        results = {}

        qs = self.items.select_related("dish__restaurant")

        restaurants = {item.dish.restaurant for item in qs}

        for restaurant in restaurants:
            results[restaurant] = qs.filter(dish__restaurant=restaurant)

        return results


class OrderItem(models.Model):
    class Meta:
        db_table = "order_items"

    quantity = models.IntegerField()
    dish = models.ForeignKey(
        "Dish",
        on_delete=models.CASCADE
    )
    order = models.ForeignKey(
        "Order",
        on_delete=models.CASCADE,
        related_name="items"
    )

    def __str__(self):
        return f"[{self.order.pk}] {self.dish.name} for {self.quantity}"