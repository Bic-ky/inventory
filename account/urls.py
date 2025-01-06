from django.urls import path
from . import views

urlpatterns =[
    path('register/', views.register, name='register'),
    path('login/', views.login_view , name="login"),
    path('myAccount/', views.myAccount, name='myAccount'),
    path('logout/',views.logout, name='logout'),

    path('admin/dashboard',views.admin_dashboard, name='admin_dashboard'),
    path('staff/dashboard',views.staff_dashboard, name='staff_dashboard'),
    path('driver/dashboard',views.driver_dashboard, name='driver_dashboard'),

    
    path('attendance/', views.attendance, name='attendance'),
    path('add_attendance/', views.add_attendance, name='add_attendance'),
    path('daily_record/', views.daily_record, name='daily_record'),

    path('add_salary', views.add_salary, name='add_salary'),
    path('salaries/manage/', views.manage_salaries, name='manage_salaries'),
    path('get_user_attendance', views.get_user_attendance, name='get_user_attendance'),


    path('admin_change_password/', views.admin_change_password, name='admin_change_password'),

]