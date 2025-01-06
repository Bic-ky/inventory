from datetime import datetime, timezone
from django.db import models
from decimal import Decimal

from account.models import User


class Customer(models.Model):
    INDIVIDUAL = "INDIVIDUAL"
    COMPANY = "COMPANY"

    CUSTOMER_TYPES = [
        (INDIVIDUAL, "Individual"),
        (COMPANY, "Company"),
    ]

    name = models.CharField(max_length=100)
    customer_type = models.CharField(max_length=10, choices=CUSTOMER_TYPES)
    address = models.TextField(blank=True, null=True)  # Optional for in-hand customers
    contact_number = models.CharField(max_length=15, blank=True, null=True)  # Optional
    is_monthly_customer = models.BooleanField(default=False)  # To differentiate types

    def __str__(self):
        return f"{self.name} ({self.get_customer_type_display()})"


class Trip(models.Model):
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trips")
    date = models.DateField(auto_now_add=True)
    trip_number = models.PositiveIntegerField()  # Trip number in the day (1, 2, ...)

    def __str__(self):
        return f"Trip {self.trip_number} by {self.driver} on {self.date}"


class Delivery(models.Model):
    trip = models.ForeignKey(
        "Trip", on_delete=models.CASCADE, related_name="deliveries"
    )
    total_jars = models.PositiveIntegerField()  # Total jars carried for the trip
    returned_count = models.PositiveIntegerField(default=0)
    leak_count = models.PositiveIntegerField(default=0)
    half_caps_count = models.PositiveIntegerField(default=0)
    driver = models.ForeignKey(User, on_delete=models.CASCADE)

    def validate_total_jars(self):
        delivered_count = sum(
            customer_delivery.quantity
            for customer_delivery in self.customer_deliveries.all()
        )
        accounted_jars = (
            self.returned_count
            + self.leak_count
            + self.half_caps_count
            + delivered_count
        )
        return self.total_jars == accounted_jars

    def __str__(self):
        return f"Delivery by {self.driver} in Trip {self.trip}"


class DeliveryCustomer(models.Model):
    delivery = models.ForeignKey(
        Delivery, on_delete=models.CASCADE, related_name="customer_deliveries"
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()  # Jars delivered to this customer
    price_per_jar = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.price_per_jar
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.quantity} jars to {self.customer.name} at {self.price_per_jar}/jar"
        )


# Vehicle model
class Vehicle(models.Model):
    number_plate = models.CharField(max_length=20, unique=True)
    model = models.CharField(max_length=50)
    capacity = models.IntegerField(help_text="Capacity in liters or number of jars")
    driver = models.ForeignKey(
        "Driver",
        on_delete=models.CASCADE,
        related_name="vehicles",
        blank=True,
        null=True,
    )  # Updated related_name

    def __str__(self):
        return self.number_plate


class Driver(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, limit_choices_to={"role": "DRIVER"}
    )
    license_number = models.CharField(max_length=20)
    vehicle = models.ForeignKey(
        "Vehicle",
        on_delete=models.CASCADE,
        related_name="drivers",
        blank=True,
        null=True,
    )  # Updated related_name

    def __str__(self):
        return self.user.full_name


# class Delivery(models.Model):
#     date = models.DateField(auto_now_add=True)
#     driver = models.ForeignKey(
#         User, on_delete=models.SET_NULL, null=True, limit_choices_to={"role": "DRIVER"}
#     )
#     customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
#     quantity = models.IntegerField(help_text="Number of jars delivered or returned")
#     jar_type = models.CharField(
#         max_length=1, choices=[("P", "Premium"), ("N", "Normal")], null=True, blank=True
#     )
#     sold_new_jars = models.IntegerField(
#         default=0, help_text="Number of new jars sold during delivery"
#     )
#     jar_price_at_delivery = models.DecimalField(
#         max_digits=6,
#         decimal_places=2,
#         default=0.0,
#         help_text="Price of each jar sold during this delivery",
#     )

#     delivered_count = models.IntegerField(
#         default=0, help_text="Number of jars successfully delivered"
#     )
#     returned_count = models.IntegerField(
#         default=0, help_text="Number of jars returned by the customer"
#     )
#     leak_count = models.IntegerField(
#         default=0, help_text="Number of jars found leaking"
#     )
#     half_caps_count = models.IntegerField(
#         default=0, help_text="Number of jars with half caps issues"
#     )

#     def __str__(self):
#         return f"{self.quantity} jars - to {self.customer.name}"

#     def total_cost(self):
#         """Calculate the total cost for the delivery including sold jars."""
#         regular_delivery_cost = self.quantity * 40
#         new_jar_cost = self.sold_new_jars * (300 + 40)
#         total_cost = regular_delivery_cost + new_jar_cost
#         return total_cost

