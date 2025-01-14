from django import template

register = template.Library()


@register.filter
def subtract(value, arg):
    """Subtracts the arg from the value."""
    try:
        return value - arg
    except (TypeError, ValueError):
        return 0  # Return 0 if the operation fails
