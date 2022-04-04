# -*- coding: utf-8 -*-
# -*- mode: python -*-
""" Tools for classifying birds and computing summaries """


def sort_and_group(qs, key):
    """Sort and group a queryset by a key function"""
    from itertools import groupby

    return groupby(sorted(qs, key=key), key)


def find_first(iterable, predicate):
    """Return the first item in iterable that matches predicate, or None if no match"""
    for item in iterable:
        if predicate(item):
            return item


def tabulate_locations(since, until):
    """Determines which animals are in which nests by date.

    In principle, it would be best to do this by using the database to
    generate a summary for day 0, then march through the subsequent days and
    use new events to generate new summaries. However, in practice it's not
    trivial to update this structure, so we're taking the lazy but probably
    more inefficient route of querying the database for each day. Consider
    the other option if it becomes too slow.

    """
    from birds.models import Animal, Event, Location, ADULT_ANIMAL_NAME
    from datetime import timedelta
    from collections import defaultdict, Counter

    repdate = since
    nests = Location.objects.filter(nest=True).order_by("name")
    dates = []
    data = {}
    while repdate <= until:
        locations = defaultdict(list)
        alive = Animal.living.exists(repdate)
        for event in Event.latest.filter(date__lte=repdate, animal__in=alive):
            if event.location.nest:
                locations[event.location].append(event.animal)
        data[repdate] = locations
        dates.append(repdate)
        repdate += timedelta(days=1)
    # pivot the structure while tabulating by age group to help the template engine
    nest_data = []
    for nest in nests:
        days = []
        for date in dates:
            animals = data[date].get(nest, [])
            locdata = {"animals": defaultdict(list), "counts": Counter()}
            for animal in animals:
                age_group = animal.age_group(date)
                locdata["animals"][age_group].append(animal)
                if age_group != ADULT_ANIMAL_NAME:
                    locdata["counts"][age_group] += 1
            days.append(locdata)
        nest_data.append({"location": nest, "days": days})
    return dates, nest_data
