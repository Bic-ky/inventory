from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Sum, F, DecimalField
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from datetime import datetime, timedelta, date

from django.utils.timezone import now
from django.db.models import Prefetch

from django.db import transaction


from product import models

from .forms import (
    BillForm,
    DecreaseJarCapForm,
    DeliveryForm,
    IncreaseJarCapForm,
    JarCapForm,
    JarInOutForm,
    MonthlyExpenseForm,
    DeliveryInventoryFormSet,
    MonthlyCustomerDeliveryForm,
    InHandDeliveryForm,
    InventoryReportForm,
    DeliveryItem,
)

from account.models import User
from product.models import (
    Bill,
    Delivery,
    Filler,
    FillerLedger,
    JarCap,
    JarInOut,
    MonthlyExpense,
    CustomerPrice,
    InventoryReport,
    WaterProduct,
)


def delivery(request):
    deliveries = Delivery.objects.all()
    context = {"deliveries": deliveries}
    return render(request, "plant/delivery.html", context)


def delivery_details(request, delivery_id):
    delivery = get_object_or_404(Delivery, id=delivery_id)

    # Prepare the data for JSON response
    data = {
        "id": delivery.id,
        "driver": delivery.driver.full_name,
        "date": delivery.delivery_date,
        "status": delivery.status,
        "inventory_items": [
            {
                "water_product": item.water_product.__str__(),
                "quantity": item.quantity,
            }
            for item in delivery.inventory_items.all()
        ],
        "delivery_items": [
            {
                "water_product": item.water_product.__str__(),
                "customer_name": (
                    item.monthly_customer.name
                    if item.monthly_customer
                    else item.customer_name
                ),
                "quantity": item.quantity,
                "price_per_unit": item.price_per_unit,
                "total_amount": item.total_amount,
            }
            for item in delivery.delivery_items.all()
        ],
        "inventory_reports": [
            {
                "water_product": report.water_product.__str__(),
                "leaks": report.leaks,
                "returns": report.returns,
                "half_caps": report.half_caps,
            }
            for report in delivery.reports.all()
        ],
    }
    return JsonResponse(data)


