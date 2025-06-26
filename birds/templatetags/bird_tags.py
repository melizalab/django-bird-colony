# -*- mode: python -*-
from django import template
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html, format_html_join

register = template.Library()


@register.filter
def ageorblank(value):
    try:
        days = value.days
        return f"{days // 365}y {days % 365:3}d"
    except (TypeError, AttributeError):
        return ""


@register.filter
def agestr(value):
    try:
        days = value.days
        return f"{days // 365}y {days % 365:3}d"
    except (TypeError, AttributeError):
        return "unknown"


@register.filter
def join_and(value):
    """Given a list of strings, format them with commas and spaces, but
    with 'and' at the end.

    >>> join_and(['apples', 'oranges', 'pears'])
    "apples, oranges, and pears"

    """
    if len(value) == 1:
        return value[0]

    # join all but the last element
    all_but_last = ", ".join(value[:-1])
    return f"{all_but_last}, and {value[-1]}"


@register.filter
def url_list(values):
    """Generate a comma-separated list of links to birds"""
    return format_html_join(
        ", ", '<a href="{}">{}</a>', ((obj.get_absolute_url(), obj) for obj in values)
    )


@register.filter
def count_summary(counter, join_by=", "):
    """Generate a summary of counts"""
    if counter is None:
        return "(not active)"
    return format_html_join(
        join_by, "{}s: {}", ((k, v) for k, v in sorted(counter.items()))
    )


@register.filter
def count_total(counter):
    """Call the total() method on a Counter"""
    return f"{counter.total()}"


@register.filter
def item_at(arr, index):
    """Return an item from a sequence by index"""
    try:
        return arr[index]
    except (ValueError, IndexError, TypeError):
        return None


@register.filter
def link_to(obj, url_name):
    """Create a link to an object if it exists"""
    try:
        url = reverse(url_name, args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj)
    except NoReverseMatch:
        return str(obj)
    except AttributeError:
        return ""


@register.filter
def link_or_blank(obj):
    try:
        url = obj.get_absolute_url()
        return format_html('<a href="{}">{}</a>', url, obj)
    except NoReverseMatch:
        return str(obj)
    except AttributeError:
        return ""
