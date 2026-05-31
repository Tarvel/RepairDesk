"""
Custom template tags and filters for repairs app.
"""
from django import template

register = template.Library()


@register.filter
def get(dictionary, key):
    """
    Get a value from a dictionary using a variable key.
    Usage: {{ my_dict|get:key_variable }}
    """
    if dictionary is None:
        return 0
    return dictionary.get(key, 0)


@register.filter
def has_role(user, role_name):
    """
    Check if a user has a specific role via UserProfile.
    Supports both new role names and legacy group names for backwards compatibility.
    Usage: {% if user|has_role:"frontdesk" %}
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    # Map legacy group names to new profile role values
    role_map = {
        'Frontdesk': 'frontdesk',
        'Technician': 'technician',
        'Supervisor': 'supervisor',
        'Quality Analyst': 'supervisor',
        'Admin': 'admin',
    }
    target_role = role_map.get(role_name, role_name.lower())

    try:
        return user.profile.role == target_role or user.profile.role == 'admin'
    except Exception:
        return False
