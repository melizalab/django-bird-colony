# -*- coding: utf-8 -*-
# -*- mode: python -*-
import datetime

from django.test import TestCase

from birds import models, tools
from birds.models import (
    Animal,
    Event,
    Location,
    Pairing,
    Species,
    Status,
)


class TabulateNestTest(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    @classmethod
    def setUpTestData(cls):
        birthday = datetime.date.today() - datetime.timedelta(days=365)
        status = models.get_birth_event_type()
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=1)
        species = Species.objects.get(pk=1)
        cls.sire = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=birthday,
            entered_by=user,
            location=location,
            sex=Animal.Sex.MALE,
            band_number=1,
        )
        cls.dam = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=birthday,
            entered_by=user,
            location=location,
            sex=Animal.Sex.FEMALE,
            band_number=2,
        )
        cls.nest = Location.objects.filter(nest=True).first()

    def test_since_after_until(self):
        until = datetime.date.today()
        since = until - datetime.timedelta(days=3)
        with self.assertRaises(ValueError):
            _ = tools.tabulate_nests(until, since)

    def test_empty_nests(self):
        until = datetime.date.today()
        since = until - datetime.timedelta(days=3)
        dates, data = tools.tabulate_nests(since, until)
        self.assertEqual(len(dates), 4)
        self.assertEqual(dates[0], since)
        self.assertEqual(dates[-1], until)
        self.assertEqual(len(data), 1)  # one nest
        loc_data = data[0]
        self.assertEqual(loc_data["location"], self.nest)
        self.assertEqual(len(loc_data["days"]), 4)
        for day in loc_data["days"]:
            self.assertEqual(day, {"animals": {}, "counts": {}})

    def test_nest_has_inhabitants_on_correct_days(self):
        user = models.get_sentinel_user()
        until = datetime.date.today()
        since = until - datetime.timedelta(days=4)
        status_laid = models.get_unborn_creation_event_type()
        status_hatched = models.get_birth_event_type()
        # day 1: move in the parents
        _ = Pairing.objects.create_with_events(
            sire=self.sire,
            dam=self.dam,
            began_on=since + datetime.timedelta(days=1),
            purpose="testing",
            entered_by=user,
            location=self.nest,
        )
        # day 2: add an egg
        child_1 = Animal.objects.create_from_parents(
            sire=self.sire,
            dam=self.dam,
            date=since + datetime.timedelta(days=2),
            status=status_laid,
            entered_by=user,
            location=self.nest,
            description="testing 123",
        )
        # day 3: hatch the egg and add another
        _ = Event.objects.create(
            animal=child_1,
            status=status_hatched,
            location=self.nest,
            date=since + datetime.timedelta(days=3),
            entered_by=user,
        )
        child_2 = Animal.objects.create_from_parents(
            sire=self.sire,
            dam=self.dam,
            date=since + datetime.timedelta(days=3),
            status=status_laid,
            entered_by=user,
            location=self.nest,
            description="testing 123",
        )
        # day 4: lose the second egg
        _ = Event.objects.create(
            animal=child_2,
            status=Status.objects.get(name=models.LOST_EVENT_NAME),
            location=self.nest,
            date=since + datetime.timedelta(days=4),
            entered_by=user,
        )
        _, data = tools.tabulate_nests(since, until)
        loc_data = data[0]
        self.assertEqual(loc_data["location"], self.nest)
        days = loc_data["days"]
        self.assertDictEqual(days[0], {"animals": {}, "counts": {}})
        self.assertDictEqual(
            days[1], {"animals": {"adult": [self.sire, self.dam]}, "counts": {}}
        )
        self.assertDictEqual(
            days[2],
            {
                "animals": {"adult": [self.sire, self.dam], "egg": [child_1]},
                "counts": {"egg": 1},
            },
        )
        self.assertDictEqual(
            days[3],
            {
                "animals": {
                    "adult": [self.sire, self.dam],
                    "hatchling": [child_1],
                    "egg": [child_2],
                },
                "counts": {"hatchling": 1, "egg": 1},
            },
        )
        self.assertDictEqual(
            days[4],
            {
                "animals": {
                    "adult": [self.sire, self.dam],
                    "hatchling": [child_1],
                },
                "counts": {"hatchling": 1},
            },
        )


