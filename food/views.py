import json
from dataclasses import asdict
from datetime import date
from pyexpat.errors import messages

from django.contrib.admindocs.utils import ROLES
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from mypy.types import names
from rest_framework import viewsets, serializers, routers, permissions
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from django.db import transaction
from services import schedule_order
from shared.cache import CacheService

from .models import Restaurant, Dish, Order, OrderItem, OrderStatus
from users.models import User, Role
from .services import TrackingOrder, all_orders_cooked


class DishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        exclude = ["restaurant"]

class OrderItemSerializer(serializers.Serializer):
    dish = serializers.PrimaryKeyRelatedField(queryset=Dish.objects.all())
    quantity = serializers.IntegerField(min_value=1, max_value=20)

class OrderSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(read_only=True)
    items = OrderItemSerializer(many=True)
    eta = serializers.DateField()
    total = serializers.IntegerField(min_value=1, read_only=True)
    status = serializers.ChoiceField(OrderStatus.choices(), read_only=True)

    @property
    def calculated_total(self) -> int:
        total = 0

        for item in self.validated_data["items"]:
            dish: Dish = item["dish"]
            quantity = item["quantity"]
            total += dish.price * quantity

        return total

    def validate_eta(self, value: date):
        if (value - date.today()) < 1:
            raise ValidationError("ETA must be min 1 day after today")
        else:
            return value

class RestaurantSerializer(serializers.ModelSerializer):
    dishes = DishSerializer(many=True)

    class Meta:
        model = Restaurant
        fields = "__all__"

class KFCOrderSerializer(serializers.Serializer):
    pass
        

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.role == Role.ADMIN:
            return True
        else:
            return False


class FoodAPIViewSet(viewsets.GenericViewSet):
    def get_permissions(self):
        match self.action:
            case "all_orders":
                return [permissions.IsAuthenticated(), IsAdmin()]
            case _:
                return [permissions.IsAuthenticated()]

    @action(methods=["get"], detail=False)
    def dishes(self, request: Request) -> Response:
        restaurants = Restaurant.objects.all()
        serializer = RestaurantSerializer(restaurants, many=True)
        return Response(data=serializer.data)

    @transaction.atomic
    @action(methods=["post"], detail=False, url_path=r"orders")
    def create_order(self, request: Request) -> Response:
        """

        :param request:
        :return:
        """
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assert type(request.user) is User

        order = Order.objects.create(
            status=OrderStatus.NOT_STARTED,
            user=request.user,
            delivery_provider="uklon",
            eta=serializer.validated_data["eta"],
            total = serializer.calculated_total
        )

        items = serializer.validated_data["items"]

        for dish_order in items:
            instance = OrderItem.objects.create(
                dish=dish_order["dish"],
                quantity=dish_order["quantity"],
                order=order
            )
            print(f"New dish order item is created: {instance.pk}")

        print(f"New food order is created {order.pk}. ETA: {order.eta}")

        schedule_order(order)

        return Response(OrderSerializer(order).data, status=201)

    @action(methods=["get"], detail=False, url_path=r"orders/(?P<id>\d+)")
    def retrieve_order(self, request: Request, id: int) -> Response:
        order = Order.objects.get(id=id)

        serializer = OrderSerializer(order)

        return Response(data=serializer.data)

    @action(methods=["get"], detail=False, url_path="orders")
    def all_orders(self, request: Request) -> Response:
        orders = Order.objects.all()
        serializer = OrderSerializer(orders, many=True)

        return Response(serializer.data)

    @action(methods=["post"], detail=False, url_path="webhooks/kfc/")
    def kfc_webhook(self, request: Request):
        data = request.data
        return

@csrf_exempt
def kfc_webhook(request):

    print("KFC webhook is handled")

    data: dict = json.loads(request.POST)

    cache = CacheService()
    restaurant = Restaurant.objects.get(name="KFC")
    kfc_cache_order = cache.get("kfc_orders", key=data["id"])

    order: Order = Order.objects.get(id=kfc_cache_order["internal_order_id"])
    tracking_order = TrackingOrder(
        **cache.get(namespace="orders", key=str(order.pk))
    )
    tracking_order.restaurants[str(restaurant.pk)] = {
        "external_id": data["id"],
        "status": OrderStatus.COOKED,
    }

    cache.set(namespace="orders", key=str(order.pk), value=asdict(tracking_order))

    if all_orders_cooked(order.pk):
        order.status = OrderStatus.COOKED
        order.save()
        print(f"All orders are cooked")
    else:
        print(f"Not all orders are cooked")

    return JsonResponse({"message": "ok"})

router = routers.DefaultRouter()
router.register(
    prefix="",
    viewset=FoodAPIViewSet,
    basename="food"
)