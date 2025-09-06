from django import template

register = template.Library()

@register.filter
def div(value, arg):
    """Divide value by arg."""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def hours_from_seconds(value):
    """Convert seconds to hours with 1 decimal place."""
    try:
        if value is None:
            return "N/A"
        return round(value.total_seconds() / 3600, 1)
    except (AttributeError, TypeError):
        return "N/A"
