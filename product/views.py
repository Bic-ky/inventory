from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse

import json

from account.models import Attendance, User
from .forms import (
    BillForm,
    DecreaseJarCapForm,
    DeliveryForm,
    IncreaseJarCapForm,
    JarCapForm,
    JarInOutForm,
    MonthlyExpenseForm,
    DeliveryForm,
    DeliveryCustomerFormSet,
)
from .models import (
    Bill,
    Customer,
    Delivery,
    Filler,
    JarCap,
    JarInOut,
    Trip,
    DeliveryCustomer,
)
from .forms import (
    BillForm,
    DecreaseJarCapForm,
    DeliveryForm,
    FillerLedgerForm,
    IncreaseJarCapForm,
    JarCapForm,
    JarInOutForm,
    MonthlyExpenseForm,
)
from .models import Bill, Customer, Delivery, Filler, FillerLedger, JarCap, JarInOut
from datetime import datetime, timedelta
from django.db.models import Sum, Count, F, DecimalField
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import date

from django.db import models

from .models import MonthlyExpense


def delivery(request):
    today = now().date()
    current_month_start = today.replace(day=1)
    current_month_end = (
        today.replace(month=today.month % 12 + 1, day=1)
        if today.month < 12
        else today.replace(year=today.year + 1, month=1, day=1)
    ) - timedelta(days=1)

    filter_date = request.GET.get("date", None)
    if filter_date:
        filter_date = datetime.strptime(filter_date, "%Y-%m").date()
        current_month_start = filter_date.replace(day=1)
        current_month_end = (
            filter_date.replace(month=filter_date.month % 12 + 1, day=1)
            if filter_date.month < 12
            else filter_date.replace(year=filter_date.year + 1, month=1, day=1)
        ) - timedelta(days=1)

    user = request.user

    # Query deliveries based on the user's role
    if user.role == User.DRIVER:
        deliveries = Delivery.objects.filter(
            trip__driver=user,
            trip__date__range=(current_month_start, current_month_end),
        )
    else:
        deliveries = Delivery.objects.filter(
            trip__date__range=(current_month_start, current_month_end)
        )

    # Aggregate data grouped by date
    delivery_summary = (
        deliveries.values("trip__date")
        .annotate(
            no_of_trips=Count("trip", distinct=True),
            total_returned=Sum("returned_count"),
            total_leak=Sum("leak_count"),
            total_half_caps=Sum("half_caps_count"),
            total_jar_delivered=Sum("customer_deliveries__quantity"),
            total_customers=Count("customer_deliveries__customer", distinct=True),
        )
        .order_by("trip__date")
    )

    context = {
        "delivery_summary": delivery_summary,
        "current_month_start": current_month_start,
        "current_month_end": current_month_end,
        "today": today,
        "user": user,
    }
    print(context)
    return render(request, "plant/delivery.html", context)


@login_required
def add_delivery(request):
    driver = request.user
    today = date.today()

    if request.method == "POST":
        print("Submit POST Request")
        delivery_form = DeliveryForm(request.POST)
        customer_formset = DeliveryCustomerFormSet(request.POST)

        if delivery_form.is_valid() and customer_formset.is_valid():
            print("Valid Form")
            delivery = delivery_form.save(commit=False)
            delivery.driver = driver

            # Validate total jars
            delivered_count = sum(
                form.cleaned_data["quantity"]
                for form in customer_formset
                if form.cleaned_data
            )
            accounted_jars = (
                delivered_count
                + delivery.returned_count
                + delivery.leak_count
                + delivery.half_caps_count
            )
            if accounted_jars != delivery.total_jars:
                print("Not valid Jar Number")
                messages.error(
                    request,
                    f"Total jars ({delivery.total_jars}) must match sum of accounted jars ({accounted_jars}).",
                )
            else:
                # return redirect("add_delivery")
                # Create the trip only when validation succeeds
                trip_number = Trip.objects.filter(driver=driver, date=today).count() + 1
                current_trip = Trip.objects.create(
                    driver=driver, date=today, trip_number=trip_number
                )

                delivery.trip = current_trip
                delivery.save()

                for form in customer_formset:
                    customer_delivery = form.save(commit=False)
                    customer_delivery.delivery = delivery

                    # Assign customer based on customer_type
                    customer_type = form.cleaned_data.get("customer_type")
                    if customer_type == "monthly":
                        customer_delivery.customer = form.cleaned_data.get(
                            "existing_customer"
                        )
                    elif customer_type == "in_hand_existing":
                        customer_delivery.customer = form.cleaned_data.get(
                            "existing_in_hand_customer"
                        )
                    elif customer_type == "in_hand_new":
                        # Create a new customer for 'in_hand_new'
                        new_customer = Customer.objects.create(
                            name=form.cleaned_data.get("new_customer_name"),
                            contact_number=form.cleaned_data.get(
                                "new_customer_contact"
                            ),
                            customer_type="in_hand",
                        )
                        customer_delivery.customer = new_customer

                    customer_delivery.save()

                messages.success(request, "Delivery added successfully.")
                return redirect("add_delivery")
        else:
            print("Not Valid POST Request")
            print(delivery_form.errors)
            print(customer_formset.errors)

            # Handle delivery form errors
            if not delivery_form.is_valid():
                for field in delivery_form:
                    for error in field.errors:
                        messages.error(
                            request, f"Error in field '{field.label}': {error}"
                        )

                # Handle non-field errors (form-wide errors) for delivery form
                for error in delivery_form.non_field_errors():
                    messages.error(request, f"Error: {error}")

            # Handle customer formset errors
            if not customer_formset.is_valid():
                for i, form in enumerate(customer_formset):  # Add index for form number
                    for field in form:
                        for error in field.errors:
                            messages.error(
                                request,
                                f"Customer {i+1} Error in field '{field.label}': {error}",  # Display form number
                            )
                    for (
                        error
                    ) in (
                        form.non_field_errors()
                    ):  # handle non field errors for each form in the formset
                        messages.error(request, f"Customer {i+1} Error: {error}")

                for error in customer_formset.non_form_errors():
                    messages.error(request, f"Customer Formset Error: {error}")
    else:
        print("GET Request")
        delivery_form = DeliveryForm()
        customer_formset = DeliveryCustomerFormSet(
            queryset=DeliveryCustomer.objects.none()
        )

    monthly_customers = list(
        Customer.objects.filter(customer_type="monthly").values("id", "name")
    )
    in_hand_customers = list(
        Customer.objects.filter(customer_type="in_hand").values("id", "name")
    )
    return render(
        request,
        "plant/add_delivery.html",
        {
            "delivery_form": delivery_form,
            "customer_formset": customer_formset,
            "driver": driver,
            "monthly_customers": json.dumps(monthly_customers, cls=DjangoJSONEncoder),
            "in_hand_customers": json.dumps(in_hand_customers, cls=DjangoJSONEncoder),
        },
    )


