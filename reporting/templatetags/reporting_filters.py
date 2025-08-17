from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    """
    Subtracts the arg from the value.
    
    Example usage: {{ value|subtract:arg }}
    """
    try:
        return value - arg
    except (ValueError, TypeError):
        return ''

@register.filter
def filter_by_date_and_competitor(queryset, args):
    """
    Filters a queryset of competitor data by date and competitor.
    
    Example usage: {{ competitor_data|filter_by_date_and_competitor:date:competitor }}
    """
    if not args or len(args) != 2:
        return None
    
    date, competitor = args
    
    try:
        return queryset.filter(date=date, competitor=competitor).first()
    except Exception:
        return None