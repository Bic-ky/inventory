from datetime import datetime, timezone
from django.utils.timezone import localtime
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages, auth
from django.core.exceptions import PermissionDenied
from django.contrib.auth import authenticate, login as auth_login
from django.urls import reverse

from product.models import Delivery, Driver, Jar, JarInOut, MonthlyExpense, Vehicle

from .forms import (
    AttendanceForm,
    CustomPasswordChangeForm,
    RegistrationForm,
    LoginForm,
    SalaryRecordForm,
)
from .models import Attendance, SalaryRecord, User

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.db.models import Sum

from django.utils.timezone import is_naive, make_aware
from django.utils import timezone


def check_role_admin(user):
    if user.role == User.ADMIN:
        return True
    else:
        raise PermissionDenied


def check_role_staff(user):
    if user.role == User.STAFF:
        return True
    else:
        raise PermissionDenied


def check_role_driver(user):
    if user.role == User.DRIVER:
        return True
    else:
        raise PermissionDenied


def detectUser(user):
    if user.role == User.ADMIN:
        return "admin_dashboard"
    elif user.role == User.STAFF:
        return "staff_dashboard"
    elif user.role == User.DRIVER:
        return "driver_dashboard"
    else:
        # Return None for roles that are not admin or staff
        return redirect("login")


def myAccount(request):
    user = request.user
    if user.is_authenticated:
        redirect_url = detectUser(user)
        if redirect_url:
            return redirect(redirect_url)  # Redirect to admin or staff dashboard
        else:
            messages.success(request, "You have been registered successfully.")
            return redirect("login")  # Redirect to the login page
    else:
        messages.error(request, "You need to log in to access your account.")
        return redirect("login")  # Redirect to login page if not authenticated


def index(request):
    return render(request, "index.html")


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            auth_login(request, user)
            return redirect("myAccount")  # Redirect to myAccount after registration
    else:
        form = RegistrationForm()

    return render(request, "register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in!")
        return redirect("myAccount")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data["phone_number"]
            password = form.cleaned_data["password"]

            user = authenticate(request, phone_number=phone_number, password=password)
            if user is not None:
                auth_login(request, user)
                messages.success(request, "You are now logged in.")
                return redirect("myAccount")
            else:
                messages.error(
                    request, "Authentication failed. Please check your credentials."
                )
        else:
            messages.error(request, "Invalid form submission.")
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})


def logout(request):
    auth.logout(request)
    messages.info(request, "You are logged out.")
    return redirect("login")


@login_required
@user_passes_test(check_role_admin)  # Replace with your admin role check
def admin_dashboard(request):
    today = timezone.now().date()

    # Stats for the dashboard
    total_deliveries = Delivery.objects.count()
    total_jars_in = JarInOut.objects.aggregate(total_in=Sum("jar_in"))["total_in"] or 0
    total_jars_out = (
        JarInOut.objects.aggregate(total_out=Sum("jar_out"))["total_out"] or 0
    )
    total_expenses = MonthlyExpense.objects.aggregate(total=Sum("amount"))["total"] or 0

    # Recent deliveries (latest 10)
    recent_deliveries = Delivery.objects.select_related("customer", "driver").order_by(
        "-date"
    )[:10]

    context = {
        "total_deliveries": total_deliveries,
        "total_jars_in": total_jars_in,
        "total_jars_out": total_jars_out,
        "total_expenses": total_expenses,
        "deliveries": recent_deliveries,
    }
    return render(request, "account/admin_dashboard.html", context)


@login_required
@user_passes_test(check_role_staff)
def staff_dashboard(request):
    today_date = datetime.now()

    # Get all drivers
    drivers = Driver.objects.all()

    # Get all vehicles with assigned drivers
    vehicles = Vehicle.objects.all()

    # Get Jar details (available jars, sold jars, returned jars, and damaged jars)
    jars_available = (
        Jar.objects.aggregate(total_available=Sum("available_jars"))["total_available"]
        or 0
    )
    jars_sold = Jar.objects.aggregate(total_sold=Sum("sold_jars"))["total_sold"] or 0
    jars_returned = (
        Jar.objects.aggregate(total_returned=Sum("returned_jars"))["total_returned"]
        or 0
    )
    jars_damaged = (
        Jar.objects.aggregate(total_damaged=Sum("damaged_jars"))["total_damaged"] or 0
    )

    # Get attendance data (for today)
    attendance_records = Attendance.objects.all()

    # Create context to send to the template
    context = {
        "today_date": today_date,
        "drivers": drivers,
        "vehicles": vehicles,
        "jars_available": jars_available,
        "jars_sold": jars_sold,
        "jars_returned": jars_returned,
        "jars_damaged": jars_damaged,
        "attendance_records": attendance_records,
    }
    return render(request, "account/staff_dashboard.html", context)


