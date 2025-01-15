from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import (
    Bill,
    CreditMarket,
    Filler,
    JarCap,
    JarInOut,
    MonthlyExpense,
    Product,
    Vehicle,
    Driver,
    Jar,
    Vendor,
    Filler,
    MonthlyCustomer,
    WaterProduct,
    CustomerPrice,
    Delivery,
    DeliveryInventory,
    DeliveryItem,
    InventoryReport,
)
from django.utils.html import format_html


# Resource classes for each model to define what data can be imported/exported


class VehicleResource(resources.ModelResource):
    class Meta:
        model = Vehicle
        fields = ("id", "number_plate", "model", "capacity", "driver")


class DriverResource(resources.ModelResource):
    class Meta:
        model = Driver
        fields = ("id", "user", "license_number", "vehicle")


class JarResource(resources.ModelResource):
    class Meta:
        model = Jar
        fields = (
            "id",
            "jar_type",
            "total_jars",
            "available_jars",
            "damaged_jars",
            "returned_jars",
        )


@admin.register(Vehicle)
class VehicleAdmin(ImportExportModelAdmin):
    resource_class = VehicleResource


@admin.register(Driver)
class DriverAdmin(ImportExportModelAdmin):
    resource_class = DriverResource


@admin.register(Jar)
class JarAdmin(ImportExportModelAdmin):
    resource_class = JarResource


@admin.register(JarCap)
class JarCapAdmin(admin.ModelAdmin):
    list_display = (
        "quantity_in_bora",
        "price_per_bora",
        "date_brought",
        "stock_status",
    )
    list_filter = ("date_brought",)

    def stock_status(self, obj):
        """
        Custom column to display a warning if stock is below 7 boras.
        """
        if obj.is_low_stock():
            return format_html('<span style="color:red;">LOW STOCK</span>')
        return "OK"

    stock_status.short_description = "Stock Status"


admin.site.register(Bill)
admin.site.register(MonthlyExpense)
admin.site.register(Vendor)
admin.site.register(Product)
admin.site.register(Filler)
admin.site.register(CreditMarket)
admin.site.register(JarInOut)


@admin.register(MonthlyCustomer)
class MonthlyCustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "address", "is_active", "created_at")
    search_fields = ("name", "phone", "address")
    list_filter = ("is_active", "created_at")


@admin.register(WaterProduct)
class WaterProductAdmin(admin.ModelAdmin):
    list_display = ("id", "water_type", "quality", "default_price", "is_active")
    list_filter = ("water_type", "quality", "is_active")
    search_fields = ("water_type", "quality")


@admin.register(CustomerPrice)
class CustomerPriceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "monthly_customer",
        "water_product",
        "price",
        "effective_from",
        "is_active",
    )
    list_filter = ("is_active", "effective_from")
    search_fields = (
        "monthly_customer__name",
        "water_product__quality",
        "water_product__water_type",
    )


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "driver",
        "delivery_date",
        "start_time",
        "end_time",
        "status",
        "notes",
    )
    list_filter = ("delivery_date", "status")
    search_fields = ("driver__full_name",)
    readonly_fields = ("delivery_date", "start_time")  # Prevent modification


@admin.register(DeliveryInventory)
class DeliveryInventoryAdmin(admin.ModelAdmin):
    list_display = ("id", "delivery", "water_product", "quantity")
    list_filter = (
        "delivery__delivery_date",
        "water_product__water_type",
        "water_product__quality",
    )
    search_fields = (
        "delivery__driver__full_name",
        "water_product__quality",
        "water_product__water_type",
    )


@admin.register(DeliveryItem)
class DeliveryItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "delivery",
        "water_product",
        "monthly_customer",
        "quantity",
        "price_per_unit",
        "customer_name",
        "customer_phone",
    )
    list_filter = (
        "delivery__delivery_date",
        "water_product__water_type",
        "water_product__quality",
    )
    search_fields = (
        "monthly_customer__name",
        "customer_name",
        "customer_phone",
        "water_product__quality",
    )


@admin.register(InventoryReport)
class InventoryReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "delivery",
        "water_product",
        "leaks",
        "returns",
        "half_caps",
    )
    list_filter = (
        "delivery__delivery_date",
        "water_product__water_type",
        "water_product__quality",
    )
    search_fields = (
        "delivery__driver__full_name",
        "water_product__quality",
        "water_product__water_type",
    )
