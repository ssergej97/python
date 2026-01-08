import csv
import io
from datetime import date
from typing import Any

from django.contrib.admindocs.utils import ROLES
from django.shortcuts import redirect
from rest_framework import viewsets, serializers, routers, permissions
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from django.db import transaction

from .enums import DeliveryProvider
from .models import Restaurant, Dish, Order, OrderItem, OrderStatus
from users.models import User, Role


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
    delivery_provider = serializers.CharField()

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
        

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.role == Role.ADMIN:
            return True
        else:
            return False


class BaseFilter:
    @staticmethod
    def snake_to_camel(value: str) -> str:
        words = value.split("_")
        camel_words = [words[0].lower()] + [word.capitalize() for word in words[1:]]
        return "".join(camel_words)

    @staticmethod
    def camel_to_snake(value: str) -> str:
        result = []
        for char in value:
            if char.isupper():
                result.append("_")
                result.append(char.lower())
            else:
                result.append(char)
        return "".join(result).lstrip("_")

    def __init__(self, **kwargs) -> None:
        errors: dict[str, dict[str, Any]] = {
            "queryParams": {}
        }

        for key, value in kwargs.items():
            _key: str = self.camel_to_snake(key)
            try:
                extractor = getattr(self, f"extract_{_key}")
            except AttributeError:
                errors["queryParams"][key] = f"You forgot to define extract_{_key} method in your {self.__class__.__name__}"
                raise ValidationError(errors)
            try:
                _extracted_value = extractor(value)
            except ValidationError as error:
                errors["queryParams"][key] = str(error)
            else:
                setattr(self, _key, _extracted_value)

        if errors["queryParams"]:
            raise ValidationError(errors)

class FoodFilters(BaseFilter):
    def __init__(self, status: str | None = None, **kwargs):
        super().__init__(status=status, **kwargs)

    def extract_delivery_provider(self, provider: str | None) -> DeliveryProvider | None:
        if provider is None:
            return None
        else:
            provider_name = provider.upper()
            try:
                _provider = DeliveryProvider[provider_name]
            except KeyError:
                raise ValidationError(f"Provider {provider} is not supported")
            else:
                return _provider

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

        # TODO: Run schedular

        return Response(OrderSerializer(order).data, status=201)

    @action(methods=["get"], detail=False, url_path=r"orders/(?P<id>\d+)")
    def retrieve_order(self, request: Request, id: int) -> Response:
        order = Order.objects.get(id=id)

        serializer = OrderSerializer(order)

        return Response(data=serializer.data)

    @action(methods=["get"], detail=False, url_path="orders")
    def all_orders(self, request: Request) -> Response:
        # filters = FoodFilters(**request.query_params.dict())
        # # status: str | None = request.query_params.get("status")
        # orders = (
        #     Order.objects.all()
        #     if filters.delivery_provider is None
        #     else Order.objects.filter(delivery_provider=filters.delivery_provider)
        # )

        orders = Order.objects.all()

        paginator = LimitOffsetPagination()
        # paginator.page_size = 2
        # paginator.page_size_query_param = "size"
        page = paginator.paginate_queryset(orders, request, view=self)

        if page is not None:
            serializer = OrderSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

def import_dishes(request):
    if request.method != "post":
        raise ValidationError(f"Method {request.method} is not allowed on this resource")
    csv_file = request.FILES.get("file")
    if csv_file is None:
        raise ValueError("No CSV file provided")

    decoded = csv_file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))
    total = 0

    for row in reader:
        restaraunt_name = row["restaraunt"]
        try:
            rest = Restaurant.objects.get(name=restaraunt_name)
        except Restaurant.DoesNotExist:
            continue
        else:
            print(f"Restaurant {rest} name")

        Dish.objects.create(
            name=row["name"],
            price=int(row["price"]),
            restaraunt=rest
        )
        total+=1

    print(f"{total} dishes upload to the database")

    return redirect(request.META.get("HTTP_REFERER", "/"))

router = routers.DefaultRouter()
router.register(
    prefix="",
    viewset=FoodAPIViewSet,
    basename="food"
)