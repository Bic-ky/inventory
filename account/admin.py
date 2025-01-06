from django.contrib import admin
from .models import SalaryRecord, User, UserProfile , Attendance
 
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'full_name', 'role', 'is_active')
    ordering = ('-date_joined',)

admin.site.register(User, CustomUserAdmin)
admin.site.register(UserProfile)
admin.site.register(Attendance)
admin.site.register(SalaryRecord)
