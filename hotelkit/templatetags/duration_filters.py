from django import template

register = template.Library()


@register.filter
def format_duration(value):
    if not value:
        return 'N/A'
    try:
        total_seconds = int(value.total_seconds())
    except Exception:
        return 'N/A'
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if not parts:
        parts.append(f"{seconds}s")
    return ' '.join(parts)