@login_required
@user_passes_test(check_role_driver)
def driver_dashboard(request):
    # Get detailed records for the driver
    # records = (
    #     Delivery.objects.filter(driver__role="DRIVER")
    #     .values("driver__full_name")
    #     .annotate(
    #         jars_delivered=Sum("delivered_count"),
    #         jars_returned=Sum("returned_count"),
    #         jars_damaged=Sum("leak_count") + Sum("half_caps_count"),
    #     )
    # )

    # context = {
    #     "records": records,
    # }
    return render(request, "account/driver_dashboard.html")


def attendance(request):
    # Get today's date
    today = timezone.now().date()

    # Get the filter date from request or default to today
    filter_date_str = request.GET.get("date", today.strftime("%Y-%m-%d"))
    try:
        filter_date = datetime.strptime(filter_date_str, "%Y-%m-%d").date()
    except ValueError:
        filter_date = today

    # Ensure the filter date range covers the entire day
    start_of_day = make_aware(datetime.combine(filter_date, datetime.min.time()))
    end_of_day = make_aware(datetime.combine(filter_date, datetime.max.time()))

    # Query attendance records within the filtered date
    attendance_records = Attendance.objects.filter(
        check_in__range=(start_of_day, end_of_day)
    )

    # Aggregate total hours worked
    total_hours_worked = (
        attendance_records.aggregate(Sum("hours_worked"))["hours_worked__sum"] or 0
    )

    context = {
        "attendance_records": attendance_records,
        "filter_date": filter_date,
        "total_hours_worked": round(total_hours_worked, 2),
        "today": today,
    }

    return render(request, "account/attendance.html", context)


def add_attendance(request):
    # Check if an attendance record already exists for today
    today = datetime.now().date()
    existing_attendance = Attendance.objects.filter(
        user=request.user, check_in__date=today
    ).first()

    if request.method == "POST":
        if existing_attendance:
            form = AttendanceForm(
                request.POST, instance=existing_attendance, logged_in_user=request.user
            )
        else:
            form = AttendanceForm(request.POST, logged_in_user=request.user)

        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.is_present = bool(attendance.check_in)

            # Ensure timezone awareness
            if attendance.check_in and is_naive(attendance.check_in):
                attendance.check_in = make_aware(attendance.check_in)
            if attendance.check_out and is_naive(attendance.check_out):
                attendance.check_out = make_aware(attendance.check_out)

            # Calculate hours worked if check-out is provided
            if attendance.check_in and attendance.check_out:
                attendance.hours_worked = (
                    attendance.check_out - attendance.check_in
                ).total_seconds() / 3600

            attendance.save()
            return redirect("attendance")  # Redirect to attendance listing page
    else:
        form = AttendanceForm(instance=existing_attendance, logged_in_user=request.user)

    return render(
        request,
        "account/add_attendance.html",
        {
            "form": form,
            "is_edit": bool(
                existing_attendance
            ),  # To indicate if editing an existing record
        },
    )


def get_user_attendance(request):
    user_id = request.GET.get("user_id")
    month = request.GET.get("month")

    if user_id and month:
        year, month = map(int, month.split("-"))
        total_hours = (
            Attendance.objects.filter(
                user_id=user_id, check_in__year=year, check_in__month=month
            ).aggregate(total=Sum("hours_worked"))["total"]
            or 0
        )

        # Calculate extra hours (assume base is 12 hours)
        extra_hours = max(0, total_hours - 12)
        return JsonResponse({"total_hours": total_hours, "extra_hours": extra_hours})

    return JsonResponse({"error": "Invalid request"}, status=400)


def admin_change_password(request):
    if request.method == "POST":
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Update session
            messages.success(request, "Your password was successfully updated!")
            logout(request)  # Log out the user

            if user.role == 1:
                return redirect("admin_dashboard")
    else:
        # Pass user=request.user to initialize the form with the user's data
        form = CustomPasswordChangeForm(user=request.user)
    return render(request, "account/change_password.html", {"form": form})


