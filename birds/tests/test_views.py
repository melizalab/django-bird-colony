# -*- coding: utf-8 -*-
# -*- mode: python -*-
import datetime

from django.urls import reverse
from django.test import TestCase

from birds import views, models
from birds.models import (
    Animal,
    Species,
    Event,
    Color,
    Status,
    Location,
    Pairing,
    Plumage,
)


class AnimalViewTest(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    @classmethod
    def setUpTestData(cls):
        birthday = datetime.date.today() - datetime.timedelta(days=365)
        status = models.get_birth_event_type()
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=1)
        species = Species.objects.get(pk=1)
        band_color = Color.objects.get(pk=1)
        cls.sire = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=birthday,
            entered_by=user,
            location=location,
            sex=Animal.Sex.MALE,
            band_color=band_color,
            band_number=1,
        )
        cls.dam = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=birthday,
            entered_by=user,
            location=location,
            sex=Animal.Sex.FEMALE,
            band_color=band_color,
            band_number=2,
        )
        cls.n_children = 10
        cls.n_eggs = 5
        pairing = Pairing.objects.create_with_events(
            sire=cls.sire,
            dam=cls.dam,
            began=birthday + datetime.timedelta(days=80),
            purpose="old pairing",
            entered_by=user,
            location=location,
        )
        pairing.close(
            ended=birthday + datetime.timedelta(days=120),
            entered_by=user,
            location=location,
            comment="ended old pairing",
        )
        for i in range(cls.n_children):
            _child = Animal.objects.create_from_parents(
                sire=cls.sire,
                dam=cls.dam,
                date=birthday + datetime.timedelta(days=90 + i),
                status=status,
                entered_by=user,
                location=location,
                description="for unto us a child is born",
                sex=Animal.Sex.UNKNOWN_SEX,
                band_color=band_color,
                band_number=10 + i,
            )
        _pairing = Pairing.objects.create_with_events(
            sire=cls.sire,
            dam=cls.dam,
            began=datetime.date.today() - datetime.timedelta(days=20),
            purpose="new pairing",
            entered_by=user,
            location=location,
        )
        status = models.get_unborn_creation_event_type()
        for i in range(cls.n_eggs):
            _child = Animal.objects.create_from_parents(
                sire=cls.sire,
                dam=cls.dam,
                date=datetime.date.today() - datetime.timedelta(days=i),
                status=status,
                entered_by=user,
                location=location,
                description=f"egg {i} laid",
                sex=Animal.Sex.UNKNOWN_SEX,
            )

    def test_list_view_url_exists_at_desired_location(self):
        response = self.client.get("/birds/animals/")
        self.assertEqual(response.status_code, 200)

    def test_list_view_contains_all_animals(self):
        response = self.client.get(reverse("birds:animals"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.context["animal_list"]), 2 + self.n_children + self.n_eggs
        )

    def test_living_list_view(self):
        response = self.client.get(reverse("birds:animals") + "?living=True")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["animal_list"]), 2 + self.n_children)

    def test_event_view_url_exists_at_desired_location(self):
        response = self.client.get("/birds/events/")
        self.assertEqual(response.status_code, 200)

    def test_event_view_contains_all_events(self):
        response = self.client.get(reverse("birds:events"))
        self.assertEqual(response.status_code, 200)
        # one event per animal + 3 events per parent for pairing start/end
        self.assertEqual(
            len(response.context["event_list"]), 2 + self.n_children + self.n_eggs + 6
        )

    def test_parent_detail_view_url_exists_at_desired_location(self):
        url = f"/birds/animals/{self.sire.uuid}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_parent_detail_view_contains_all_related_objects(self):
        response = self.client.get(reverse("birds:animal", args=[self.sire.uuid]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.context["animal_list"]), self.n_children + self.n_eggs
        )
        # one hatch, old pairing started and ended, new pairing started
        self.assertEqual(len(response.context["event_list"]), 4)
        self.assertEqual(len(response.context["pairing_list"]), 2)

    def test_pairing_list_url_exists_at_desired_location(self):
        response = self.client.get("/birds/pairings/")
        self.assertEqual(response.status_code, 200)

    def test_pairing_list_contains_all_pairings(self):
        response = self.client.get(reverse("birds:pairings"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["pairing_list"]), 2)

    def test_active_pairing_list_url_exists_at_desired_location(self):
        response = self.client.get("/birds/pairings/active/")
        self.assertEqual(response.status_code, 200)

    def test_active_pairing_list_contains_only_active_pairings(self):
        response = self.client.get(reverse("birds:pairings_active"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["pairing_list"]), 1)


# TODO: transfer in male and female birds using new animal form entry.
# Assert that the birds are in the database and listed as alive
# Assert that transfer and banding events exist

# TODO: create child of existing male and female bird using new animal form entry.
# Assert that child is in the database and has the correct parents, species, etc
# Assert that hatch and banding events exist

# TODO: band an existing animal
# Assert that the animal displays its uuid-based name before and its band-based
# name after.

# TODO: create clutch using clutch form
# Assert that children exist and have correct parents and species

# TODO: add death event to an existing bird using event entry form
# Assert that the bird is no longer listed as alive.

# TODO: add sample to an existing bird using sample entry form
# Assert that sample is in the database and linked to the bird
# Assert that