def all_deliveries(request):
    """
    View to display all deliveries.
    """
    deliveries = Delivery.objects.select_related(
        "customer", "driver", "bill"
    )  # Optimizes by selecting related models
    context = {
        "deliveries": deliveries,
    }
    return render(request, "plant/all_deliveries.html", context)


def bill_detail(request, delivery_id):
    delivery = get_object_or_404(Delivery, id=delivery_id)
    bill_total = delivery.calculate_bill()

    context = {
        "delivery": delivery,
        "bill_total": bill_total,
        "customer": delivery.customer,
        "driver": delivery.driver,
    }
    return render(request, "plant/bill_detail.html", context)


def expenses(request):
    today = timezone.now().date()
    month = request.GET.get("month", today.month)
    year = request.GET.get("year", today.year)

    # Filter expenses for the selected month and year
    expenses = MonthlyExpense.objects.filter(date__month=month, date__year=year)

    # Calculate total expenses for the month
    total_expenses = MonthlyExpense.total_monthly_expense(month, year)

    context = {
        "expenses": expenses,
        "total_expenses": total_expenses,
        "today": today,
        "month": month,
        "year": year,
    }

    return render(request, "expenses/expenses.html", context)


def add_expense(request):
    if request.method == "POST":
        form = MonthlyExpenseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("expenses")  # Redirect to the list view after saving
    else:
        form = MonthlyExpenseForm()
    return render(request, "expenses/add_expense.html", {"form": form})


from django.utils.timezone import now


def monthly_summary(request):
    # Get filter month from request or default to the current month
    filter_month = request.GET.get("month", now().strftime("%Y-%m"))
    year, month = map(int, filter_month.split("-"))

    drivers = User.objects.filter(role="DRIVER")
    summary_data = []

    # Initialize totals
    total_jars = total_received = total_due = 0

    for driver in drivers:
        # Total jars delivered by the driver
        total_jars_driver = (
            Delivery.objects.filter(
                trip__driver=driver, trip__date__year=year, trip__date__month=month
            ).aggregate(total=Sum("total_jars"))["total"]
            or 0
        )

        # Total amount collected by the driver (based on DeliveryCustomer records)
        amount_received = (
            DeliveryCustomer.objects.filter(
                delivery__trip__driver=driver,
                delivery__trip__date__year=year,
                delivery__trip__date__month=month,
            ).aggregate(total=Sum("total_price"))["total"]
            or 0
        )

        # Calculate total amount
        total_amount = (
            DeliveryCustomer.objects.filter(
                delivery__trip__driver=driver,
                delivery__trip__date__year=year,
                delivery__trip__date__month=month,
            )
            .annotate(calculated_price=F("quantity") * F("price_per_jar"))
            .aggregate(total=Sum("calculated_price", output_field=DecimalField()))[
                "total"
            ]
            or total_jars_driver
            * 40  # Default to 40 per jar if no specific price is provided
        )

        # Calculate due amount
        due_amount = total_amount - amount_received

        # Add data to summary
        summary_data.append(
            {
                "name": driver.full_name,
                "total_jars": total_jars_driver,
                "total_amount": total_amount,
                "amount_received": amount_received,
                "due_amount": due_amount,
            }
        )

        # Update totals
        total_jars += total_jars_driver
        total_received += amount_received
        total_due += due_amount

    # Render the summary template with context
    return render(
        request,
        "expenses/monthly_summary.html",
        {
            "summary_data": summary_data,
            "filter_month": filter_month,
            "today": now(),
            "total_jars": total_jars,
            "total_received": total_received,
            "total_due": total_due,
        },
    )