#     def calculate_bill(self):
#         """Calculate the total cost for this delivery."""
#         regular_delivery_cost = Decimal(self.quantity * 40)
#         new_jar_cost = Decimal(self.sold_new_jars * (300 + 40))
#         return regular_delivery_cost + new_jar_cost


class Jar(models.Model):
    jar_type = models.CharField(
        max_length=1, choices=[("P", "Premium"), ("N", "Normal")], default="Normal"
    )
    total_jars = models.IntegerField(blank=True, null=True)
    available_jars = models.IntegerField(blank=True, null=True)
    damaged_jars = models.IntegerField(default=0)
    returned_jars = models.IntegerField(default=0)
    sold_jars = models.IntegerField(default=0, help_text="Number of jars sold")
    jar_price = models.DecimalField(
        max_digits=6, decimal_places=2, default=0.0, help_text="Price per jar if sold"
    )

    def __str__(self):
        return f"{self.total_jars} total jars ({self.get_jar_type_display()})"


from django.db import models
from decimal import Decimal


class Bill(models.Model):
    """
    One Bill per Delivery.
    The Bill references the Delivery for jar info and driver/customer context,
    plus we add payment-related fields.
    """

    # One-to-One means each Delivery can have exactly one Bill
    delivery = models.OneToOneField(
        Delivery, on_delete=models.CASCADE, related_name="bill"
    )

    # Payment category & sub-options
    CATEGORY_CHOICES = [
        ("cash", "Cash"),
        ("online", "Online"),
    ]
    ONLINE_METHOD_CHOICES = [
        ("mobile_banking", "Mobile Banking"),
        ("digital_wallet", "Digital Wallet"),
    ]

    payment_category = models.CharField(
        max_length=10,
        choices=CATEGORY_CHOICES,
        default="cash",
        help_text="Cash or Online",
    )
    online_method = models.CharField(
        max_length=20,
        choices=ONLINE_METHOD_CHOICES,
        blank=True,
        null=True,
        help_text="Required if payment_category = Online",
    )

    # Finance fields
    receivable_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    amount_received_by_driver = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    due_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), editable=False
    )

    # Bill date & optional notes
    date_issued = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        """
        1. If payment_category != online, clear online_method.
        2. due_amount = receivable_amount - amount_received_by_driver.
        3. Optionally auto-fill receivable_amount from Delivery, if desired.
        """
        if self.payment_category != "online":
            self.online_method = None

        # If you want to auto-set receivable_amount from the Delivery cost:
        # self.receivable_amount = self.delivery.calculate_bill()

        self.due_amount = self.receivable_amount - self.amount_received_by_driver
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Bill for Delivery ID {self.delivery_id} - Due: {self.due_amount}"


    
class Filler(models.Model):
    contact_person = models.CharField(max_length=100, help_text="Name of the contact person for the filler.")
    number = models.CharField(max_length=15, help_text="Contact number.")
    vehicle_number = models.CharField(max_length=20, help_text="Vehicle number used by the filler.")

    def total_received(self):
        """Calculate the total amount received by the filler."""
        return self.ledger_entries.aggregate(total=models.Sum('amount_received'))['total'] or Decimal('0.00')

    def total_due(self):
        """Calculate the total due amount for the filler."""
        return self.ledger_entries.aggregate(total=models.Sum('amount_due'))['total'] or Decimal('0.00')

    def __str__(self):
        return self.contact_person
    

class JarInOut(models.Model):
    created_at = models.DateTimeField(default=datetime.now)

    jar_in = models.PositiveIntegerField(
        default=0, help_text="Number of jars coming in."
    )
    jar_out = models.PositiveIntegerField(
        default=0, help_text="Number of jars going out."
    )
    fillers = models.ForeignKey(
        "Filler",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Contact person filling the jars.",
    )
    vehicle_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Vehicle number used for transportation.",
    )
    driver_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Name associated with the record.",
    )
    time = models.DateTimeField(
        blank=True, null=True, help_text="Datetime of the transaction."
    )
    leak = models.PositiveIntegerField(
        default=0, help_text="Number of jars with leaks."
    )
    half_cap = models.PositiveIntegerField(
        default=0, help_text="Number of jars with half caps."
    )
    return_jar = models.PositiveIntegerField(
        default=0, help_text="Number of jars returned."
    )
    notes = models.TextField(
        blank=True, null=True, help_text="Additional info about this record."
    )

    jar_in = models.PositiveIntegerField(default=0, help_text="Number of jars coming in.")
    jar_out = models.PositiveIntegerField(default=0, help_text="Number of jars going out.")
    fillers = models.ForeignKey(
        'Filler',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='jar_records',
        help_text="Contact person filling the jars."
    )
    vehicle_number = models.CharField(max_length=20, blank=True, null=True, help_text="Vehicle number used for transportation.")
    name = models.CharField(max_length=100, blank=True, null=True, help_text="Name associated with the record.")
    timestamp = models.DateTimeField(blank=True, null=True, help_text="Timestamp of the transaction.")
    leak = models.PositiveIntegerField(default=0, help_text="Number of jars with leaks.")
    half_cap = models.PositiveIntegerField(default=0, help_text="Number of jars with half caps.")
    return_jar = models.PositiveIntegerField(default=0, help_text="Number of jars returned.")
    notes = models.TextField(blank=True, null=True, help_text="Additional info about this record.")


    def __str__(self):
        return f"Jar In: {self.jar_in}, Jar Out: {self.jar_out} on {self.created_at.strftime('%Y-%m-%d')}"



