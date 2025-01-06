from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from account.models import Attendance, User
from .forms import BillForm, DecreaseJarCapForm, DeliveryForm, IncreaseJarCapForm, JarCapForm, JarInOutForm, MonthlyExpenseForm
from .models import Bill, Customer, Delivery, Filler, JarCap, JarInOut
from datetime import datetime, timedelta
from django.db.models import Sum , Avg
from django.contrib import messages
from django.contrib.auth.decorators import login_required


from .models import MonthlyExpense


def delivery(request):
    today = timezone.now().date()
    filter_date = request.GET.get('date', today)

    if isinstance(filter_date, str):
        filter_date = datetime.strptime(filter_date, '%Y-%m-%d').date()

    # Filter deliveries by the selected date
    deliveries = Delivery.objects.filter(date=filter_date)

    # Calculate totals
    total_jars = deliveries.aggregate(total=Sum('quantity'))['total'] or 0
    total_leaks = deliveries.aggregate(total=Sum('leak_count'))['total'] or 0
    total_half_caps = deliveries.aggregate(total=Sum('half_caps_count'))['total'] or 0
    total_delivered_safely = deliveries.aggregate(total=Sum('delivered_count'))['total'] or 0
    total_returned = deliveries.aggregate(total=Sum('returned_count'))['total'] or 0

    context = {
        'deliveries': deliveries,
        'today': today,
        'filter_date': filter_date,
        'total_jars': total_jars,
        'total_leaks': total_leaks,
        'total_half_caps': total_half_caps,
        'total_delivered_safely': total_delivered_safely,
        'total_returned': total_returned,
    }

    return render(request, 'plant/delivery.html', context)



@login_required
def add_delivery(request):
    driver = request.user  
    # if driver.role != 'DRIVER' : 
    #     messages.error(request, "Only drivers can add deliveries.")
    #     return redirect('home')

    if request.method == 'POST':
        form = DeliveryForm(request.POST)
        if form.is_valid():
            delivery = form.save(commit=False)
            delivery.driver = driver  # Assign the logged-in driver (User instance)
            delivery.save()
            messages.success(request, "Delivery added successfully.")
            return redirect('add_delivery')
    else:
        form = DeliveryForm()

    return render(request, 'plant/add_delivery.html', {'form': form, 'driver': driver})


def all_deliveries(request):
    """
    View to display all deliveries.
    """
    deliveries = Delivery.objects.select_related('customer', 'driver', 'bill')  # Optimizes by selecting related models
    context = {
        "deliveries": deliveries,
    }
    return render(request, 'plant/all_deliveries.html', context)



def bill_detail(request, delivery_id):
    delivery = get_object_or_404(Delivery, id=delivery_id)
    bill_total = delivery.calculate_bill()

    context = {
        "delivery": delivery,
        "bill_total": bill_total,
        "customer": delivery.customer,
        "driver": delivery.driver,
    }
    return render(request, 'plant/bill_detail.html', context)




