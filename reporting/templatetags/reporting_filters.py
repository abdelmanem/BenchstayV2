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

@register.filter
def format_currency_short(value):
    """
    Formats large numbers with K for thousands and M for millions.
    
    Example usage: {{ value|format_currency_short }}
    """
    if value is None or value == '':
        return ''
    
    try:
        number = float(value)
        if number >= 1000000:
            return f"{number / 1000000:.1f}M"
        elif number >= 1000:
            return f"{number / 1000:.1f}K"
        else:
            return f"{number:.0f}"
    except (ValueError, TypeError):
        return str(value)

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
    Example usage in Python:
        competitor_data|filter_by_date_and_competitor:(date, competitor)
    """
    if not args or len(args) != 2:
        return None

    date, competitor = args

    try:
        return queryset.filter(date=date, competitor=competitor).first()
    except Exception:
        return None


@register.filter
def get_item(dictionary, key):
    """
    Returns a dictionary item by key.
    Example usage: {{ mydict|get_item:"mykey" }}
    """
    if dictionary and isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
        