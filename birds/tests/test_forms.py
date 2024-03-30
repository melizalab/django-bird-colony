# -*- coding: utf-8 -*-
# -*- mode: python -*-
import datetime

from django.test import TestCase

from birds import models
from birds.models import Animal, Location, Plumage, Color, Status, Species
from birds.forms import (
    NewBandForm,
    ReservationForm,
    SexForm,
    NewAnimalForm,
    NestCheckForm,
    NewPairingForm,
)


class SexFormTest(TestCase):
    def test_without_note_status(self):
        user = models.get_sentinel_user()
        form = SexForm({"date": datetime.date.today(), "sex": "M", "entered_by": user})
        self.assertFalse(form.is_valid())

    def test_with_note_status(self):
        _ = Status.objects.get_or_create(name=models.NOTE_EVENT_NAME)
        user = models.get_sentinel_user()
        form = SexForm({"date": datetime.date.today(), "sex": "M", "entered_by": user})
        self.assertTrue(form.is_valid())


class ReservationFormTest(TestCase):
    def test_without_reservation_status(self):
        user = models.get_sentinel_user()
        form = ReservationForm({"date": datetime.date.today(), "entered_by": user})
        self.assertFalse(form.is_valid())

    def test_with_reservation_status(self):
        _ = Status.objects.get_or_create(name=models.RESERVATION_EVENT_NAME)
        user = models.get_sentinel_user()
        form = ReservationForm({"date": datetime.date.today(), "entered_by": user})
        self.assertTrue(form.is_valid())

    def test_without_user(self):
        _ = Status.objects.get_or_create(name=models.RESERVATION_EVENT_NAME)
        user = models.get_sentinel_user()
        form = ReservationForm({"date": datetime.date.today()})
        self.assertTrue(form.is_valid())


class NewBandFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        species = Species.objects.create(
            common_name="eurasian magpie", genus="pica", species="pica", code="EUMA"
        )
        cls.plumage = Plumage.objects.create(name="standard")
        cls.color = Color.objects.create(name="blue", abbrv="bl")
        cls.location = Location.objects.create(name="home")
        cls.animal = Animal.objects.create(
            species=species,
            sex=Animal.Sex.MALE,
            band_color=cls.color,
            plumage=cls.plumage,
            band_number=20,
        )

    def test_without_banded_status(self):
        user = models.get_sentinel_user()
        form = NewBandForm(
            {
                "banding_date": datetime.date.today(),
                "band_number": 10,
                "sex": "M",
                "user": user,
            }
        )
        self.assertFalse(form.is_valid())

    def test_with_banded_status(self):
        _ = Status.objects.get_or_create(name=models.BANDED_EVENT_NAME)
        user = models.get_sentinel_user()
        form = NewBandForm(
            {
                "banding_date": datetime.date.today(),
                "band_number": 10,
                "sex": "M",
                "user": user,
            }
        )
        self.assertTrue(form.is_valid())

    def test_band_already_exists(self):
        _ = Status.objects.get_or_create(name=models.BANDED_EVENT_NAME)
        user = models.get_sentinel_user()
        form = NewBandForm(
            {
                "banding_date": datetime.date.today(),
                "band_color": self.color,
                "band_number": 20,
                "sex": "M",
                "user": user,
            }
        )
        self.assertFalse(form.is_valid())

    def test_with_all_fields(self):
        _ = Status.objects.get_or_create(name=models.BANDED_EVENT_NAME)
        user = models.get_sentinel_user()
        form = NewBandForm(
            {
                "banding_date": datetime.date.today(),
                "band_color": self.color,
                "plumage": self.plumage,
                "location": self.location,
                "band_number": 40,
                "sex": "F",
                "user": user,
            }
        )
        self.assertTrue(form.is_valid())


