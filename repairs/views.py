"""
RepairDesk - Views

HTMX-powered views for ticket management and state transitions.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Count, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django_fsm import TransitionNotAllowed

from .models import RepairTicket, Customer, Device, Inventory, TicketNote, Notification
from .forms import CustomerForm, DeviceForm, TicketForm
from .decorators import is_frontdesk, is_technician, is_qa_supervisor, frontdesk_required


# ===================
# Dashboard Views
# ===================

@login_required
def dashboard(request):
    """
    Live dashboard showing ticket counts per state.
    Managers can see the full pipeline at a glance.
    """
    # Get ticket counts per state
    state_counts = RepairTicket.objects.values('state').annotate(
        count=Count('id')
    ).order_by('state')
    
    # Convert to dict for lookup
    counts = {item['state']: item['count'] for item in state_counts}
    
    # Build state data with counts for template
    state_data = [
        {'code': code, 'name': name, 'count': counts.get(code, 0)}
        for code, name in RepairTicket.STATE_CHOICES
    ]
    
    # Get all tickets to group by state for the Kanban Board view
    all_tickets = RepairTicket.objects.select_related(
        'device', 'device__customer', 'assigned_technician'
    ).order_by('-created_at')
    
    from collections import defaultdict
    grouped_tickets = defaultdict(list)
    for ticket in all_tickets:
        grouped_tickets[ticket.state].append(ticket)
    
    # Get recent tickets (for compatibility with existing templates/activity log)
    recent_tickets = all_tickets[:10]
    
    context = {
        'state_data': state_data,
        'recent_tickets': recent_tickets,
        'states': RepairTicket.STATE_CHOICES,
        'grouped_tickets': dict(grouped_tickets),
    }
    return render(request, 'repairs/dashboard.html', context)


@login_required
def dashboard_stats_partial(request):
    """
    HTMX partial - Returns only the state count cards.
    Used for live updates without full page refresh.
    """
    state_counts = RepairTicket.objects.values('state').annotate(
        count=Count('id')
    ).order_by('state')
    
    counts = {item['state']: item['count'] for item in state_counts}
    
    # Build state data with counts for template
    state_data = [
        {'code': code, 'name': name, 'count': counts.get(code, 0)}
        for code, name in RepairTicket.STATE_CHOICES
    ]
    
    return render(request, 'repairs/partials/dashboard_stats.html', {
        'state_data': state_data,
    })


# ===================
# Ticket Views
# ===================

@login_required
def ticket_list(request):
    """List all tickets with filtering options."""
    tickets_qs = RepairTicket.objects.select_related(
        'device', 'device__customer', 'assigned_technician'
    ).order_by('-created_at')
    
    # Filter by state if provided
    state = request.GET.get('state')
    if state:
        tickets_qs = tickets_qs.filter(state=state)
    
    # Search by ticket number, customer name, phone, device info, or complaint
    search = request.GET.get('q')
    if search:
        search_query = search.strip()
        # Strip leading '#' if present (common when copying ticket numbers like #RD-20260528-0001)
        if search_query.startswith('#'):
            search_query = search_query[1:]
            
        tickets_qs = tickets_qs.filter(
            Q(ticket_number__icontains=search_query) |
            Q(device__customer__name__icontains=search_query) |
            Q(device__customer__phone__icontains=search_query) |
            Q(device__brand__icontains=search_query) |
            Q(device__model_name__icontains=search_query) |
            Q(customer_complaint__icontains=search_query)
        )
    
    # Pagination: 10 tickets per page
    paginator = Paginator(tickets_qs, 10)
    page_num = request.GET.get('page')
    try:
        tickets = paginator.page(page_num)
    except PageNotAnInteger:
        tickets = paginator.page(1)
    except EmptyPage:
        tickets = paginator.page(paginator.num_pages)
        
    context = {
        'tickets': tickets,
        'states': RepairTicket.STATE_CHOICES,
        'current_state': state or '',
        'search': search or '',
    }
    return render(request, 'repairs/ticket_list.html', context)


@login_required
def ticket_detail(request, ticket_id):
    """Ticket detail page with state transition buttons."""
    ticket = get_object_or_404(
        RepairTicket.objects.select_related(
            'device', 'device__customer', 'assigned_technician', 'created_by'
        ).prefetch_related('parts_used__part'),
        id=ticket_id
    )
    
    # Determine available transitions based on current state and user permissions
    available_transitions = get_available_transitions(ticket, request.user)
    
    can_comment = is_frontdesk(request.user) or request.user == ticket.assigned_technician
    is_authorized_assigner = is_frontdesk(request.user)
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    technicians = User.objects.filter(Q(profile__role='technician') | Q(is_superuser=True)).distinct()
    
    context = {
        'ticket': ticket,
        'available_transitions': available_transitions,
        'can_comment': can_comment,
        'is_authorized_assigner': is_authorized_assigner,
        'technicians': technicians,
    }
    return render(request, 'repairs/ticket_detail.html', context)


def get_available_transitions(ticket, user):
    """
    Get list of available transitions for the current ticket state.
    Checks both FSM state and user permissions.
    """
    transitions = []
    
    # Map of transitions with their display names and required permissions
    transition_map = {
        'start_diagnosis': {
            'name': 'Start Diagnosis',
            'source': RepairTicket.INTAKE,
            'check': is_technician,
            'btn_class': 'btn-primary',
        },
        'request_approval': {
            'name': 'Request Approval',
            'source': RepairTicket.DIAGNOSING,
            'check': is_technician,
            'btn_class': 'btn-warning',
        },
        'approve_repair': {
            'name': 'Approve Repair',
            'source': RepairTicket.AWAITING_APPROVAL,
            'check': is_frontdesk,
            'btn_class': 'btn-success',
        },
        'reject_repair': {
            'name': 'Reject (Cancel)',
            'source': RepairTicket.AWAITING_APPROVAL,
            'check': is_frontdesk,
            'btn_class': 'btn-danger',
        },
        'finish_repair': {
            'name': 'Finish Repair',
            'source': RepairTicket.REPAIRING,
            'check': is_technician,
            'btn_class': 'btn-info',
        },
        'pass_qc': {
            'name': 'Pass QC',
            'source': RepairTicket.PENDING_QC,
            'check': is_qa_supervisor,
            'btn_class': 'btn-success',
        },
        'fail_qc': {
            'name': 'Fail QC (Rework)',
            'source': RepairTicket.PENDING_QC,
            'check': is_qa_supervisor,
            'btn_class': 'btn-danger',
        },
        'mark_collected': {
            'name': 'Mark Collected',
            'source': RepairTicket.READY,
            'check': is_frontdesk,
            'btn_class': 'btn-success',
        },
    }
    
    for action, config in transition_map.items():
        if ticket.state == config['source']:
            # Check role requirement
            check_func = config.get('check')
            if check_func is None or check_func(user):
                transitions.append({
                    'action': action,
                    'name': config['name'],
                    'btn_class': config['btn_class'],
                })
    
    return transitions


@login_required
@require_POST
def transition_ticket(request, ticket_id, action):
    """
    HTMX endpoint - Handle FSM state transitions.
    Returns updated row partial for list, or status section for detail page.
    """
    ticket = get_object_or_404(
        RepairTicket.objects.select_related(
            'device', 'device__customer', 'assigned_technician'
        ),
        id=ticket_id
    )
    
    # Map action names to ticket methods
    transition_methods = {
        'start_diagnosis': ticket.start_diagnosis,
        'request_approval': ticket.request_approval,
        'approve_repair': ticket.approve_repair,
        'reject_repair': ticket.reject_repair,
        'finish_repair': ticket.finish_repair,
        'pass_qc': ticket.pass_qc,
        'fail_qc': ticket.fail_qc,
        'mark_collected': ticket.mark_collected,
    }
    
    if action not in transition_methods:
        return HttpResponse(
            '<div class="alert alert-error">Invalid action</div>',
            status=400
        )
        
    if action == 'start_diagnosis' and not ticket.assigned_technician:
        return HttpResponse(
            '<div class="alert alert-error">You must assign a Technician before starting Diagnosis.</div>',
            status=400
        )
    
    try:
        # Execute the transition
        transition_method = transition_methods[action]
        transition_method()
        ticket.save()
        
        # Log the transition as a system activity
        TicketNote.objects.create(
            ticket=ticket,
            user=request.user,
            note_type='system',
            content=f"Ticket transitioned to {ticket.get_state_display()}"
        )
        
        # Auto-create in-app notifications
        _create_transition_notifications(ticket, action, request.user)
        
        # Detect if request came from ticket list (target is ticket-row-*) or detail page
        hx_target = request.headers.get('HX-Target', '')
        
        if hx_target.startswith('ticket-row-'):
            # Return updated row for ticket list
            return render(request, 'repairs/partials/ticket_row.html', {
                'ticket': ticket,
            })
        else:
            # Return updated status section and actions for detail page using OOB swaps
            # We render a generic wrapper that contains both partials with hx-swap-oob
            available_transitions = get_available_transitions(ticket, request.user)
            
            # Instead of returning a single section that ruins the layout, we return both
            # pieces with hx-swap-oob to target their specific locations
            context = {
                'ticket': ticket,
                'available_transitions': available_transitions,
            }
            badge_html = render_to_string("repairs/partials/ticket_status_badge.html", context, request=request)
            actions_html = render_to_string("repairs/partials/ticket_actions.html", context, request=request)
            
            return HttpResponse(f'''
                <div id="ticket-status-badge" hx-swap-oob="true">
                    {badge_html}
                </div>
                <div id="ticket-actions" class="flex flex-col gap-2" hx-swap-oob="true">
                    {actions_html}
                </div>
            ''')
        
    except TransitionNotAllowed:
        return HttpResponse(
            f'<div class="alert alert-error">Transition "{action}" is not allowed from current state</div>',
            status=400
        )
    except PermissionError:
        return HttpResponse(
            '<div class="alert alert-error">You do not have permission for this action</div>',
            status=403
        )


# ===================
# Customer Views
# ===================

@login_required
def customer_list(request):
    """List customers with search."""
    customers = Customer.objects.annotate(
        device_count=Count('devices')
    ).order_by('-created_at')
    
    search = request.GET.get('q')
    if search:
        customers = customers.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )
    
    context = {
        'customers': customers,
        'search': search or '',
    }
    return render(request, 'repairs/customer_list.html', context)


@login_required
def customer_search(request):
    """
    HTMX endpoint - Live customer search.
    Returns partial with matching customers.
    """
    # Accept both 'q' and 'customer_search' as parameter names
    search = request.GET.get('q', '') or request.GET.get('customer_search', '')
    search = search.strip()
    
    if len(search) < 2:
        return HttpResponse('')
    
    customers = Customer.objects.filter(
        Q(name__icontains=search) |
        Q(phone__icontains=search)
    )[:10]
    
    return render(request, 'repairs/partials/customer_search_results.html', {
        'customers': customers,
    })


@login_required
def customer_create(request):
    """Create new customer."""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f'Customer "{customer.name}" created successfully.')
            return redirect('repairs:customer_detail', customer_id=customer.id)
    else:
        form = CustomerForm()
    
    return render(request, 'repairs/customer_form.html', {
        'form': form,
        'title': 'New Customer',
    })


@login_required
def customer_detail(request, customer_id):
    """Customer detail with devices and tickets."""
    customer = get_object_or_404(Customer, id=customer_id)
    devices = customer.devices.prefetch_related('tickets').order_by('-created_at')
    
    return render(request, 'repairs/customer_detail.html', {
        'customer': customer,
        'devices': devices,
    })


# ===================
# Inventory Views
# ===================

@login_required
def inventory_list(request):
    """List inventory with search and low-stock alerts."""
    items = Inventory.objects.all()
    
    search = request.GET.get('q')
    if search:
        items = items.filter(
            Q(part_name__icontains=search) |
            Q(sku__icontains=search)
        )
    
    # Filter for low stock
    if request.GET.get('low_stock'):
        items = [i for i in items if i.needs_reorder]
    
    context = {
        'items': items,
        'search': search or '',
    }
    return render(request, 'repairs/inventory_list.html', context)


@login_required
def inventory_search(request):
    """
    HTMX endpoint - Live inventory search.
    Returns partial with matching parts.
    """
    search = request.GET.get('q', '').strip()
    
    if len(search) < 2:
        return HttpResponse('')
    
    items = Inventory.objects.filter(
        Q(part_name__icontains=search) |
        Q(sku__icontains=search)
    )[:10]
    
    return render(request, 'repairs/partials/inventory_search_results.html', {
        'items': items,
    })
# ===================
# Intake Views
# ===================

@login_required
@frontdesk_required
def create_ticket(request, customer_id=None):
    """
    Create new repair ticket (Intake process).
    Optionally pre-fill with existing customer.
    """
    customer = None
    if customer_id:
        customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        customer_form = None if customer else CustomerForm(request.POST, prefix='customer')
        device_form = DeviceForm(request.POST, request.FILES, prefix='device')
        ticket_form = TicketForm(request.POST, prefix='ticket')
        
        forms_valid = device_form.is_valid() and ticket_form.is_valid()
        if not customer:
            forms_valid = forms_valid and customer_form.is_valid()
        
        if forms_valid:
            # Create or use existing customer
            if not customer:
                customer = customer_form.save()
            
            # Create device
            device = device_form.save(commit=False)
            device.customer = customer
            device.save()
            
            # Create ticket
            ticket = ticket_form.save(commit=False)
            ticket.device = device
            ticket.created_by = request.user
            ticket.save()
            
            messages.success(request, f'Ticket #{ticket.ticket_number} created successfully.')
            return redirect('repairs:ticket_detail', ticket_id=ticket.id)
    else:
        customer_form = None if customer else CustomerForm(prefix='customer')
        device_form = DeviceForm(prefix='device')
        ticket_form = TicketForm(prefix='ticket')
    
    context = {
        'customer': customer,
        'customer_form': customer_form,
        'device_form': device_form,
        'ticket_form': ticket_form,
    }
    return render(request, 'repairs/create_ticket.html', context)


@login_required
def ticket_timeline(request, ticket_id):
    """HTMX polling endpoint returning timeline feed + OOB swaps for badge/actions/comment."""
    ticket = get_object_or_404(RepairTicket, id=ticket_id)
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Render the main timeline
    timeline_html = render_to_string(
        'repairs/partials/ticket_timeline.html',
        {'ticket': ticket},
        request=request
    )
    
    # OOB: Status Badge
    badge_html = render_to_string(
        'repairs/partials/ticket_status_badge.html',
        {'ticket': ticket},
        request=request
    )
    
    # OOB: Action Buttons (RBAC-aware)
    available_transitions = get_available_transitions(ticket, request.user)
    actions_html = render_to_string(
        'repairs/partials/ticket_actions.html',
        {'ticket': ticket, 'available_transitions': available_transitions},
        request=request
    )
    
    # Combine: main content + OOB swaps (no comment-box swap to avoid wiping user input)
    return HttpResponse(f'''
        {timeline_html}
        <div id="ticket-status-badge" hx-swap-oob="true">
            {badge_html}
        </div>
        <div id="ticket-actions" class="flex flex-col gap-2" hx-swap-oob="true">
            {actions_html}
        </div>
    ''')


@login_required
@require_POST
def add_ticket_note(request, ticket_id):
    """HTMX endpoint to add a comment to a ticket."""
    ticket = get_object_or_404(RepairTicket, id=ticket_id)
    
    # No comments on completed tickets
    if ticket.state == RepairTicket.COMPLETED:
        return HttpResponseForbidden('<div class="alert alert-error">This ticket is closed. No further comments allowed.</div>')
    
    # Restrict to Frontdesk or the specifically assigned Technician
    if not (is_frontdesk(request.user) or request.user == ticket.assigned_technician):
        return HttpResponseForbidden('<div class="alert alert-error">You are not authorized to comment on this ticket.</div>')

    content = request.POST.get('content', '').strip()
    
    if content:
        note = TicketNote.objects.create(
            ticket=ticket,
            user=request.user,
            note_type='comment',
            content=content
        )
        _create_comment_notifications(ticket, request.user)
        # Re-fetch notes to render the single note or just return the single note
        return render(request, 'repairs/partials/ticket_note_single.html', {'note': note})
        
    return HttpResponse(status=400)


@login_required
@require_POST
def assign_technician(request, ticket_id):
    """HTMX endpoint to handle technician assignments."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    ticket = get_object_or_404(RepairTicket, id=ticket_id)
    
    # Authorized assigners only (Frontdesk & Admin only)
    if not is_frontdesk(request.user):
        return HttpResponse(
            f'<div class="text-red-500 text-xs mt-1">Error: You do not have permission to assign or unassign technicians.</div>'
            f'<div id="ticket-assignment" hx-swap-oob="true"> '
            f'    {render_to_string("repairs/partials/ticket_assignment.html", {"ticket": ticket}, request=request)}'
            f'</div>',
            status=403
        )
        
    tech_id = request.POST.get('technician_id')
    
    if tech_id:
        try:
            technician = User.objects.get(id=tech_id)
            
            # Enforce Max 2 Active Tickets for Technicians
            active_tickets = RepairTicket.objects.filter(
                assigned_technician=technician,
                state__in=[RepairTicket.DIAGNOSING, RepairTicket.REPAIRING]
            ).exclude(id=ticket.id).count()
            
            if active_tickets >= 2:
                return HttpResponse(
                    f'<div class="text-red-500 text-xs mt-1">Error: {technician.username} already has 2 active repairs!</div>'
                    f'<div id="ticket-assignment" hx-swap-oob="true"> '
                    f'    {render_to_string("repairs/partials/ticket_assignment.html", {"ticket": ticket}, request=request)}'
                    f'</div>',
                    status=400
                )
                
            ticket.assigned_technician = technician
            ticket.save()
            
            # Auto-log system assignment note
            TicketNote.objects.create(
                ticket=ticket,
                user=request.user,
                note_type='system',
                content=f"Assigned to {technician.get_full_name() or technician.username}"
            )
        except User.DoesNotExist:
            return HttpResponse('<div class="text-red-500 text-sm">Invalid Technician</div>', status=400)
    else:
        # Unassign logic
        ticket.assigned_technician = None
        ticket.save()
        TicketNote.objects.create(
            ticket=ticket,
            user=request.user,
            note_type='system',
            content="Ticket unassigned"
        )
        
    # We will return the updated Assignment UI block
    is_authorized_assigner = is_frontdesk(request.user)
    
    context = {
        'ticket': ticket,
        'technicians': User.objects.filter(Q(profile__role='technician') | Q(is_superuser=True)).distinct(),
        'is_authorized_assigner': is_authorized_assigner,
    }
    return render(request, 'repairs/partials/ticket_assignment.html', context)


