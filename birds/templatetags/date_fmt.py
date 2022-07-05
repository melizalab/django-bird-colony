# -*- coding: utf-8 -*-
# -*- mode: python -*-
from django import template
from django.utils.html import format_html_join

register = template.Library()

@register.filter
def ageorblank(value):
    try:
        return "{}y {:3}d".format(value // 365, value % 365)
    except TypeError:
        return ""


@register.filter
def agestr(value):
    try:
        return "{}y {:3}d".format(value // 365, value % 365)
    except TypeError:
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
    return "%s, and %s" % (all_but_last, value[-1])


@register.filter
def url_list(values):
    """ Generate a comma-separated list of links to birds """
    return format_html_join(", ", '<a href="{}">{}</a>',
                            ((obj.get_absolute_url(), obj) for obj in values))

@register.filter
def count_summary(counter):
    """ Generate a summary of counts """
    return format_html_join(", ", '{}s: {}', ((k, v) for k, v in sorted(counter.items())))


@register.simple_tag
def age_at(animal, event):
    """ Returns the age of the animal at a given event (or None, if birthday is not known) """
    from birds.models import BIRTH_EVENT_NAME
    evt_birth = animal.event_set.filter(status__name=BIRTH_EVENT_NAME).first()
    if evt_birth is None:
        return ""
    diff = (event.date - evt_birth.date).days
    if diff < 0:
        return ""
    return agestr(diff)
    