class NewAnimalFormTest(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    @classmethod
    def setUpTestData(cls):
        status = models.get_birth_event_type()
        birthday = datetime.date.today() - datetime.timedelta(days=365)
        cls.user = models.get_sentinel_user()
        cls.location = Location.objects.get(pk=2)
        cls.species = Species.objects.get(pk=1)
        cls.sire = Animal.objects.create_with_event(
            species=cls.species,
            status=status,
            date=birthday,
            entered_by=cls.user,
            location=cls.location,
            sex=Animal.Sex.MALE,
            band_number=1,
        )
        cls.dam = Animal.objects.create_with_event(
            species=cls.species,
            status=status,
            date=birthday,
            entered_by=cls.user,
            location=cls.location,
            sex=Animal.Sex.FEMALE,
        )

    def test_add_by_transfer(self):
        acq_on = datetime.date.today() - datetime.timedelta(days=10)
        acq_status = Status.objects.get(name="transferred in")
        form = NewAnimalForm(
            {
                "acq_status": acq_status,
                "acq_date": acq_on,
                "banding_date": datetime.date.today(),
                "sex": "M",
                "species": self.species,
                "band_number": 100,
                "location": self.location,
                "user": self.user,
            }
        )
        self.assertTrue(form.is_valid())

    def test_add_by_transfer_requires_species(self):
        acq_on = datetime.date.today() - datetime.timedelta(days=10)
        acq_status = Status.objects.get(name="transferred in")
        form = NewAnimalForm(
            {
                "acq_status": acq_status,
                "acq_date": acq_on,
                "banding_date": datetime.date.today(),
                "sex": "M",
                "band_number": 100,
                "location": self.location,
                "user": self.user,
            }
        )
        self.assertFalse(form.is_valid())

    def test_add_from_parents(self):
        acq_on = datetime.date.today() - datetime.timedelta(days=10)
        acq_status = models.get_birth_event_type()
        form = NewAnimalForm(
            {
                "acq_status": acq_status,
                "acq_date": acq_on,
                "banding_date": datetime.date.today(),
                "sex": "U",
                "sire": self.sire,
                "dam": self.dam,
                "band_number": 100,
                "location": self.location,
                "user": self.user,
            }
        )
        self.assertTrue(form.is_valid())

    def test_add_from_one_parent(self):
        acq_on = datetime.date.today() - datetime.timedelta(days=10)
        acq_status = models.get_birth_event_type()
        form = NewAnimalForm(
            {
                "acq_status": acq_status,
                "acq_date": acq_on,
                "banding_date": datetime.date.today(),
                "sex": "U",
                "sire": self.sire,
                "band_number": 100,
                "location": self.location,
                "user": self.user,
            }
        )
        self.assertFalse(form.is_valid())

    def test_add_from_mismatched_parent(self):
        acq_on = datetime.date.today() - datetime.timedelta(days=10)
        acq_status = models.get_birth_event_type()
        species = Species.objects.create(
            common_name="eurasian magpie", genus="pica", species="pica", code="EUMA"
        )
        wrong_dam = Animal.objects.create_with_event(
            species=species,
            status=acq_status,
            date=datetime.date.today() - datetime.timedelta(days=10),
            entered_by=self.user,
            location=self.location,
            sex=Animal.Sex.MALE,
        )
        form = NewAnimalForm(
            {
                "acq_status": acq_status,
                "acq_date": acq_on,
                "banding_date": datetime.date.today(),
                "sex": "U",
                "sire": self.sire,
                "dam": wrong_dam,
                "band_number": 100,
                "location": self.location,
                "user": self.user,
            }
        )
        self.assertFalse(form.is_valid())

    def test_band_already_exists(self):
        acq_on = datetime.date.today() - datetime.timedelta(days=10)
        acq_status = Status.objects.get(name="transferred in")
        form = NewAnimalForm(
            {
                "acq_status": acq_status,
                "acq_date": acq_on,
                "banding_date": datetime.date.today(),
                "sex": "M",
                "species": self.species,
                "band_number": 1,
                "location": self.location,
                "user": self.user,
            }
        )
        self.assertFalse(form.is_valid())


# TODO: this one is pretty hairy
# class NestCheckFormTest(TestCase):
#     fixtures = ["bird_colony_starter_kit"]