class Filler(models.Model):
    contact_person = models.CharField(max_length=100)
    number = models.CharField()
    vehicle_number = models.CharField(max_length=20)
class FillerLedger(models.Model):
    filler = models.ForeignKey(
        'Filler', 
        on_delete=models.CASCADE, 
        related_name='ledger_entries', 
        help_text="The filler associated with this ledger entry."
    )
    jar_in_out = models.ForeignKey(
        'JarInOut',
        on_delete=models.CASCADE,
        related_name='ledger_records',
        help_text="The Jar In/Out record associated with this ledger entry.",
        null=True,
        blank=True
    )
    date = models.DateTimeField(default=datetime.now)
    amount_received = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        help_text="Amount received from the filler."
    )
    amount_due = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        help_text="Amount still due."
    )
    remarks = models.TextField(
        blank=True, 
        null=True, 
        help_text="Remarks or additional details about this ledger entry."
    )

    def balance_due(self):
        """Calculate the balance due."""
        return self.amount_due - self.amount_received

    def __str__(self):
        return f"{self.filler.contact_person} - {self.date.strftime('%Y-%m-%d')}"



class CreditMarket(models.Model):
    company_name = models.CharField(max_length=100)
    registration_number = models.IntegerField()
    contact_number = models.CharField()
    address = models.CharField()
    rate = models.IntegerField()

    def __str__(self):
        return self.company_name


class JarCap(models.Model):
    """
    Keeps a record of jar caps.
    1. quantity_in_bora: how many 'boras' of caps you have
    2. price_per_bora: cost per bora
    3. date_brought: when the caps were brought in
    """

    quantity_in_bora = models.PositiveIntegerField(
        help_text="Number of boras of jar caps currently in stock."
    )
    price_per_bora = models.DecimalField(
        max_digits=8, decimal_places=2, help_text="Price per bora of jar caps."
    )
    date_brought = models.DateField(
        default=datetime.now, help_text="Date when these jar caps were brought in."
    )

    last_updated = models.DateField(
        help_text="Date when we last changed this jar cap stock.", null=True, blank=True
    )

    usage_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date when jar caps were last used (set 1 day ahead).",
    )

    def __str__(self):
        return f"Jar Caps: {self.quantity_in_bora} boras @ {self.price_per_bora} (brought on {self.date_brought})"

    def is_low_stock(self):
        """
        Returns True if quantity_in_bora < 7, indicating low stock.
        """
        return self.quantity_in_bora < 7


class Vendor(models.Model):
    name = models.CharField(max_length=255, unique=True)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    CATEGORY_CHOICES = [
        ("jar_cap", "Jar Cap"),
        ("jar_label", "Jar Label"),
        ("date_sticker", "Date Sticker"),
        ("liquid_soap", "Liquid Soap"),
    ]

    name = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.get_category_display()} - {self.name}"


class MonthlyExpense(models.Model):
    DAILY_EXPENSE = "DAILY"
    MISCELLANEOUS = "MISCELLANEOUS"
    VENDOR = "VENDOR"

    EXPENSE_TYPE_CHOICES = [
        (DAILY_EXPENSE, "Daily Expense"),
        (MISCELLANEOUS, "Miscellaneous"),
        (VENDOR, "Vendor"),
    ]

    # Common Fields
    date = models.DateField(default=datetime.now)
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    remarks = models.TextField(
        blank=True, null=True, help_text="Additional remarks about the expense"
    )

    # Vendor-related Fields
    vendor = models.ForeignKey(
        "Vendor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
        help_text="Vendor associated with the expense (if applicable)",
    )
    product = models.ForeignKey(
        "Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
        help_text="Product associated with the expense (if applicable)",
    )
    # Miscellaneous Expenses
    miscellaneous_details = models.TextField(
        blank=True, null=True, help_text="Details for miscellaneous expenses"
    )

    # Method for calculating monthly total
    @classmethod
    def total_monthly_expense(cls, month, year):
        """Returns the total expense for a specific month and year."""
        return (
            cls.objects.filter(date__month=month, date__year=year).aggregate(
                total=models.Sum("amount")
            )["total"]
            or 0
        )

    def __str__(self):
        return f"{self.get_expense_type_display()} - {self.amount} on {self.date}"

    class Meta:
        verbose_name = "Monthly Expense"
        verbose_name_plural = "Monthly Expenses"
        ordering = ["-date"]