def _create_transition_notifications(ticket, action, actor):
    """Create in-app notifications for relevant users after a ticket transition."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if action == 'request_approval':
        # Notify all Frontdesk users
        frontdesk_users = User.objects.filter(Q(profile__role='frontdesk') | Q(is_superuser=True)).distinct()
        for user in frontdesk_users:
            Notification.objects.create(
                recipient=user,
                ticket=ticket,
                message=f"#{ticket.ticket_number} is awaiting your approval ({ticket.device.brand} {ticket.device.model_name})"
            )
    elif action in ('approve_repair', 'reject_repair'):
        # Notify the assigned technician
        if ticket.assigned_technician:
            verb = 'approved' if action == 'approve_repair' else 'rejected'
            Notification.objects.create(
                recipient=ticket.assigned_technician,
                ticket=ticket,
                message=f"Repair for #{ticket.ticket_number} has been {verb} by {actor.get_full_name() or actor.username}"
            )
    elif action == 'finish_repair':
        # Notify QA supervisors
        qa_users = User.objects.filter(Q(profile__role='supervisor') | Q(is_superuser=True)).distinct()
        for user in qa_users:
            Notification.objects.create(
                recipient=user,
                ticket=ticket,
                message=f"#{ticket.ticket_number} is ready for QC review"
            )
    elif action in ('pass_qc', 'fail_qc'):
        # Notify Frontdesk
        frontdesk_users = User.objects.filter(Q(profile__role='frontdesk') | Q(is_superuser=True)).distinct()
        verb = 'passed' if action == 'pass_qc' else 'failed'
        for user in frontdesk_users:
            Notification.objects.create(
                recipient=user,
                ticket=ticket,
                message=f"#{ticket.ticket_number} {verb} QC"
            )


def _create_comment_notifications(ticket, commenter):
    """When someone comments, notify the other party."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if is_frontdesk(commenter) or is_qa_supervisor(commenter):
        # Notify assigned technician
        if ticket.assigned_technician and ticket.assigned_technician != commenter:
            Notification.objects.create(
                recipient=ticket.assigned_technician,
                ticket=ticket,
                message=f"New comment on #{ticket.ticket_number} from {commenter.get_full_name() or commenter.username}"
            )
    elif is_technician(commenter):
        # Notify all Frontdesk users
        frontdesk_users = User.objects.filter(Q(profile__role='frontdesk') | Q(is_superuser=True)).exclude(id=commenter.id).distinct()
        for user in frontdesk_users:
            Notification.objects.create(
                recipient=user,
                ticket=ticket,
                message=f"New comment on #{ticket.ticket_number} from {commenter.get_full_name() or commenter.username}"
            )


@login_required
def notification_bell(request):
    """HTMX endpoint: returns notification dropdown HTML."""
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:15]
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return render(request, 'repairs/partials/notification_dropdown.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })


@login_required
@require_POST
def mark_notifications_read(request):
    """Mark all notifications as read for the current user."""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:15]
    return render(request, 'repairs/partials/notification_dropdown.html', {
        'notifications': notifications,
        'unread_count': 0,
    })


@login_required
def notification_click(request, notification_id):
    """Mark a single notification as read and redirect to its ticket."""
    notif = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notif.is_read = True
    notif.save()
    if notif.ticket:
        return redirect('repairs:ticket_detail', ticket_id=notif.ticket.id)
    return redirect('repairs:dashboard')
