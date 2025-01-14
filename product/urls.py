from django.urls import path

from .send_email import send_monthly_summary
from . import views


urlpatterns =[
    path('delivery/', views.delivery, name='delivery'),

    path('add-delivery/', views.add_delivery, name='add_delivery'),
    path('all-deliveries/', views.all_deliveries, name='all_deliveries'),
    path('bills/<int:delivery_id>/', views.bill_detail, name='bill_detail'),

    path('expenses/', views.expenses, name='expenses'),
    path('add_expense/', views.add_expense, name='add_expense'),

    path('monthly_summary/', views.monthly_summary, name='monthly_summary'),
    path('send_monthly_summary/', send_monthly_summary, name='send_monthly_summary'),

    path('jar-in-out/new/', views.jar_in_out_create, name='jar_in_out_create'),
    path('jar-in-out/', views.jar_in_out_list, name='jar_in_out_list'),

    path('bills/', views.bill_list, name='bill_list'),
    path('bills/new/', views.bill_create, name='bill_create'),

    path('jarcaps/', views.jar_cap_list, name='jar_cap_list'),
    path('jarcaps/new/', views.jar_cap_create, name='jar_cap_create'),
    path('get-filler-vehicle/<int:filler_id>/', views.get_filler_vehicle, name='get_filler_vehicle'),

    path('fillers/', views.filler_list, name='filler_list'),
    path('fillers/<int:pk>/', views.filler_detail, name='filler_detail'),
    path('filler_ledger_detail/<int:filler_id>/', views.filler_ledger_detail, name='filler_ledger_detail'),

]