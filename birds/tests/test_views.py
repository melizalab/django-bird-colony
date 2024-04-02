# -*- coding: utf-8 -*-
# -*- mode: python -*-
import uuid
import datetime

from django.urls import reverse
from django.test import TestCase
from django.contrib.auth import get_user_model

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

User = get_user_model()


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

    def test_bird_detail_404_invalid_bird_id(self):
        id = uuid.uuid4()
        response = self.client.get(reverse("birds:animal", args=[id]))
        self.assertEqual(response.status_code, 404)

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

    def test_bird_events_404_invalid_bird_id(self):
        id = uuid.uuid4()
        response = self.client.get(reverse("birds:animal_events", args=[id]))
        self.assertEqual(response.status_code, 404)

    def test_parent_event_list_at_correct_url(self):
        url = f"/birds/animals/{self.sire.uuid}/events/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_parent_detail_view_contains_all_related_objects(self):
        response = self.client.get(
            reverse("birds:animal_events", args=[self.sire.uuid])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["event_list"]), 4)

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


class NewAnimalFormViewTestCase(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    def setUp(self):
        # Create a user
        self.test_user1 = User.objects.create_user(
            username="testuser1", password="1X<ISRUkw+tuK"
        )
        self.test_user1.save()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse("birds:new_animal"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_initial_values_and_options(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("birds:new_animal"))
        self.assertEqual(response.status_code, 200)
        # TODO only status types that add should be given as options
        status_adds = Status.objects.filter(adds=True)

    def test_transfer_creates_bird_and_events(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        status = Status.objects.get(name="transferred in")
        species = Species.objects.get(pk=1)
        location = Location.objects.get(pk=1)
        response = self.client.post(
            reverse("birds:new_animal"),
            {
                "acq_status": status.pk,
                "acq_date": datetime.date.today() - datetime.timedelta(days=10),
                "sex": "M",
                "species": species.pk,
                "banding_date": datetime.date.today(),
                "band_number": 10,
                "location": location.pk,
                "user": self.test_user1.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        animal = Animal.objects.get(band_number=10)
        self.assertTrue(animal.alive())
        # one event for transfer and one for banding
        self.assertEqual(animal.event_set.count(), 2)
        self.assertRedirects(response, reverse("birds:animal", args=[animal.uuid]))

    def test_hatch_creates_bird_and_events(self):
        status = models.get_birth_event_type()
        location = Location.objects.get(pk=1)
        species = Species.objects.get(pk=1)
        sire = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=datetime.date.today() - datetime.timedelta(days=100),
            entered_by=self.test_user1,
            location=location,
            sex=Animal.Sex.MALE,
            band_number=1,
        )
        dam = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=datetime.date.today() - datetime.timedelta(days=100),
            entered_by=self.test_user1,
            location=location,
            sex=Animal.Sex.FEMALE,
            band_number=2,
        )
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("birds:new_animal"),
            {
                "acq_status": status.pk,
                "acq_date": datetime.date.today() - datetime.timedelta(days=10),
                "sex": "U",
                "sire": sire.pk,
                "dam": dam.pk,
                "banding_date": datetime.date.today(),
                "band_number": 10,
                "location": location.pk,
                "user": self.test_user1.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        animal = Animal.objects.get(band_number=10)
        self.assertTrue(animal.alive())
        # one event for transfer and one for banding
        self.assertEqual(animal.event_set.count(), 2)
        self.assertRedirects(response, reverse("birds:animal", args=[animal.uuid]))


class NewBandFormViewTest(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    def setUp(self):
        # Create a user
        self.test_user1 = User.objects.create_user(
            username="testuser1", password="1X<ISRUkw+tuK"
        )
        self.test_user1.save()
        # Create an unbanded animal
        species = Species.objects.get(pk=1)
        self.animal = Animal.objects.create(species=species)

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse("birds:new_band", args=[self.animal.uuid]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_initial_values_and_options(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("birds:new_band", args=[self.animal.uuid]))
        self.assertEqual(response.status_code, 200)

    def test_update_band(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("birds:new_band", args=[self.animal.uuid]),
            {
                "banding_date": datetime.date.today(),
                "sex": "M",
                "band_number": 10,
                "user": self.test_user1.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:animal", args=[self.animal.uuid]))
        animal = Animal.objects.get(band_number=10)
        self.assertEqual(animal.sex, "M")
        self.assertEqual(animal.event_set.count(), 1)


class NewEventFormViewTest(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    def setUp(self):
        # Create a user
        self.test_user1 = User.objects.create_user(
            username="testuser1", password="1X<ISRUkw+tuK"
        )
        self.test_user1.save()
        self.animal = Animal.objects.create_with_event(
            species=Species.objects.get(pk=1),
            status=models.get_birth_event_type(),
            date=datetime.date.today() - datetime.timedelta(days=365),
            entered_by=models.get_sentinel_user(),
            location=Location.objects.get(pk=1),
            sex=Animal.Sex.MALE,
            band_color=Color.objects.get(pk=1),
            band_number=1,
        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse("birds:new_event", args=[self.animal.uuid]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_initial_values_and_options(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("birds:new_event", args=[self.animal.uuid]))
        self.assertEqual(response.status_code, 200)

    def test_add_event(self):
        self.assertEqual(self.animal.event_set.count(), 1)
        self.assertTrue(self.animal.alive())
        status = Status.objects.get(name=models.DEATH_EVENT_NAME)
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("birds:new_event", args=[self.animal.uuid]),
            {
                "date": datetime.date.today(),
                "status": status.pk,
                "location": 1,
                "entered_by": self.test_user1.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:animal", args=[self.animal.uuid]))
        self.assertEqual(self.animal.event_set.count(), 2)
        self.assertFalse(self.animal.alive())


class PairingFormViewTest(TestCase):
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
        cls.pairing = Pairing.objects.create_with_events(
            sire=cls.sire,
            dam=cls.dam,
            began=birthday + datetime.timedelta(days=80),
            purpose="old pairing",
            entered_by=user,
            location=location,
        )
        cls.pairing.close(
            ended=birthday + datetime.timedelta(days=120),
            entered_by=user,
            location=location,
            comment="ended old pairing",
        )

    def setUp(self):
        # Create a user
        self.test_user1 = User.objects.create_user(
            username="testuser1", password="1X<ISRUkw+tuK"
        )
        self.test_user1.save()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse("birds:new_pairing"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))
        response = self.client.get(reverse("birds:end_pairing", args=[self.pairing.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_initial_values_and_options(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("birds:new_pairing"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("sire", response.context["form"].initial)
        self.assertNotIn("dam", response.context["form"].initial)

    def test_initial_values_from_previous_pairing(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("birds:new_pairing", args=[self.pairing.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["sire"], self.sire)
        self.assertEqual(response.context["form"].initial["dam"], self.dam)

    def test_initial_values_ending_pairing(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        new_pairing = Pairing.objects.create_with_events(
            sire=self.sire,
            dam=self.dam,
            began=datetime.date.today() - datetime.timedelta(days=10),
            purpose="new pairing",
            entered_by=self.test_user1,
            location=Location.objects.get(pk=1),
        )
        response = self.client.get(reverse("birds:end_pairing", args=[new_pairing.pk]))
        self.assertEqual(response.status_code, 200)

    def test_create_pairing(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        location = Location.objects.filter(nest=True).first()
        response = self.client.post(
            reverse("birds:new_pairing"),
            {
                "sire": self.sire.pk,
                "dam": self.dam.pk,
                "began": datetime.date.today(),
                "purpose": "evil",
                "entered_by": self.test_user1.pk,
                "location": location.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        pairing = Pairing.objects.active().first()
        self.assertRedirects(response, reverse("birds:pairing", args=[pairing.pk]))
        # new event for pairing creation + 2 for previous + 1 for birth
        self.assertEqual(self.sire.event_set.count(), 4)
        self.assertEqual(self.dam.event_set.count(), 4)

    def test_close_pairing(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        new_pairing = Pairing.objects.create_with_events(
            sire=self.sire,
            dam=self.dam,
            began=datetime.date.today() - datetime.timedelta(days=10),
            purpose="new pairing",
            entered_by=self.test_user1,
            location=Location.objects.get(pk=1),
        )
        response = self.client.post(
            reverse("birds:end_pairing", args=[new_pairing.pk]),
            {
                "ended": datetime.date.today(),
                "location": 1,
                "entered_by": self.test_user1.pk,
                "comment": "testing",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:pairing", args=[new_pairing.pk]))


# TODO: add sample to an existing bird using sample entry form
# Assert that sample is in the database and linked to the bird
# Assert that
