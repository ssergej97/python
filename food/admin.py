from django.contrib import admin

from .models import Dish, Order, OrderItem, Restaurant

admin.site.register(Restaurant)
admin.site.register(OrderItem)

@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "price", "restaurant")
    search_fields = ("name",)
    list_filter = ("name", "restaurant")

class DishOrderItemInline(admin.TabularInline):
    model = OrderItem

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("__str__", "id", "status")
    inlines = (DishOrderItemInline, )