class TabulatePairsTests(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    @classmethod
    def setUpTestData(cls):
        birthday = datetime.date.today() - datetime.timedelta(days=365)
        status = models.get_birth_event_type()
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=1)
        species = Species.objects.get(pk=1)
        cls.sire = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=birthday,
            entered_by=user,
            location=location,
            sex=Animal.Sex.MALE,
            band_number=1,
        )
        cls.dam = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=birthday,
            entered_by=user,
            location=location,
            sex=Animal.Sex.FEMALE,
            band_number=2,
        )
        cls.nest = Location.objects.filter(nest=True).first()

    def test_since_after_until(self):
        until = datetime.date.today()
        since = until - datetime.timedelta(days=3)
        with self.assertRaises(ValueError):
            _ = tools.tabulate_pairs(until, since)

    def test_empty_pairs(self):
        until = datetime.date.today()
        since = until - datetime.timedelta(days=3)
        began_on = since + datetime.timedelta(days=1)
        pair = Pairing.objects.create_with_events(
            sire=self.sire,
            dam=self.dam,
            began_on=began_on,
            purpose="testing",
            entered_by=models.get_sentinel_user(),
            location=self.nest,
        )
        dates, data = tools.tabulate_pairs(since, until)
        self.assertEqual(len(dates), 4)
        self.assertEqual(dates[0], since)
        self.assertEqual(dates[-1], until)
        self.assertEqual(len(data), 1)  # one nest
        pair_data = data[0]
        self.assertEqual(pair_data["pair"], pair)
        self.assertEqual(len(pair_data["counts"]), 4)
        for day in pair_data["counts"]:
            self.assertEqual(day, {})

    def test_pair_has_progeny_on_correct_days(self):
        user = models.get_sentinel_user()
        until = datetime.date.today()
        since = until - datetime.timedelta(days=4)
        status_laid = models.get_unborn_creation_event_type()
        status_hatched = models.get_birth_event_type()
        # day 1: move in the parents
        pair = Pairing.objects.create_with_events(
            sire=self.sire,
            dam=self.dam,
            began_on=since + datetime.timedelta(days=1),
            purpose="testing",
            entered_by=user,
            location=self.nest,
        )
        # day 2: add an egg
        child_1 = Animal.objects.create_from_parents(
            sire=self.sire,
            dam=self.dam,
            date=since + datetime.timedelta(days=2),
            status=status_laid,
            entered_by=user,
            location=self.nest,
            description="testing 123",
        )
        # day 3: hatch the egg and add another
        _ = Event.objects.create(
            animal=child_1,
            status=status_hatched,
            location=self.nest,
            date=since + datetime.timedelta(days=3),
            entered_by=user,
        )
        child_2 = Animal.objects.create_from_parents(
            sire=self.sire,
            dam=self.dam,
            date=since + datetime.timedelta(days=3),
            status=status_laid,
            entered_by=user,
            location=self.nest,
            description="testing 123",
        )
        # day 4: lose the second egg
        _ = Event.objects.create(
            animal=child_2,
            status=Status.objects.get(name=models.LOST_EVENT_NAME),
            location=self.nest,
            date=since + datetime.timedelta(days=4),
            entered_by=user,
        )
        _, data = tools.tabulate_pairs(since, until)
        pair_data = data[0]
        self.assertEqual(pair_data["pair"], pair)
        counts = pair_data["counts"]
        self.assertDictEqual(counts[0], {})
        self.assertDictEqual(counts[1], {})
        self.assertDictEqual(counts[2], {"egg": 1})
        self.assertDictEqual(counts[3], {"hatchling": 1, "egg": 1})
        self.assertDictEqual(counts[4], {"hatchling": 1})

    def test_only_active(self):
        until = datetime.date.today()
        since = until - datetime.timedelta(days=3)
        pair = Pairing.objects.create_with_events(
            sire=self.sire,
            dam=self.dam,
            began_on=since,
            purpose="testing",
            entered_by=models.get_sentinel_user(),
            location=self.nest,
        )
        pair.close(
            until - datetime.timedelta(days=1), entered_by=models.get_sentinel_user()
        )
        dates, data = tools.tabulate_pairs(since, until, only_active=True)
        self.assertEqual(len(data), 0)
