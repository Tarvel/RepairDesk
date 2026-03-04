"""
RepairDesk - Repairs App URL Configuration
"""
from django.urls import path
from . import views

app_name = 'repairs'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('dashboard/stats/', views.dashboard_stats_partial, name='dashboard_stats'),
    
    # Tickets
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/new/', views.create_ticket, name='create_ticket'),
    path('tickets/new/<uuid:customer_id>/', views.create_ticket, name='create_ticket_for_customer'),
    path('tickets/<uuid:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<uuid:ticket_id>/transition/<str:action>/', views.transition_ticket, name='transition_ticket'),
    path('tickets/<uuid:ticket_id>/timeline/', views.ticket_timeline, name='ticket_timeline'),
    path('tickets/<uuid:ticket_id>/note/', views.add_ticket_note, name='add_ticket_note'),
    path('tickets/<uuid:ticket_id>/assign/', views.assign_technician, name='assign_technician'),
    
    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/new/', views.customer_create, name='customer_create'),
    path('customers/search/', views.customer_search, name='customer_search'),
    path('customers/<uuid:customer_id>/', views.customer_detail, name='customer_detail'),
    
    # Inventory
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/search/', views.inventory_search, name='inventory_search'),
    
    # Notifications
    path('notifications/', views.notification_bell, name='notification_bell'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('notifications/<uuid:notification_id>/click/', views.notification_click, name='notification_click'),
]
