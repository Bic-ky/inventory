from django import forms
from .models import Bill, Delivery, JarCap, JarInOut, MonthlyExpense, DeliveryInventory

from .models import Bill, Delivery, FillerLedger, JarCap, JarInOut, MonthlyExpense
from django import forms
from .models import (
    MonthlyExpense,
    WaterProduct,
    Delivery,
    DeliveryInventory,
    JarCap,
    JarInOut,
    Bill,
    MonthlyCustomer,
    DeliveryItem,
    InventoryReport,
)


class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ["notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }


class DeliveryInventoryFormSet(
    forms.modelformset_factory(
        DeliveryInventory,
        fields=["water_product", "quantity"],
        extra=4,
        widgets={
            "water_product": forms.Select(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        },
    )
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active water products
        for form in self.forms:
            form.fields["water_product"].queryset = WaterProduct.objects.filter(
                is_active=True
            )


class MonthlyCustomerDeliveryForm(forms.ModelForm):
    monthly_customer = forms.ModelChoiceField(
        queryset=MonthlyCustomer.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "form-control select2"}),
        empty_label="Select Monthly Customer",
    )

    class Meta:
        model = DeliveryItem
        fields = ["monthly_customer", "water_product", "quantity"]
        widgets = {
            "water_product": forms.Select(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["water_product"].queryset = WaterProduct.objects.filter(
            is_active=True
        )


class InHandDeliveryForm(forms.ModelForm):
    class Meta:
        model = DeliveryItem
        fields = [
            "customer_name",
            "customer_phone",
            "water_product",
            "quantity",
            "price_per_unit",
        ]
        widgets = {
            "customer_name": forms.TextInput(attrs={"class": "form-control"}),
            "customer_phone": forms.TextInput(attrs={"class": "form-control"}),
            "water_product": forms.Select(
                attrs={"class": "form-control", "required": "required"}
            ),
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "required": "required"}
            ),
            "price_per_unit": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "required": "required",
                }
            ),
        }

    # Custom validation for quantity
    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")
        if quantity is None or quantity <= 0:
            raise forms.ValidationError("Please enter a quantity greater than 0.")
        return quantity


class InventoryReportForm(forms.ModelForm):
    class Meta:
        model = InventoryReport
        fields = ["water_product", "leaks", "returns", "half_caps", "notes"]
        widgets = {
            "water_product": forms.Select(attrs={"class": "form-control"}),
            "leaks": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "returns": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "half_caps": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class MonthlyExpenseForm(forms.ModelForm):
    class Meta:
        model = MonthlyExpense
        fields = [
            "expense_type",
            "date",
            "amount",
            "remarks",
            "vendor",
            "product",
            "miscellaneous_details",
        ]

    def __init__(self, *args, **kwargs):
        super(MonthlyExpenseForm, self).__init__(*args, **kwargs)

        # Customizing field behavior based on expense type
        self.fields["vendor"].required = False
        self.fields["product"].required = False
        self.fields["miscellaneous_details"].required = False

    def clean(self):
        cleaned_data = super().clean()
        expense_type = cleaned_data.get("expense_type")
        remarks = cleaned_data.get("remarks")
        vendor = cleaned_data.get("vendor")
        product = cleaned_data.get("product")
        miscellaneous_details = cleaned_data.get("miscellaneous_details")

        if expense_type == MonthlyExpense.MISCELLANEOUS:
            # Ensure amount and remarks are provided
            if not remarks:
                self.add_error(
                    "remarks", "Remarks are required for miscellaneous expenses."
                )

        elif expense_type == MonthlyExpense.VENDOR:
            # Ensure vendor, product, and invoice are provided
            if not vendor:
                self.add_error("vendor", "Vendor is required for vendor expenses.")
            if not product:
                self.add_error("product", "Product is required for vendor expenses.")
            # Miscellaneous details should not be filled
            if miscellaneous_details:
                self.add_error(
                    "miscellaneous_details",
                    "Miscellaneous details should not be filled for vendor expenses.",
                )

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({"class": "form-control"})


class JarInOutForm(forms.ModelForm):
    class Meta:
        model = JarInOut
        fields = [
            "jar_in",
            "fillers",
            "leak",
            "half_cap",
            "return_jar",
            "receivable_amount",  # User inputs this field
            "received_amount",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"


class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = [
            "delivery",
            "payment_category",
            "online_method",
            "receivable_amount",
            "amount_received_by_driver",
            "notes",
        ]
        widgets = {
            "delivery": forms.Select(attrs={"class": "form-control"}),
            "payment_category": forms.Select(attrs={"class": "form-control"}),
            "online_method": forms.Select(attrs={"class": "form-control"}),
            "receivable_amount": forms.NumberInput(attrs={"class": "form-control"}),
            "amount_received_by_driver": forms.NumberInput(
                attrs={"class": "form-control"}
            ),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only let user choose Delivery objects that don't already have a Bill
        # i.e., 'bill__isnull=True'
        self.fields["delivery"].queryset = Delivery.objects.filter(bill__isnull=True)

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("payment_category")
        method = cleaned_data.get("online_method")
        if category == "online" and not method:
            self.add_error(
                "online_method",
                "Select an online method if payment category is Online.",
            )
        return cleaned_data


class JarCapForm(forms.ModelForm):
    class Meta:
        model = JarCap
        fields = ["quantity_in_bora", "price_per_bora", "date_brought"]
        widgets = {
            "quantity_in_bora": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "price_per_bora": forms.NumberInput(attrs={"class": "form-control"}),
            "date_brought": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
        }


class IncreaseJarCapForm(forms.Form):
    added_bora = forms.IntegerField(
        min_value=1,
        label="Add Bora",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )


class DecreaseJarCapForm(forms.Form):
    used_bora = forms.IntegerField(
        min_value=1,
        label="Use Bora",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    widget = forms.NumberInput(attrs={"class": "form-control"})


class FillerLedgerForm(forms.ModelForm):
    class Meta:
        model = FillerLedger
        fields = ["filler", "jar_in_out", "amount_received", "amount_due", "remarks"]
        widgets = {
            "remarks": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "amount_received": forms.NumberInput(attrs={"class": "form-control"}),
            "amount_due": forms.NumberInput(attrs={"class": "form-control"}),
            "filler": forms.Select(attrs={"class": "form-control"}),
            "jar_in_out": forms.Select(attrs={"class": "form-control"}),
        }
