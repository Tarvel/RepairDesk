from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

from .models import UserProfile

def is_frontdesk(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    try:
        return user.profile.role in ['frontdesk', 'admin']
    except (UserProfile.DoesNotExist, AttributeError):
        return False

def is_technician(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    try:
        return user.profile.role in ['technician', 'admin']
    except (UserProfile.DoesNotExist, AttributeError):
        return False

def is_qa_supervisor(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    try:
        return user.profile.role in ['supervisor', 'admin']
    except (UserProfile.DoesNotExist, AttributeError):
        return False

def role_required(test_func, error_message="You don't have permission to perform this action."):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            else:
                messages.warning(request, error_message)
                referer = request.META.get('HTTP_REFERER')
                if referer:
                    return redirect(referer)
                return redirect('repairs:dashboard')
        return _wrapped_view
    return decorator

def frontdesk_required(view_func):
    return role_required(is_frontdesk, "Only Frontdesk staff can create tickets or approve repairs.")(view_func)

def technician_required(view_func):
    return role_required(is_technician, "Only Technicians can access this.")(view_func)

def qa_supervisor_required(view_func):
    return role_required(is_qa_supervisor, "Only Quality Analysts can access this.")(view_func)