def expenses(request):
    today = timezone.now().date()
    month = request.GET.get('month', today.month)
    year = request.GET.get('year', today.year)

    # Filter expenses for the selected month and year
    expenses = MonthlyExpense.objects.filter(date__month=month, date__year=year)

    # Calculate total expenses for the month
    total_expenses = MonthlyExpense.total_monthly_expense(month, year)

    context = {
        'expenses': expenses,
        'total_expenses': total_expenses,
        'today': today,
        'month': month,
        'year': year,
    }

    return render(request, 'expenses/expenses.html', context)



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
    # Filter month from request
    filter_month = request.GET.get('month', now().strftime('%Y-%m'))
    year, month = map(int, filter_month.split('-'))

    drivers = User.objects.filter(role='DRIVER')
    summary_data = []

    total_jars = total_received = total_due = 0

    for driver in drivers:
        # Total jars delivered by the driver
        total_jars_driver = Delivery.objects.filter(driver=driver, date__year=year, date__month=month).aggregate(
            total=Sum('quantity'))['total'] or 0

        # Total amount collected by the driver (assuming "amount_received" is captured in MonthlyExpense for DAILY_EXPENSE type)
        amount_received = MonthlyExpense.objects.filter(
            expense_type=MonthlyExpense.DAILY_EXPENSE,
            date__year=year,
            date__month=month,
            remarks__icontains=driver.full_name  # Assuming remarks include driver's name
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Total amount (assuming 1 jar = 40)
        total_amount = total_jars_driver * 40

        # Due amount
        due_amount = total_amount - amount_received

        # Add to summary
        summary_data.append({
            'name': driver.full_name,
            'total_jars': total_jars_driver,
            'total_amount': total_amount,
            'amount_received': amount_received,
            'due_amount': due_amount,
        })

        # Update overall totals
        total_jars += total_jars_driver
        total_received += amount_received
        total_due += due_amount

    return render(request, 'expenses/monthly_summary.html', {
        'summary_data': summary_data,
        'filter_month': filter_month,
        'today': now(),
        'total_jars': total_jars,
        'total_received': total_received,
        'total_due': total_due,
    })

def jar_in_out_list(request):
    """
    Shows a list of all JarInOut records, sorted newest first.
    """
    records = JarInOut.objects.order_by('-created_at')
    return render(request, 'records/jar_in_out_list.html', {'records': records})



def jar_in_out_create(request):
    if request.method == 'POST':
        form = JarInOutForm(request.POST)
        if form.is_valid():
            jar_in_out = form.save(commit=False)
            jar_in_out.vehicle_number = request.POST.get('vehicle_number')  # Save vehicle number
            jar_in_out.save()
            return redirect('jar_in_out_list')  # Redirect to list view
    else:
        form = JarInOutForm()

    context = {'form': form}
    return render(request, 'records/jar_in_out_create.html', context)


def get_filler_vehicle(request, filler_id):
    try:
        filler = Filler.objects.get(id=filler_id)
        return JsonResponse({'vehicle_number': filler.vehicle_number})
    except Filler.DoesNotExist:
        return JsonResponse({'error': 'Filler not found'}, status=404)


def bill_list(request):
    bills = Bill.objects.order_by('-date_issued')
    return render(request, 'records/bill_list.html', {'bills': bills})

def bill_create(request):
    """
    Allows staff to create a new Bill record.
    Shows `online_method` field only if payment_category == 'online'.
    """
    if request.method == 'POST':
        form = BillForm(request.POST)
        if form.is_valid():
            bill = form.save(commit=False)
            # Optional: if you want to store who created the bill
            # if request.user.is_authenticated:
            #     bill.added_by = request.user
            bill.save()
            return redirect(reverse('bill_list'))
    else:
        form = BillForm()

    return render(request, 'records/bill_create.html', {'form': form})




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
        pk=1,
        defaults={'quantity_in_bora': 0, 'last_updated': datetime.now().date()}
    )

    if request.method == 'POST':
        if 'increase' in request.POST:
            # The user clicked the "Add" button
            inc_form = IncreaseJarCapForm(request.POST)
            dec_form = DecreaseJarCapForm()  # empty
            if inc_form.is_valid():
                added_qty = inc_form.cleaned_data['added_bora']
                jarcap.quantity_in_bora += added_qty
                jarcap.last_updated = timezone.now().date()  # updated today
                # usage_date might remain unchanged
                jarcap.save()
                return redirect('jar_cap_list')

        elif 'decrease' in request.POST:
            # The user clicked the "Use" button
            dec_form = DecreaseJarCapForm(request.POST)
            inc_form = IncreaseJarCapForm()  # empty
            if dec_form.is_valid():
                used_qty = dec_form.cleaned_data['used_bora']
                # Subtract but don’t go below 0
                jarcap.quantity_in_bora = max(0, jarcap.quantity_in_bora - used_qty)
                jarcap.last_updated = timezone.now().date()  # updated today

                # Set usage_date to tomorrow
                jarcap.usage_date = timezone.now().date() + timedelta(days=1)

                jarcap.save()
                return redirect('jar_cap_list')

    else:
        inc_form = IncreaseJarCapForm()
        dec_form = DecreaseJarCapForm()

    # Render the page with the single record + forms
    return render(request, 'records/jar_cap_list.html', {
        'jarcap': jarcap,
        'inc_form': inc_form,
        'dec_form': dec_form,
    })



def jar_cap_create(request):
    """
    Create a new JarCap entry: quantity_in_bora, price_per_bora, date_brought.
    Increases the inventory.
    """
    if request.method == 'POST':
        form = JarCapForm(request.POST)
        if form.is_valid():
            form.save()  
            return redirect('jar_cap_list')
    else:
        form = JarCapForm()

    return render(request, 'records/jar_cap_create.html', {'form': form})

