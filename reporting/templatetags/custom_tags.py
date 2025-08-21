# reporting/templatetags/custom_tags.py
from django import template

register = template.Library()

@register.simple_tag
def get_competitor_data(competitor_data, date, competitor):
    try:
        return competitor_data.get(date=date, competitor=competitor)
    except Exception:
        return None

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary by key
    Usage: {{ my_dict|get_item:key_variable }}
    """
    return dictionary.get(key) if dictionary else None