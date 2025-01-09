import datetime
from decimal import Decimal
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, role=None):
        if not phone_number:
            raise ValueError("The Phone Number field must be set")

        user = self.model(phone_number=phone_number, role=role)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None):
        # Create and save a new superuser with the given phone number and password
        user = self.create_user(phone_number, password, role=User.ADMIN)
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    ADMIN = "ADMIN"
    STAFF = "STAFF"
    DRIVER = "DRIVER"

    ROLE_CHOICES = [
        (ADMIN, "Admin"),
        (STAFF, "Staff"),
        (DRIVER, "Driver"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone_number = models.CharField(unique=True, max_length=15, null=True, blank=True)
    full_name = models.CharField(max_length=50, blank=True)
    email = models.EmailField(max_length=100, unique=False, default="")

    address = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, blank=True)

    created_date = models.DateTimeField(default=timezone.now)
    modified_date = models.DateTimeField(auto_now=True)
    date_joined = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = "phone_number"
    objects = UserManager()

    def __str__(self):
        return str(self.full_name)

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return True

    def get_role(self):
        if self.role == "ADMIN":
            user_role = "Admin"
        elif self.role == "STAFF":
            user_role = "Staff"
        else:
            user_role = "Unknown Role"
        return user_role


class UserProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="user_profile"
    )
    GENDER_CHOICES = (
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other"),
    )
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    age = models.PositiveSmallIntegerField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to="users/profile_pictures", blank=True, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.user.phone_number)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


@receiver(post_save, sender=User)
def post_save_create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
        print("Userprofile was created.")
    else:
        try:
            profile = UserProfile.objects.get(user=instance)
            print("Userprofile was updated.")
            profile.save()
        except:
            UserProfile.objects.create(user=instance)
            print("Userprofile was not found so created.")


class Attendance(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role__in": ["STAFF", "DRIVER"]},
    )
    check_in = models.DateTimeField(default=timezone.now)
    check_out = models.DateTimeField(null=True, blank=True)
    hours_worked = models.FloatField(default=0, editable=False)
    is_present = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "check_in")

    def calculate_hours_worked(self):
        """Automatically calculates the number of hours worked between check-in and check-out."""
        if self.check_out:
            time_difference = self.check_out - self.check_in
            self.hours_worked = round(time_difference.total_seconds() / 3600.0, 2)
        else:
            self.hours_worked = 0

    def save(self, *args, **kwargs):
        """Override save method to calculate hours worked before saving."""
        self.calculate_hours_worked()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.full_name} - {self.check_in.date()}"


class SalaryRecord(models.Model):
    DRIVER = "DRIVER"
    STAFF = "STAFF"

    ROLE_CHOICES = [
        (DRIVER, "Driver"),
        (STAFF, "Staff"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, limit_choices_to={"role__in": [DRIVER, STAFF]}
    )
    month = models.DateField(default=timezone.now)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    extra_hours = models.FloatField(default=0)
    extra_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remarks = models.TextField(blank=True, null=True)

    def calculate_salary(self):
        """Calculate total salary based on base salary and extra payment."""
        hourly_rate = Decimal("10.00")  # Ensure hourly_rate is a Decimal
        if self.user.role == self.DRIVER:
            hourly_rate = Decimal("10.00")  # Example rate for DRIVER
        elif self.user.role == self.STAFF:
            hourly_rate = Decimal("8.00")  # Example rate for STAFF

        # Calculate extra payment as a Decimal
        self.extra_payment = Decimal(self.extra_hours) * hourly_rate

        # Calculate total salary as a Decimal
        self.total_salary = self.base_salary + self.extra_payment

    def save(self, *args, **kwargs):
        """Override save to calculate salary before saving."""
        self.calculate_salary()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.full_name} - {self.month.strftime('%B %Y')} - {self.total_salary}"
