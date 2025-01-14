from django.db import models

from decimal import Decimal
from datetime import datetime

from account.models import User


# Customer Information (all are monthly customers)
class MonthlyCustomer(models.Model):
    name = models.CharField(max_length=255, unique=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


# Product Information (e.g., Normal Jar, Premium Bottle)
class WaterProduct(models.Model):
    WATER_TYPE = [
        ("JAR", "Jar"),
        ("BOTTLE", "Bottle"),
    ]

    QUALITY_TYPE = [
        ("NORMAL", "Normal"),
        ("PREMIUM", "Premium"),
    ]

    name = models.CharField(max_length=255, unique=True)
    water_type = models.CharField(max_length=100, choices=WATER_TYPE)
    quality = models.CharField(max_length=100, choices=QUALITY_TYPE)

    def __str__(self):
        return f"{self.quality.capitalize()} {self.water_type.capitalize()}"


# Price Mapping for Each Customer and WaterProduct
class Price(models.Model):
    monthly_customer = models.ForeignKey(
        MonthlyCustomer, on_delete=models.CASCADE, related_name="prices"
    )
    water_product = models.ForeignKey(
        WaterProduct, on_delete=models.CASCADE, related_name="prices"
    )
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.monthly_customer.name} - {self.water_product.name} @ {self.price_per_unit}"


# Delivery Records
class Delivery(models.Model):
    driver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="deliveries"
    )
    delivery_date = models.DateField(auto_now_add=True)

    # Pickup quantities for each product type
    total_normal_jars = models.PositiveIntegerField(default=0)
    total_premium_jars = models.PositiveIntegerField(default=0)
    total_normal_bottles = models.PositiveIntegerField(default=0)
    total_premium_bottles = models.PositiveIntegerField(default=0)

    def total_water_picked(self):
        return (
            self.total_normal_jars
            + self.total_premium_jars
            + self.total_normal_bottles
            + self.total_premium_bottles
        )

    def total_water_accounted_for(self):
        delivered = sum(detail.quantity for detail in self.details.all())
        reported = sum(
            report.leaks + report.returns + report.half_caps
            for report in self.reports.all()
        )
        return delivered + reported

    def is_delivery_complete(self):
        return self.total_water_picked() == self.total_water_accounted_for()

    def __str__(self):
        return f"Delivery by {self.driver.name} on {self.delivery_date}"


# Delivery Details (WaterProduct Delivery to MonthlyCustomers)
class DeliveryDetail(models.Model):
    delivery = models.ForeignKey(
        Delivery, on_delete=models.CASCADE, related_name="details"
    )
    water_product = models.ForeignKey(WaterProduct, on_delete=models.CASCADE)
    monthly_customer = models.ForeignKey(MonthlyCustomer, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total_price(self):
        return self.quantity * self.price_per_unit

    def __str__(self):
        return f"{self.water_product.name} to {self.monthly_customer.name} - {self.quantity}"


# Report Discrepancies (Leaks, Returns, Half Caps)
class Report(models.Model):
    delivery = models.ForeignKey(
        Delivery, on_delete=models.CASCADE, related_name="reports"
    )
    water_product = models.ForeignKey(WaterProduct, on_delete=models.CASCADE)
    leaks = models.PositiveIntegerField(default=0)
    returns = models.PositiveIntegerField(default=0)
    half_caps = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Report for {self.water_product.name} in Delivery {self.delivery.id}"


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
    contact_person = models.CharField(
        max_length=100, help_text="Name of the contact person for the filler."
    )
    number = models.CharField(max_length=15, help_text="Contact number.")
    vehicle_number = models.CharField(
        max_length=20, help_text="Vehicle number used by the filler."
    )

    def total_received(self):
        """Calculate the total amount received by the filler."""
        return self.ledger_entries.aggregate(total=models.Sum("amount_received"))[
            "total"
        ] or Decimal("0.00")

    def total_due(self):
        """Calculate the total due amount for the filler."""
        return self.ledger_entries.aggregate(total=models.Sum("amount_due"))[
            "total"
        ] or Decimal("0.00")

    def __str__(self):
        return self.contact_person


class JarInOut(models.Model):
    created_at = models.DateTimeField(default=datetime.now)
    jar_in = models.PositiveIntegerField(
        default=0, help_text="Number of jars coming in."
    )
    jar_out = models.PositiveIntegerField(
        editable=False, default=0, help_text="Number of jars going out (calculated)."
    )
    fillers = models.ForeignKey(
        "Filler",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Contact person filling the jars.",
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

    receivable_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Bill Amount to be collected for this transaction.",
    )
    received_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Amount received for this transaction.",
    )
    due_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
        default=Decimal("0.00"),
        help_text="Remaining due amount after this transaction.",
    )

    def save(self, *args, **kwargs):
        # Calculate jar_out
        self.jar_out = self.jar_in - (self.leak + self.half_cap + self.return_jar)

        # Calculate current due for this transaction
        current_due = self.receivable_amount - self.received_amount

        # Fetch the cumulative due amount from previous records
        previous_due = JarInOut.objects.filter(fillers=self.fillers).exclude(
            id=self.id
        ).order_by(  # Exclude the current record
            "created_at"
        ).aggregate(  # Ensure correct chronological order
            total_due=models.Sum("due_amount")
        )[
            "total_due"
        ] or Decimal(
            "0.00"
        )

        # Cumulative due = previous cumulative + current due
        self.due_amount = previous_due + current_due

        super().save(*args, **kwargs)

        # Automatically create or update the ledger entry
        FillerLedger.objects.create(
            filler=self.fillers,
            jar_in_out=self,
            date=self.created_at,
            amount_received=self.received_amount,
            amount_due=self.due_amount,
            remarks=self.notes,
        )

    def __str__(self):
        return f"Jar In: {self.jar_in}, Jar Out: {self.jar_out} on {self.created_at.strftime('%Y-%m-%d')}"


class FillerLedger(models.Model):
    filler = models.ForeignKey(
        "Filler",
        on_delete=models.CASCADE,
        related_name="ledger_entries",
        help_text="The filler associated with this ledger entry.",
    )
    jar_in_out = models.ForeignKey(
        "JarInOut",
        on_delete=models.CASCADE,
        related_name="ledger_records",
        help_text="The Jar In/Out record associated with this ledger entry.",
        null=True,
        blank=True,
    )
    date = models.DateTimeField(default=datetime.now)
    amount_received = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Amount received from the filler.",
    )
    amount_due = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Cumulative due amount for the filler.",
    )
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Remarks or additional details about this ledger entry.",
    )

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
