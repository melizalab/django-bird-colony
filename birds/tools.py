# -*- coding: utf-8 -*-
# -*- mode: python -*-
""" Tools for classifying birds and computing summaries """
import datetime
from collections import Counter, defaultdict

from birds.models import ADULT_ANIMAL_NAME, Animal, Event, Location, Pairing


def sort_and_group(qs, key):
    """Sort and group a queryset by a key function"""
    from itertools import groupby

    return groupby(sorted(qs, key=key), key)


def find_first(iterable, predicate):
    """Return the first item in iterable that matches predicate, or None if no match"""
    for item in iterable:
        if predicate(item):
            return item


# old version of this function
def tabulate_locations(since, until):
    """Determines which animals are in which nests by date.

    In principle, it would be best to do this by using the database to
    generate a summary for day 0, then march through the subsequent days and
    use new events to generate new summaries. However, in practice it's not
    trivial to update this structure, so we're taking the lazy but probably
    more inefficient route of querying the database for each day. Consider
    the other option if it becomes too slow.

    """
    repdate = since
    nests = Location.objects.filter(nest=True).order_by("name")
    dates = []
    data = {}
    while repdate <= until:
        locations = defaultdict(list)
        alive = Animal.objects.existing(repdate)
        qs = (
            Event.objects.has_location()
            .latest_by_animal()
            .select_related("location", "animal")
            .filter(date__lte=repdate, animal__in=alive)
        )
        for event in qs:
            if event.location.nest:
                locations[event.location].append(event.animal)
        data[repdate] = locations
        dates.append(repdate)
        repdate += datetime.timedelta(days=1)
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


def tabulate_nests(since: datetime.date, until: datetime.date):
    """Determines which animals are in which nests by date.

    In principle, it would be best to do this by using the database to generate
    a summary for day 0, then march through the subsequent days and use new
    events to generate new summaries. However, in practice it's not trivial to
    update this structure, so we're taking the lazy but probably more
    inefficient route of querying the database for each day and each nest.
    Consider the other option if it becomes too slow.

    """
    if since > until:
        raise ValueError("until must be after since")
    n_days = (until - since).days + 1
    dates = [since + datetime.timedelta(days=x) for x in range(n_days)]
    data = []
    for nest in Location.objects.filter(nest=True).order_by("name"):
        days = []
        for date in dates:
            by_group = defaultdict(list)
            counts = Counter()
            birds = (
                nest.birds(date)
                .existing(date)
                .with_dates(date)
                .select_related("species", "band_color")
                .prefetch_related("species__age_set")
                .order_by("band_color", "band_number")
            )
            for bird in birds:
                age_group = bird.age_group()
                by_group[age_group].append(bird)
                if age_group is not None and age_group != ADULT_ANIMAL_NAME:
                    counts[age_group] += 1
            days.append({"animals": dict(by_group), "counts": dict(counts)})
        data.append({"location": nest, "days": days})
    return dates, data


def tabulate_pairs(
    since: datetime.date, until: datetime.date, only_active: bool = False
):
    """Counts the number of chicks of each age group in all pairing over a range
    of dates (since to until, inclusive). If `only_active` is True, only pairs
    that are active on `until` are included; otherwise all pairs that were
    active at any point between `since` and `until` are used.

    TODO: move this logic into the Pairing model and let the caller decide which
    pairs to look at over which dates.

    """
    if since > until:
        raise ValueError("until must be after since")
    n_days = (until - since).days + 1
    dates = dates = [since + datetime.timedelta(days=x) for x in range(n_days)]
    if only_active:
        active_pairs = Pairing.objects.active(on_date=until).order_by("-began_on")
    else:
        active_pairs = Pairing.objects.active_between(since, until).order_by(
            "-began_on"
        )
    data = []
    for pair in active_pairs:
        location = pair.last_location(on_date=until)
        eggs = pair.eggs().with_dates().with_related()
        days = []
        for date in dates:
            counts = Counter()
            if pair.ended_on is not None and date > pair.ended_on:
                pass
            else:
                for animal in eggs:
                    # dead/lost animals are not counted
                    if animal.died_on is None or animal.died_on > date:
                        age_group = animal.age_group(date)
                        if age_group is not None:
                            counts[age_group] += 1
            days.append(counts)
        data.append({"pair": pair, "location": location, "counts": days})
    return dates, data


# Expressions for annotating animal records with names. This avoids a bunch of
# related table lookups
# _short_uuid_expr = Substr(Cast("uuid", output_field=CharField()), 1, 8)
# _band_expr = Concat(
#     "band_color__name", Value("_"), "band_number", output_field=CharField()
# )
# _animal_name_expr = Concat(
#     "species__code",
#     Value("_"),
#     Case(
#         When(band_number__isnull=True, then=_short_uuid_expr),
#         When(
#             band_color__isnull=True, then=Cast("band_number", output_field=CharField())
#         ),
#         default=_band_expr,
#     ),
#     output_field=CharField(),
# )

# Expressions for calculating age in the database