from collections import defaultdict


def daily_record(request):
    """
    Displays the number of jars each driver took for a particular day,
    along with leak jars, returned, and half caps in a sub-table.
    """

    today = datetime.now().date()

    filter_date_str = request.GET.get("date")
    if filter_date_str:
        try:
            filter_date = datetime.strptime(filter_date_str, "%Y-%m-%d").date()
        except ValueError:
            filter_date = today
    else:
        filter_date = today

    # All deliveries for the selected date
    deliveries = Delivery.objects.filter(date=filter_date)

    # 1) Aggregate by driver
    driver_summaries = deliveries.values("driver__id", "driver__full_name").annotate(
        total_leaks=Sum("leak_count"),
        total_half_caps=Sum("half_caps_count"),
        total_returns=Sum("returned_count"),
    )

    # 2) Build a dict: { driver_id: [Delivery objects...] }
    from collections import defaultdict

    driver_deliveries_dict = defaultdict(list)
    for d in deliveries:
        if d.driver is not None:
            driver_deliveries_dict[d.driver.id].append(d)

    # 3) Combine them into a single list so the template doesn’t need a dictionary lookup
    driver_list = []
    for summary in driver_summaries:
        driver_id = summary["driver__id"]
        driver_name = summary["driver__full_name"]
        total_jars = summary["total_jars"] or 0
        total_leaks = summary["total_leaks"] or 0
        total_half_caps = summary["total_half_caps"] or 0
        total_returns = summary["total_returns"] or 0

        driver_list.append(
            {
                "id": driver_id,
                "name": driver_name,
                "total_jars": total_jars,
                "total_leaks": total_leaks,
                "total_half_caps": total_half_caps,
                "total_returns": total_returns,
                "deliveries": driver_deliveries_dict[
                    driver_id
                ],  # attach the list of deliveries
            }
        )

    context = {
        "today": today,
        "filter_date": filter_date,
        "driver_list": driver_list,
    }
    return render(request, "records/daily_record.html", context)


def manage_salaries(request):
    # Get the filter month from the request; default to the current month
    filter_month = request.GET.get("month", localtime().strftime("%Y-%m"))
    try:
        year, month = map(int, filter_month.split("-"))
    except ValueError:
        # Handle invalid month format gracefully
        year, month = localtime().year, localtime().month
        filter_month = f"{year:04d}-{month:02d}"

    # Fetch workers (only STAFF and DRIVER roles)
    workers = User.objects.filter(role__in=["STAFF", "DRIVER"])

    # Base salary and overtime rate
    BASE_SALARY = {"DRIVER": 12000, "STAFF": 10000}
    EXTRA_HOUR_RATE = 100

    salary_data = []

    for worker in workers:
        # Calculate total hours worked for the filtered month
        total_hours_worked = (
            Attendance.objects.filter(
                user=worker, check_in__year=year, check_in__month=month
            ).aggregate(total=Sum("hours_worked"))["total"]
            or 0
        )

        # Calculate salary components
        if total_hours_worked > 0:
            extra_hours = max(0, total_hours_worked - 12)
            extra_payment = extra_hours * EXTRA_HOUR_RATE
            total_salary = BASE_SALARY[worker.role] + extra_payment
        else:
            extra_hours = 0
            extra_payment = 0
            total_salary = 0

        # Append worker data
        salary_data.append(
            {
                "name": worker.full_name,
                "role": worker.get_role_display(),
                "base_salary": (
                    BASE_SALARY[worker.role] if total_hours_worked > 0 else 0
                ),
                "total_hours": total_hours_worked,
                "extra_hours": extra_hours,
                "extra_payment": extra_payment,
                "total_salary": total_salary,
            }
        )

    # Fetch salary records filtered by the selected month
    salary_records = SalaryRecord.objects.filter(
        month__year=year, month__month=month
    ).order_by("-month")

    # Render template
    return render(
        request,
        "account/salary.html",
        {
            "salary_data": salary_data,
            "salary_records": salary_records,
            "current_month": datetime.now().strftime("%B %Y"),
            "filter_month": filter_month,
        },
    )


def add_salary(request):
    if request.method == "POST":
        form = SalaryRecordForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(
                reverse("manage_salaries")
            )  # Redirect to the salary management page
    else:
        form = SalaryRecordForm()

    return render(request, "account/add_salary.html", {"form": form})
