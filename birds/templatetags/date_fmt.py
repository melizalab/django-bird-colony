# -*- coding: utf-8 -*-
# -*- mode: python -*-
from django import template

register = template.Library()

@register.filter
def agestr(value):
    try:
        return "{}y {:3}d".format(value // 365, value % 365)
    except TypeError:
        return "unknown"
