"""
RepairDesk - Forms

Forms for Customer, Device, and Ticket creation/editing.
"""
from django import forms
from .models import Customer, Device, RepairTicket, Inventory


# Tailwind CSS input classes for consistent styling
INPUT_CLASS = 'w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-gray-400 focus:border-gray-400 focus:outline-none'
TEXTAREA_CLASS = 'w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-gray-400 focus:border-gray-400 focus:outline-none'
CHECKBOX_CLASS = 'w-4 h-4 rounded border-gray-300 text-gray-900 focus:ring-gray-400 focus:ring-1 focus:ring-offset-0 cursor-pointer'
FILE_CLASS = 'w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200 cursor-pointer'


class CustomerForm(forms.ModelForm):
    """Form for creating/editing customers."""
    
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'email', 'address']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Full Name',
            }),
            'phone': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': '08012345678',
            }),
            'email': forms.EmailInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'email@example.com',
            }),
            'address': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'rows': 3,
                'placeholder': 'Address',
            }),
        }


class DeviceForm(forms.ModelForm):
    """Form for device intake with physical audit fields."""
    
    class Meta:
        model = Device
        fields = [
            'brand', 'model_name', 'serial_number',
            'physical_condition', 'has_charger', 'has_battery',
            'additional_accessories', 'photo_1', 'photo_2', 'photo_3',
        ]
        widgets = {
            'brand': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'e.g., HP, Dell, Lenovo',
            }),
            'model_name': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'e.g., Pavilion 15, ThinkPad X1',
            }),
            'serial_number': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Serial Number (if visible)',
            }),
            'physical_condition': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'rows': 4,
                'placeholder': 'Document all scratches, dents, screen cracks, etc.',
            }),
            'has_charger': forms.CheckboxInput(attrs={
                'class': CHECKBOX_CLASS,
            }),
            'has_battery': forms.CheckboxInput(attrs={
                'class': CHECKBOX_CLASS,
            }),
            'additional_accessories': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'rows': 2,
                'placeholder': 'List any other accessories (bag, mouse, etc.)',
            }),
            'photo_1': forms.FileInput(attrs={'class': FILE_CLASS}),
            'photo_2': forms.FileInput(attrs={'class': FILE_CLASS}),
            'photo_3': forms.FileInput(attrs={'class': FILE_CLASS}),
        }


class TicketForm(forms.ModelForm):
    """Form for repair ticket creation."""
    
    class Meta:
        model = RepairTicket
        fields = [
            'customer_complaint', 'diagnostic_fee', 'diagnostic_fee_paid',
        ]
        widgets = {
            'customer_complaint': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'rows': 4,
                'placeholder': "Customer's description of the issue",
            }),
            'diagnostic_fee': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'step': '0.01',
            }),
            'diagnostic_fee_paid': forms.CheckboxInput(attrs={
                'class': CHECKBOX_CLASS,
            }),
        }


class DiagnosisForm(forms.ModelForm):
    """Form for technician to enter diagnosis details."""
    
    class Meta:
        model = RepairTicket
        fields = ['technician_notes', 'parts_cost', 'labor_cost']
        widgets = {
            'technician_notes': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'rows': 5,
                'placeholder': 'Diagnosis findings and recommended repairs',
            }),
            'parts_cost': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'step': '0.01',
                'placeholder': '₦0.00',
            }),
            'labor_cost': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'step': '0.01',
                'placeholder': '₦0.00',
            }),
        }


class InventoryForm(forms.ModelForm):
    """Form for adding/editing inventory items."""
    
    class Meta:
        model = Inventory
        fields = [
            'part_name', 'sku', 'description',
            'quantity', 'reorder_level', 'unit_price',
        ]
        widgets = {
            'part_name': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Part Name',
            }),
            'sku': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'SKU-001',
            }),
            'description': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'rows': 3,
            }),
            'quantity': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
            }),
            'reorder_level': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'step': '0.01',
            }),
        }