@login_required
def add_delivery(request):
    active_products = WaterProduct.objects.filter(is_active=True)

    if request.method == "POST":
        delivery_form = DeliveryForm(request.POST)
        inventory_formset = DeliveryInventoryFormSet(request.POST, prefix="inventory")

        if delivery_form.is_valid() and inventory_formset.is_valid():
            # check if total quantity is zero
            total_quantity = sum(
                int(form.cleaned_data["quantity"])
                for form in inventory_formset
                if form.cleaned_data.get("quantity", 0) > 0
            )
            if total_quantity == 0:
                messages.error(request, "Please add at least one item to the delivery.")
                return render(
                    request,
                    "plant/add_delivery.html",
                    {
                        "delivery_form": delivery_form,
                        "inventory_formset": inventory_formset,
                        "active_products": active_products,
                    },
                )
            try:
                with transaction.atomic():
                    # Save delivery
                    delivery = delivery_form.save(commit=False)
                    delivery.driver = request.user
                    delivery.save()

                    # Save inventory items
                    inventory_items = inventory_formset.save(commit=False)
                    for item in inventory_items:
                        if item.quantity > 0:  # Only save items with quantity
                            item.delivery = delivery
                            item.save()

                    messages.success(request, "Delivery created successfully!")
                    return redirect(
                        reverse(
                            "record_delivery",
                            kwargs={"delivery_id": delivery.id},
                        )
                    )
            except Exception as e:
                messages.error(request, f"Error creating delivery: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        delivery_form = DeliveryForm()
        inventory_formset = DeliveryInventoryFormSet(prefix="inventory")

    return render(
        request,
        "plant/add_delivery.html",
        {
            "delivery_form": delivery_form,
            "inventory_formset": inventory_formset,
            "active_products": active_products,  # Pass active products to the template
        },
    )


@login_required
def record_delivery(request, delivery_id):
    delivery = get_object_or_404(
        Delivery, id=delivery_id, driver=request.user, status="ONGOING"
    )

    # Initialize the forms to ensure they're available in all cases
    monthly_form = MonthlyCustomerDeliveryForm()
    inhand_form = InHandDeliveryForm()
    report_form = InventoryReportForm()

    # Calculate remaining inventory
    inventory_taken = {
        item.water_product_id: item.quantity for item in delivery.inventory_items.all()
    }

    delivered = (
        DeliveryItem.objects.filter(delivery=delivery)
        .values("water_product")
        .annotate(total=Sum("quantity"))
    )

    reported = (
        InventoryReport.objects.filter(delivery=delivery)
        .values("water_product")
        .annotate(total=Sum(F("leaks") + F("returns") + F("half_caps")))
    )

    remaining_inventory = {}
    for product_id, taken in inventory_taken.items():
        delivered_qty = next(
            (
                item["total"]
                for item in delivered
                if item["water_product"] == product_id
            ),
            0,
        )
        reported_qty = next(
            (item["total"] for item in reported if item["water_product"] == product_id),
            0,
        )
        remaining_inventory[product_id] = taken - delivered_qty - reported_qty

    remaining_inventory_with_products = {}
    for product_id, quantity in remaining_inventory.items():
        product = WaterProduct.objects.get(id=product_id)
        remaining_inventory_with_products[product] = quantity

    if request.method == "POST":
        if "monthly_delivery" in request.POST:
            form = MonthlyCustomerDeliveryForm(request.POST)
            if form.is_valid():
                delivery_item = form.save(commit=False)
                delivery_item.delivery = delivery

                # Check if enough inventory is available
                remaining = remaining_inventory.get(delivery_item.water_product.id, 0)
                if remaining < delivery_item.quantity:
                    messages.error(
                        request,
                        f"Not enough {delivery_item.water_product} available. Remaining: {remaining}",
                    )
                    return redirect("record_delivery", delivery_id=delivery_id)

                # Get customer-specific price
                customer_price = CustomerPrice.objects.filter(
                    monthly_customer=form.cleaned_data["monthly_customer"],
                    water_product=form.cleaned_data["water_product"],
                    is_active=True,
                ).first()

                if customer_price:
                    delivery_item.price_per_unit = customer_price.price
                    delivery_item.save()
                    messages.success(
                        request, "Monthly customer delivery recorded successfully!"
                    )
                else:
                    messages.error(
                        request, "No price found for this customer and product!"
                    )

                return redirect("record_delivery", delivery_id=delivery_id)

        elif "inhand_delivery" in request.POST:
            # Make a mutable copy of request.POST
            mutable_post = request.POST.copy()

            # Set customer name and phone as in-hand delivery defaults
            mutable_post["customer_name"] = "In-hand"
            mutable_post["customer_phone"] = "0000000000"

            # Pass the modified data to the form
            form = InHandDeliveryForm(mutable_post)

            if form.is_valid():
                delivery_item = form.save(commit=False)
                delivery_item.delivery = delivery

                # Check if enough inventory is available
                remaining = remaining_inventory.get(delivery_item.water_product.id, 0)
                if remaining < delivery_item.quantity:
                    messages.error(
                        request,
                        f"Not enough {delivery_item.water_product} available. Remaining: {remaining}",
                    )
                    return redirect("record_delivery", delivery_id=delivery_id)
                delivery_item.save()
                messages.success(request, "In-hand delivery recorded successfully!")
                return redirect("record_delivery", delivery_id=delivery_id)
            else:
                # Display validation errors
                for field, error_list in form.errors.items():
                    for error in error_list:
                        messages.error(request, f"{field}: {error}")

        elif "inventory_report" in request.POST:
            form = InventoryReportForm(request.POST)
            if form.is_valid():
                report = form.save(commit=False)
                report.delivery = delivery

                # Check if enough inventory is available
                remaining = remaining_inventory.get(report.water_product.id, 0)
                total_reported = report.leaks + report.returns + report.half_caps
                if remaining < total_reported:
                    messages.error(
                        request,
                        f"Not enough {report.water_product} available. Remaining: {remaining}",
                    )
                    return redirect("record_delivery", delivery_id=delivery_id)

                report.save()
                messages.success(request, "Inventory report recorded successfully!")
                return redirect("record_delivery", delivery_id=delivery_id)

    context = {
        "delivery": delivery,
        "monthly_form": monthly_form,
        "inhand_form": inhand_form,
        "report_form": report_form,
        "delivery_items": delivery.delivery_items.all().order_by("-id"),
        "inventory_reports": delivery.reports.all().order_by("-id"),
        "remaining_inventory": remaining_inventory_with_products,
    }

    return render(request, "plant/record_delivery.html", context)


@login_required
def complete_delivery(request, delivery_id):
    delivery = get_object_or_404(
        Delivery, id=delivery_id, driver=request.user, status="ONGOING"
    )

    # Calculate total quantity delivered
    total_quantity = DeliveryItem.objects.filter(delivery_id=delivery_id).aggregate(
        total_quantity=Sum("quantity")
    )["total_quantity"]
    total_quantity_deliver = total_quantity or 0

    # Calculate total amount
    total_amount = (
        DeliveryItem.objects.filter(delivery_id=delivery_id)
        .annotate(total_item_amount=F("quantity") * F("price_per_unit"))
        .aggregate(total_amount=Sum("total_item_amount"))["total_amount"]
    )
    total_amount = total_amount or Decimal(0)

    # Calculate the total for leaks, returns, and half_caps for this delivery
    totals = InventoryReport.objects.filter(delivery_id=delivery_id).aggregate(
        total_leaks=Sum("leaks"),
        total_returns=Sum("returns"),
        total_half_caps=Sum("half_caps"),
    )
    # Accessing the totals
    total_leaks = totals.get("total_leaks", 0)  # Default to 0 if no records
    total_returns = totals.get("total_returns", 0)
    total_half_caps = totals.get("total_half_caps", 0)

    if request.method == "POST":
        delivery.status = "COMPLETED"
        delivery.end_time = timezone.now()
        delivery.save()
        return redirect("delivery")
    else:
        messages.error(
            request,
            "Inventory counts do not match. Please verify all deliveries and reports.",
        )

    return render(
        request,
        "plant/complete_delivery.html",
        {
            "delivery": delivery,
            "total_quantity": total_quantity_deliver,
            "total_amount": total_amount,
            "total_leaks": total_leaks,
            "total_returns": total_returns,
            "total_half_caps": total_half_caps,
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
    Shows a grouped list of all JarInOut records, organized by Filler with date filter.
    """
    # Get date filter parameters
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    # Base queryset
    jar_in_out_queryset = JarInOut.objects.order_by("-created_at")

    # Apply date filter if provided
    if start_date:
        jar_in_out_queryset = jar_in_out_queryset.filter(
            created_at__date__gte=start_date
        )
    if end_date:
        jar_in_out_queryset = jar_in_out_queryset.filter(created_at__date__lte=end_date)

    # Prefetch only the most recent 5 records per filler
    jar_in_out_prefetch = Prefetch(
        "jarinout_set",
        queryset=jar_in_out_queryset,
        to_attr="recent_records",  # Store the prefetched queryset as a custom attribute
    )

    fillers = Filler.objects.prefetch_related(jar_in_out_prefetch).order_by(
        "contact_person"
    )

    context = {
        "fillers": fillers,
        "start_date": start_date,
        "end_date": end_date,
    }
    return render(request, "records/jar_in_out_list.html", context)


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


def filler_ledger_detail(request, filler_id):
    """Display financial details and ledger records for a specific filler."""
    filler = get_object_or_404(Filler, pk=filler_id)
    ledger_records = FillerLedger.objects.filter(filler=filler).order_by("date")

    # Initialize cumulative balance
    cumulative_balance_due = Decimal("0.00")
    for record in ledger_records:
        # Calculate cumulative balance
        cumulative_balance_due += record.jar_in_out.receivable_amount
        cumulative_balance_due -= record.amount_received
        # Update record's balance due
        record.balance_due = cumulative_balance_due

    # Calculate cumulative totals
    total_receivable = ledger_records.aggregate(
        total=Sum("jar_in_out__receivable_amount")
    )["total"] or Decimal("0.00")
    total_received = ledger_records.aggregate(total=Sum("amount_received"))[
        "total"
    ] or Decimal("0.00")
    total_balance_due = cumulative_balance_due

    context = {
        "filler": filler,
        "ledger_records": ledger_records,
        "total_receivable": total_receivable,
        "total_received": total_received,
        "total_balance_due": total_balance_due,
    }
    return render(request, "records/filler_ledger_detail.html", context)


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


def filler_detail(request, pk):
    """Display the ledger records and jar records for a specific filler."""
    filler = get_object_or_404(Filler, pk=pk)
    ledger_records = filler.ledger_entries.select_related("jar_in_out")
    return render(
        request,
        "filler/filler_detail.html",
        {"filler": filler, "ledger_records": ledger_records},
    )
