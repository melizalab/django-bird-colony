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

    def test_pair_created_today(self):
        until = datetime.date.today()
        since = until - datetime.timedelta(days=3)
        began_on = until
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
        self.assertEqual(pair_data["location"], self.nest)

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
            status=Status.objects.get(name=models.BAD_EGG_EVENT_NAME),
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

    def test_pair_created_today_only_active(self):
        until = datetime.date.today()
        since = until - datetime.timedelta(days=3)
        began_on = until
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
        self.assertEqual(pair_data["location"], self.nest)

    def test_excludes_dead_chicks(self):
        """Test that tabulate_pairs doesn't count dead chicks"""
        user = models.get_sentinel_user()
        until = datetime.date.today()
        since = until - datetime.timedelta(days=3)
        # Create pairing
        pair = Pairing.objects.create_with_events(
            sire=self.sire,
            dam=self.dam,
            began_on=since,
            purpose="testing",
            entered_by=user,
            location=self.nest,
        )
        # Create and hatch two eggs
        eggs = [
            Animal.objects.create_from_parents(
                sire=self.sire,
                dam=self.dam,
                date=since + datetime.timedelta(days=1),
                status=models.get_unborn_creation_event_type(),
                entered_by=user,
                location=self.nest,
            )
            for _ in range(2)
        ]
        # Both eggs hatch
        for egg in eggs:
            Event.objects.create(
                animal=egg,
                status=models.get_birth_event_type(),
                date=since + datetime.timedelta(days=2),
                entered_by=user,
            )
        # One chick dies
        Event.objects.create(
            animal=eggs[1],
            status=models.get_death_event_type(),
            date=until,
            entered_by=user,
        )
        # make sure we see the right number of living chicks in the db
        self.assertEqual(pair.eggs().alive().count(), 1)
        # check the tabulatio
        _, data = tools.tabulate_pairs(until, until)
        pair_data = next(p for p in data if p["pair"] == pair)
        tabulated_counts = pair_data["counts"][0]
        tabulated_total = sum(tabulated_counts.values())
        tabulated_eggs = tabulated_counts.get("egg", 0)
        tabulated_chicks = tabulated_total - tabulated_eggs
        self.assertEqual(tabulated_chicks, 1, "Should have 1 living chick")
