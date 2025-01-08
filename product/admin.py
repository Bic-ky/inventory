from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import (
    Bill,
    CreditMarket,
    Customer,
    Filler,
    JarCap,
    JarInOut,
    MonthlyExpense,
    Product,
    Vehicle,
    Driver,
    Delivery,
    Jar,
    Vendor,
    Filler,
    Trip,
    DeliveryCustomer,
)
from django.utils.html import format_html


# Resource classes for each model to define what data can be imported/exported
class CustomerResource(resources.ModelResource):
    class Meta:
        model = Customer
        fields = ("id", "name", "customer_type", "address", "contact_number")


class VehicleResource(resources.ModelResource):
    class Meta:
        model = Vehicle
        fields = ("id", "number_plate", "model", "capacity", "driver")


class DriverResource(resources.ModelResource):
    class Meta:
        model = Driver
        fields = ("id", "user", "license_number", "vehicle")


class DeliveryResource(resources.ModelResource):
    class Meta:
        model = Delivery
        fields = ("id", "date", "driver", "customer", "jar_type")


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


# Register models with ImportExportModelAdmin for Excel import/export
@admin.register(Customer)
class CustomerAdmin(ImportExportModelAdmin):
    resource_class = CustomerResource


@admin.register(Vehicle)
class VehicleAdmin(ImportExportModelAdmin):
    resource_class = VehicleResource


@admin.register(Driver)
class DriverAdmin(ImportExportModelAdmin):
    resource_class = DriverResource


# @admin.register(Delivery)
# class DeliveryAdmin(ImportExportModelAdmin):
#     resource_class = DeliveryResource

#     list_display = ('date', 'driver', 'customer')

#     # Optionally, allow filtering by date
#     list_filter = ('date', 'jar_type', 'driver', 'customer')


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
admin.site.register(Trip)
admin.site.register(Delivery)
admin.site.register(DeliveryCustomer)
