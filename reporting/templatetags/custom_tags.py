# reporting/templatetags/custom_tags.py
from django import template

register = template.Library()

@register.simple_tag
def get_competitor_data(competitor_data, date, competitor):
    try:
        return competitor_data.get(date=date, competitor=competitor)
    except Exception:
        return None