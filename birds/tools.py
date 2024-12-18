# -*- coding: utf-8 -*-
# -*- mode: python -*-
""" Tools for classifying birds and computing summaries """
import datetime
from collections import Counter

from birds.models import Pairing


def sort_and_group(qs, key):
    """Sort and group a queryset by a key function"""
    from itertools import groupby

    return groupby(sorted(qs, key=key), key)


def find_first(iterable, predicate):
    """Return the first item in iterable that matches predicate, or None if no match"""
    for item in iterable:
        if predicate(item):
            return item


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