def jar_in_out_list(request):
    """
    Shows a list of all JarInOut records, sorted newest first.
    """
    records = JarInOut.objects.order_by("-created_at")
    return render(request, "records/jar_in_out_list.html", {"records": records})


def jar_in_out_create(request):
    if request.method == "POST":
        form = JarInOutForm(request.POST)
        if form.is_valid():
            jar_in_out = form.save(commit=False)
            jar_in_out.vehicle_number = request.POST.get(
                "vehicle_number"
            )  # Save vehicle number
            jar_in_out.save()
            return redirect("jar_in_out_list")  # Redirect to list view
    else:
        form = JarInOutForm()

    context = {"form": form}
    return render(request, "records/jar_in_out_create.html", context)


def get_filler_vehicle(request, filler_id):
    try:
        filler = Filler.objects.get(id=filler_id)
        return JsonResponse({"vehicle_number": filler.vehicle_number})
    except Filler.DoesNotExist:
        return JsonResponse({"error": "Filler not found"}, status=404)


def bill_list(request):
    bills = Bill.objects.order_by("-date_issued")
    return render(request, "records/bill_list.html", {"bills": bills})


def bill_create(request):
    """
    Allows staff to create a new Bill record.
    Shows `online_method` field only if payment_category == 'online'.
    """
    if request.method == "POST":
        form = BillForm(request.POST)
        if form.is_valid():
            bill = form.save(commit=False)
            # Optional: if you want to store who created the bill
            # if request.user.is_authenticated:
            #     bill.added_by = request.user
            bill.save()
            return redirect(reverse("bill_list"))
    else:
        form = BillForm()

    return render(request, "records/bill_create.html", {"form": form})


def jar_cap_list(request):
    """
    A single page that shows the single jar cap record in a table
    and has two forms:
      - inc_form: IncreaseJarCapForm
      - dec_form: DecreaseJarCapForm
    If quantity < 7, display a 'LOW STOCK' warning.
    When decreasing, set usage_date to tomorrow.
    """
    # Get or create a single row for jar caps
    jarcap, _ = JarCap.objects.get_or_create(
        pk=1, defaults={"quantity_in_bora": 0, "last_updated": datetime.now().date()}
    )

    if request.method == "POST":
        if "increase" in request.POST:
            # The user clicked the "Add" button
            inc_form = IncreaseJarCapForm(request.POST)
            dec_form = DecreaseJarCapForm()  # empty
            if inc_form.is_valid():
                added_qty = inc_form.cleaned_data["added_bora"]
                jarcap.quantity_in_bora += added_qty
                jarcap.last_updated = timezone.now().date()  # updated today
                # usage_date might remain unchanged
                jarcap.save()
                return redirect("jar_cap_list")

        elif "decrease" in request.POST:
            # The user clicked the "Use" button
            dec_form = DecreaseJarCapForm(request.POST)
            inc_form = IncreaseJarCapForm()  # empty
            if dec_form.is_valid():
                used_qty = dec_form.cleaned_data["used_bora"]
                # Subtract but don’t go below 0
                jarcap.quantity_in_bora = max(0, jarcap.quantity_in_bora - used_qty)
                jarcap.last_updated = timezone.now().date()  # updated today

                # Set usage_date to tomorrow
                jarcap.usage_date = timezone.now().date() + timedelta(days=1)

                jarcap.save()
                return redirect("jar_cap_list")

    else:
        inc_form = IncreaseJarCapForm()
        dec_form = DecreaseJarCapForm()

    # Render the page with the single record + forms
    return render(
        request,
        "records/jar_cap_list.html",
        {
            "jarcap": jarcap,
            "inc_form": inc_form,
            "dec_form": dec_form,
        },
    )


def jar_cap_create(request):
    """
    Create a new JarCap entry: quantity_in_bora, price_per_bora, date_brought.
    Increases the inventory.
    """
    if request.method == "POST":
        form = JarCapForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("jar_cap_list")
    else:
        form = JarCapForm()
    return render(request, "records/jar_cap_create.html", {"form": form})


def filler_list(request):
    """Display all fillers in a table."""
    fillers = Filler.objects.all()
    return render(request, "filler/filler_list.html", {"fillers": fillers})


def add_ledger_entry(request):
    """Add a new ledger entry for a filler."""
    if request.method == "POST":
        form = FillerLedgerForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("filler_list")  # Redirect to filler list or relevant page
    else:
        form = FillerLedgerForm()
    return render(request, "filler/add_ledger_entry.html", {"form": form})


def filler_detail(request, pk):
    """Display the ledger records and jar records for a specific filler."""
    filler = get_object_or_404(Filler, pk=pk)
    ledger_records = filler.ledger_entries.select_related("jar_in_out")
    return render(
        request,
        "filler/filler_detail.html",
        {"filler": filler, "ledger_records": ledger_records},
    )
