# -*- coding: utf-8 -*-
# -*- mode: python -*-
""" Tools for classifying birds and computing summaries """
from birds.models import Age


def sort_and_group(qs, key):
    """ Sort and group a queryset by a key function """
    from itertools import groupby
    return groupby(sorted(qs, key=key), key)


def find_first(iterable, predicate):
    """ Return the first item in iterable that matches predicate, or None if no match """
    for item in iterable:
        if predicate(item):
            return item


def classify_ages(iterable, default_age="adult"):
    """ Classifies birds by age using the age table, probably very inefficiently"""
    # this seems horrendously inefficient to create a lambda for each animal, but for
    # some reason it doesn't work to pre-generate the lambdas.
    ages = tuple(Age.objects.order_by("species", "-min_days").values_list("species", "min_days", "name"))
    for animal in iterable:
        species = animal.species.id
        age_days = animal.age_days()
        try:
            age_name = find_first(ages, lambda age: (age[0] == species) and (age[1] <= age_days))[2]
        except TypeError:
            age_name = default_age
        yield (animal, age_name)


def classify_all(iterable, default_age="adult"):
    """ Generates a unique classification based on species, age, and sex. """
    for animal, age_name in classify_ages(iterable, default_age):
        yield (animal, "{0.species} {1}s ({0.sex})".format(animal, age_name))