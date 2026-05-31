"""
RepairDesk - Core Models

Customer, Device, Inventory, and RepairTicket models with FSM state machine.
"""
import uuid
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.utils import timezone
from django_fsm import FSMField, transition


class Customer(models.Model):
    """Customer profile for the repair shop."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, unique=True, db_index=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name} ({self.phone})"


class Device(models.Model):
    """Device belonging to a customer for repair."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='devices'
    )
    
    # Device identification
    brand = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=255, blank=True)
    
    # Physical Audit - "Nigerian Factor" for liability protection
    physical_condition = models.TextField(
        help_text="Document scratches, dents, screen condition, etc."
    )
    has_charger = models.BooleanField(default=False)
    has_battery = models.BooleanField(default=True)
    additional_accessories = models.TextField(
        blank=True,
        help_text="List any other accessories received"
    )
    
    # Photos for condition documentation
    photo_1 = models.ImageField(upload_to='device_photos/', blank=True, null=True)
    photo_2 = models.ImageField(upload_to='device_photos/', blank=True, null=True)
    photo_3 = models.ImageField(upload_to='device_photos/', blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.brand} {self.model_name} - {self.customer.name}"


class Inventory(models.Model):
    """Spare parts inventory management."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    part_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    
    # Stock management
    quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(
        default=0,
        help_text="Parts reserved for pending repairs"
    )
    reorder_level = models.PositiveIntegerField(default=5)
    
    # Pricing (in Naira)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Inventory"
        ordering = ['part_name']
        
    def __str__(self):
        return f"{self.part_name} ({self.sku})"
    
    @property
    def available_quantity(self):
        """Returns quantity minus reserved parts."""
        return self.quantity - self.reserved_quantity
    
    @property
    def needs_reorder(self):
        """Check if stock is below reorder level."""
        return self.available_quantity <= self.reorder_level


class RepairTicket(models.Model):
    """
    Main repair ticket with FSM-based workflow.
    
    States:
    - INTAKE: Device received, physical audit done
    - DIAGNOSING: Technician running diagnostics
    - AWAITING_APPROVAL: Quote sent, waiting for customer decision
    - REPAIRING: Approved, work in progress
    - PENDING_QC: Repair done, awaiting quality check
    - READY: Passed QC, ready for customer pickup
    - COMPLETED: Customer collected device
    """
    
    # State choices
    INTAKE = 'intake'
    DIAGNOSING = 'diagnosing'
    AWAITING_APPROVAL = 'awaiting_approval'
    REPAIRING = 'repairing'
    PENDING_QC = 'pending_qc'
    READY = 'ready'
    COMPLETED = 'completed'
    
    STATE_CHOICES = [
        (INTAKE, 'Intake'),
        (DIAGNOSING, 'Diagnosing'),
        (AWAITING_APPROVAL, 'Awaiting Approval'),
        (REPAIRING, 'Repairing'),
        (PENDING_QC, 'Pending QC'),
        (READY, 'Ready for Pickup'),
        (COMPLETED, 'Completed'),
    ]
    
    # Primary key - ticket number
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(max_length=20, unique=True, editable=False)
    
    # Relationships
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='tickets'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tickets'
    )
    assigned_technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets'
    )
    
    # FSM State
    state = FSMField(default=INTAKE, choices=STATE_CHOICES, db_index=True)
    
    # Problem description
    customer_complaint = models.TextField(help_text="Customer's description of the issue")
    technician_notes = models.TextField(blank=True)
    
    # Payment Tracking - "Nigerian Factor"
    diagnostic_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('7500.00'),
        help_text="Upfront diagnostic fee (₦)"
    )
    diagnostic_fee_paid = models.BooleanField(default=False)
    
    # Repair costs (populated after diagnosis)
    parts_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    labor_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    deposit_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    balance_paid = models.BooleanField(default=False)
    
    # Warranty tracking
    warranty_days = models.PositiveIntegerField(default=90)
    warranty_start_date = models.DateField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    diagnosed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        permissions = [
            ('can_diagnose', 'Can perform diagnosis'),
            ('can_approve', 'Can approve repairs'),
            ('can_qc', 'Can perform quality check'),
            ('can_collect', 'Can handle device collection'),
        ]
        
    def __str__(self):
        return f"Ticket #{self.ticket_number} - {self.device}"
    
    def save(self, *args, **kwargs):
        """Generate ticket number on first save in a transaction-safe manner."""
        if not self.ticket_number:
            from django.db import transaction
            # Format: RD-YYYYMMDD-XXXX
            today = timezone.now().strftime('%Y%m%d')
            with transaction.atomic():
                counter, created = TicketCounter.objects.select_for_update().get_or_create(
                    date_str=today,
                    defaults={'last_sequence': 0}
                )
                counter.last_sequence += 1
                counter.save()
                self.ticket_number = f'RD-{today}-{counter.last_sequence:04d}'
        super().save(*args, **kwargs)
    
    @property
    def total_cost(self):
        """Calculate total repair cost."""
        return self.parts_cost + self.labor_cost
    
    @property
    def balance_due(self):
        """Calculate remaining balance."""
        return self.total_cost - self.deposit_paid
    
    # ===================
    # FSM Transitions
    # ===================
    
    def has_technician(self):
        return self.assigned_technician is not None
        
    @transition(
        field=state,
        source=INTAKE,
        target=DIAGNOSING,
        permission='repairs.can_diagnose'
    )
    def start_diagnosis(self):
        """
        Technician scans barcode to check in device.
        Transition: INTAKE -> DIAGNOSING
        """
        from .notifications import notify_status_change
        notify_status_change(self, 'Diagnosis started')
    
    @transition(
        field=state,
        source=DIAGNOSING,
        target=AWAITING_APPROVAL
    )
    def request_approval(self):
        """
        Generate pro-forma invoice and request customer approval.
        Transition: DIAGNOSING -> AWAITING_APPROVAL
        """
        self.diagnosed_at = timezone.now()
        from .notifications import notify_customer_awaiting_approval
        notify_customer_awaiting_approval(self)
    
    @transition(
        field=state,
        source=AWAITING_APPROVAL,
        target=REPAIRING,
        permission='repairs.can_approve'
    )
    def approve_repair(self):
        """
        Customer approves quote and pays deposit.
        Transition: AWAITING_APPROVAL -> REPAIRING
        """
        self.approved_at = timezone.now()
    
    @transition(
        field=state,
        source=AWAITING_APPROVAL,
        target=READY
    )
    def reject_repair(self):
        """
        Customer rejects quote - device ready for collection.
        Transition: AWAITING_APPROVAL -> READY
        """
        from .notifications import notify_customer_ready
        notify_customer_ready(self, cancelled=True)
    
    @transition(
        field=state,
        source=REPAIRING,
        target=PENDING_QC
    )
    def finish_repair(self):
        """
        Technician completes repair work.
        Transition: REPAIRING -> PENDING_QC
        """
        pass
    
    @transition(
        field=state,
        source=PENDING_QC,
        target=READY,
        permission='repairs.can_qc'
    )
    def pass_qc(self):
        """
        Supervisor approves quality check.
        Transition: PENDING_QC -> READY
        """
        from .notifications import notify_customer_ready
        notify_customer_ready(self, cancelled=False)
    
    @transition(
        field=state,
        source=PENDING_QC,
        target=REPAIRING
    )
    def fail_qc(self):
        """
        QC failed - return to technician for rework.
        Transition: PENDING_QC -> REPAIRING
        """
        pass
    
    @transition(
        field=state,
        source=READY,
        target=COMPLETED,
        permission='repairs.can_collect'
    )
    def mark_collected(self):
        """
        Customer collects device - activate warranty.
        Transition: READY -> COMPLETED
        """
        self.completed_at = timezone.now()
        self.warranty_start_date = timezone.now().date()
        self.balance_paid = True


class TicketPart(models.Model):
    """Parts used in a repair ticket."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        RepairTicket,
        on_delete=models.CASCADE,
        related_name='parts_used'
    )
    part = models.ForeignKey(
        Inventory,
        on_delete=models.PROTECT,
        related_name='ticket_usages'
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Price at time of use (may differ from current inventory price)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['ticket', 'part']
        
    def __str__(self):
        return f"{self.quantity}x {self.part.part_name} for {self.ticket.ticket_number}"
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price


class TicketNote(models.Model):
    """
    Tracks both user-submitted comments and system-generated activity logs.
    """
    
    NOTE_TYPE_CHOICES = [
        ('system', 'System Activity'),
        ('comment', 'User Comment'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        RepairTicket,
        on_delete=models.CASCADE,
        related_name='notes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who made the comment or triggered the system event."
    )
    note_type = models.CharField(max_length=20, choices=NOTE_TYPE_CHOICES, default='comment')
    content = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.get_note_type_display()} on {self.ticket.ticket_number}"


class Notification(models.Model):
    """
    In-app notification for staff (technicians, frontdesk, QA).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    ticket = models.ForeignKey(
        RepairTicket,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True, blank=True
    )
    message = models.CharField(max_length=300)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.message[:60]}"


class TicketCounter(models.Model):
    """Monotonically increasing thread-safe counter for ticket numbers."""
    date_str = models.CharField(max_length=8, unique=True, db_index=True)  # YYYYMMDD
    last_sequence = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Ticket Counter"
        verbose_name_plural = "Ticket Counters"

    def __str__(self):
        return f"{self.date_str}: {self.last_sequence}"


class UserProfile(models.Model):
    """User profile mapping custom roles for RepairDesk staff."""
    
    ROLE_CHOICES = [
        ('admin', 'Admin/Manager'),
        ('frontdesk', 'Frontdesk'),
        ('technician', 'Technician'),
        ('supervisor', 'QA Supervisor'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='frontdesk',
        db_index=True
    )
    
    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    """Ensure every User model instance has a matching UserProfile."""
    if created:
        role = 'admin' if instance.is_superuser else 'frontdesk'
        UserProfile.objects.get_or_create(user=instance, defaults={'role': role})
    else:
        # Save profile if it exists, or create one if it was missing for legacy users
        if not hasattr(instance, 'profile'):
            role = 'admin' if instance.is_superuser else 'frontdesk'
            UserProfile.objects.get_or_create(user=instance, defaults={'role': role})
        else:
            instance.profile.save()

