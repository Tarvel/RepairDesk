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
    Check if a user belongs to a specific group.
    Usage: {% if user|has_role:"Frontdesk" %}
    """
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name=role_name).exists()

