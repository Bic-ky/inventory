from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile, Attendance, SalaryRecord


class UserAdmin(BaseUserAdmin):
    list_display = ("phone_number", "full_name", "role", "is_active", "is_admin")
    list_filter = ("role", "is_active", "is_admin") 
    search_fields = ("phone_number", "full_name") 
    ordering = ("phone_number",)  

    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        (_("Personal info"), {"fields": ("full_name", "email", "address", "city", "country")}),
        (_("Permissions"), {"fields": ("is_active", "is_admin", "is_staff", "is_superuser", "role")}),
        (_("Important dates"), {"fields": ("last_login", "created_date")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone_number", "password1", "password2", "role"),
        }),
    )

    filter_horizontal = ()  # OVERRIDE 

    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get("password"):
            obj.set_password(form.cleaned_data["password"])
        super().save_model(request, obj, form, change)


# Register 
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile)
admin.site.register(Attendance)
admin.site.register(SalaryRecord)
