from django import template

register = template.Library()

@register.simple_tag
def fullurl(value):
    # Example implementation
    return f"http://127.0.0.1:8000/birds/{value}"
