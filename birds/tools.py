# -*- coding: utf-8 -*-
# -*- mode: python -*-
""" Tools for classifying birds and computing summaries """


def sort_and_group(qs, key):
    """ Sort and group a queryset by a key function """
    from itertools import groupby
    return groupby(sorted(qs, key=key), key)


def find_first(iterable, predicate):
    """ Return the first item in iterable that matches predicate, or None if no match """
    for item in iterable:
        if predicate(item):
            return item
