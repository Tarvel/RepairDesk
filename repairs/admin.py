"""
RepairDesk - Admin Configuration

Admin interface for managing repairs, customers, and inventory.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Customer, Device, Inventory, RepairTicket, TicketPart


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'device_count', 'created_at']
    search_fields = ['name', 'phone', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def device_count(self, obj):
        return obj.devices.count()
    device_count.short_description = 'Devices'


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['brand', 'model_name', 'customer', 'has_charger', 'has_battery', 'created_at']
    list_filter = ['brand', 'has_charger', 'has_battery']
    search_fields = ['brand', 'model_name', 'serial_number', 'customer__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['customer']


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['part_name', 'sku', 'quantity', 'reserved_quantity', 'available_stock', 'unit_price', 'stock_status']
    list_filter = ['reorder_level']
    search_fields = ['part_name', 'sku']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def available_stock(self, obj):
        return obj.available_quantity
    available_stock.short_description = 'Available'
    
    def stock_status(self, obj):
        if obj.needs_reorder:
            return format_html('<span style="color: red; font-weight: bold;">LOW STOCK</span>')
        return format_html('<span style="color: green;">OK</span>')
    stock_status.short_description = 'Status'


class TicketPartInline(admin.TabularInline):
    model = TicketPart
    extra = 0
    raw_id_fields = ['part']
    readonly_fields = ['total_price']


@admin.register(RepairTicket)
class RepairTicketAdmin(admin.ModelAdmin):
    list_display = [
        'ticket_number', 'device_info', 'customer_name', 'state_badge',
        'diagnostic_fee_paid', 'total_cost', 'created_at'
    ]
    list_filter = ['state', 'diagnostic_fee_paid', 'balance_paid', 'created_at']
    search_fields = ['ticket_number', 'device__customer__name', 'device__customer__phone']
    readonly_fields = [
        'id', 'ticket_number', 'created_at', 'updated_at',
        'diagnosed_at', 'approved_at', 'completed_at'
    ]
    raw_id_fields = ['device', 'created_by', 'assigned_technician']
    inlines = [TicketPartInline]
    
    fieldsets = (
        ('Ticket Info', {
            'fields': ('ticket_number', 'device', 'state', 'created_by', 'assigned_technician')
        }),
        ('Problem', {
            'fields': ('customer_complaint', 'technician_notes')
        }),
        ('Financials', {
            'fields': (
                ('diagnostic_fee', 'diagnostic_fee_paid'),
                ('parts_cost', 'labor_cost'),
                ('deposit_paid', 'balance_paid'),
            )
        }),
        ('Warranty', {
            'fields': ('warranty_days', 'warranty_start_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'diagnosed_at', 'approved_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def device_info(self, obj):
        return f"{obj.device.brand} {obj.device.model_name}"
    device_info.short_description = 'Device'
    
    def customer_name(self, obj):
        return obj.device.customer.name
    customer_name.short_description = 'Customer'
    
    def state_badge(self, obj):
        colors = {
            'intake': '#6c757d',
            'diagnosing': '#007bff',
            'awaiting_approval': '#ffc107',
            'repairing': '#17a2b8',
            'pending_qc': '#fd7e14',
            'ready': '#28a745',
            'completed': '#6c757d',
        }
        color = colors.get(obj.state, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_state_display()
        )
    state_badge.short_description = 'State'


@admin.register(TicketPart)
class TicketPartAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'part', 'quantity', 'unit_price', 'total_price']
    raw_id_fields = ['ticket', 'part']
