from datetime import datetime, timedelta, timezone
from django import forms
from .models import (
    Bill,
    Delivery,
    JarCap,
    JarInOut,
    MonthlyExpense,
    Customer,
    DeliveryCustomer,
)
from django.forms import modelformset_factory

from .models import Bill, Delivery, FillerLedger, JarCap, JarInOut, MonthlyExpense
from django import forms
from .models import MonthlyExpense, Vendor, Product
class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ["total_jars", "returned_count", "leak_count", "half_caps_count"]
        widgets = {
            "total_jars": forms.NumberInput(attrs={"class": "form-control"}),
            "returned_count": forms.NumberInput(attrs={"class": "form-control"}),
            "leak_count": forms.NumberInput(attrs={"class": "form-control"}),
            "half_caps_count": forms.NumberInput(attrs={"class": "form-control"}),
        }


class DeliveryCustomerForm(forms.ModelForm):
    existing_customer = forms.ModelChoiceField(
        queryset=Customer.objects.filter(is_monthly_customer=True),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Existing Customer (Monthly Base)",
    )
    new_customer_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="New Customer Name (In-Hand)",
    )
    new_customer_contact = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="New Customer Contact (Optional)",
    )

    class Meta:
        model = DeliveryCustomer
        fields = ["quantity", "price_per_jar"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"class": "form-control"}),
            "price_per_jar": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        existing_customer = cleaned_data.get("existing_customer")
        new_customer_name = cleaned_data.get("new_customer_name")

        if not existing_customer and not new_customer_name:
            raise forms.ValidationError(
                "Please select an existing customer or provide details for a new customer."
            )
        return cleaned_data


DeliveryCustomerFormSet = modelformset_factory(
    DeliveryCustomer,
    form=DeliveryCustomerForm,
    extra=1,
)


from django import forms
from .models import MonthlyExpense, Vendor, Product


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
            "jar_out",
            "fillers",
            "driver_name",
            "time",
            "leak",
            "half_cap",
            "return_jar",
            "notes",
        ]
        widgets = {
            "time": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            'jar_in', 'jar_out', 'fillers', 'name', 'timestamp',
            'leak', 'half_cap', 'return_jar', 'notes'
        ]
        widgets = {
            'timestamp': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super(JarInOutForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"
            if field_name != 'timestamp':  # Timestamp already has its widget defined
                field.widget.attrs['class'] = 'form-control'





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
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
class FillerLedgerForm(forms.ModelForm):
    class Meta:
        model = FillerLedger
        fields = ['filler', 'jar_in_out', 'amount_received', 'amount_due', 'remarks']
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'amount_received': forms.NumberInput(attrs={'class': 'form-control'}),
            'amount_due': forms.NumberInput(attrs={'class': 'form-control'}),
            'filler': forms.Select(attrs={'class': 'form-control'}),
            'jar_in_out': forms.Select(attrs={'class': 'form-control'}),
        }

