# -*- coding: utf-8 -*-
# -*- mode: python -*-
import datetime
import warnings

from django.test import TestCase
from django.forms import formset_factory

from birds import models
from birds.models import Animal, Location, Plumage, Color, Status, Species, Pairing
from birds.forms import (
    NewBandForm,
    ReservationForm,
    SexForm,
    NewAnimalForm,
    NestCheckForm,
    NewPairingForm,
)

warnings.filterwarnings("error")


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


class NewPairingFormTest(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    @classmethod
    def setUpTestData(cls):
        birthday = datetime.date.today() - datetime.timedelta(days=365)
        cls.status = models.get_birth_event_type()
        cls.user = models.get_sentinel_user()
        cls.location = Location.objects.get(pk=2)
        cls.species = Species.objects.get(pk=1)
        cls.sire = Animal.objects.create_with_event(
            species=cls.species,
            status=cls.status,
            date=birthday,
            entered_by=cls.user,
            location=cls.location,
            sex=Animal.Sex.MALE,
            band_number=1,
        )
        cls.dam = Animal.objects.create_with_event(
            species=cls.species,
            status=cls.status,
            date=birthday,
            entered_by=cls.user,
            location=cls.location,
            sex=Animal.Sex.FEMALE,
        )

    def test_create_new_pairing(self):
        form = NewPairingForm(
            {
                "sire": self.sire,
                "dam": self.dam,
                "entered_by": self.user,
                "began": datetime.date.today(),
            }
        )
        self.assertTrue(form.is_valid())

    def test_wrong_sex(self):
        form = NewPairingForm(
            {
                "sire": self.dam,
                "dam": self.sire,
                "entered_by": self.user,
                "began": datetime.date.today(),
            }
        )
        self.assertFalse(form.is_valid())

    def test_not_alive(self):
        dead_sire = Animal.objects.create(species=self.species, sex=Animal.Sex.MALE)
        form = NewPairingForm(
            {
                "sire": dead_sire,
                "dam": self.dam,
                "entered_by": self.user,
                "began": datetime.date.today(),
            }
        )
        self.assertFalse(form.is_valid())
        dead_dam = Animal.objects.create(species=self.species, sex=Animal.Sex.FEMALE)
        form = NewPairingForm(
            {
                "sire": self.sire,
                "dam": dead_dam,
                "entered_by": self.user,
                "began": datetime.date.today(),
            }
        )
        self.assertFalse(form.is_valid())

    def test_not_adults(self):
        invalid_sire = Animal.objects.create_with_event(
            species=self.species,
            status=self.status,
            date=datetime.date.today() - datetime.timedelta(days=5),
            entered_by=self.user,
            location=self.location,
            sex=Animal.Sex.MALE,
            band_number=1,
        )
        form = NewPairingForm(
            {
                "sire": invalid_sire,
                "dam": self.dam,
                "entered_by": self.user,
                "began": datetime.date.today(),
            }
        )
        self.assertFalse(form.is_valid())
        invalid_dam = Animal.objects.create_with_event(
            species=self.species,
            status=self.status,
            date=datetime.date.today() - datetime.timedelta(days=5),
            entered_by=self.user,
            location=self.location,
            sex=Animal.Sex.FEMALE,
            band_number=1,
        )
        form = NewPairingForm(
            {
                "sire": self.sire,
                "dam": invalid_dam,
                "entered_by": self.user,
                "began": datetime.date.today(),
            }
        )
        self.assertFalse(form.is_valid())

    def test_in_active_pairing(self):
        _pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began=datetime.date.today() - datetime.timedelta(days=10),
        )
        form = NewPairingForm(
            {
                "sire": self.dam,
                "dam": self.sire,
                "entered_by": self.user,
                "began": datetime.date.today(),
            }
        )
        self.assertFalse(form.is_valid())

    def test_overlaps_pairing(self):
        _pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began=datetime.date.today() - datetime.timedelta(days=50),
            ended=datetime.date.today() - datetime.timedelta(days=5),
        )
        form = NewPairingForm(
            {
                "sire": self.dam,
                "dam": self.sire,
                "entered_by": self.user,
                "began": datetime.date.today() - datetime.timedelta(days=10),
            }
        )
        self.assertFalse(form.is_valid())


class NestCheckFormTest(TestCase):
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
        _ = Pairing.objects.create_with_events(
            sire=cls.sire,
            dam=cls.dam,
            began=datetime.date.today() - datetime.timedelta(days=1),
            purpose="testing",
            entered_by=user,
            location=cls.nest,
        )

    def test_nest_check_no_change(self):
        initial = {"location": self.nest, "eggs": 1, "chicks": 1}
        form = NestCheckForm(
            {"location": self.nest, "eggs": 1, "chicks": 1}, initial=initial
        )
        self.assertTrue(form.is_valid())
        self.assertDictEqual(
            form.cleaned_data, form.cleaned_data | {"delta_eggs": 0, "delta_chicks": 0}
        )

    def test_nest_check_add_egg(self):
        form = NestCheckForm({"location": self.nest, "eggs": 1, "chicks": 0})
        self.assertTrue(form.is_valid())
        self.assertDictEqual(
            form.cleaned_data, form.cleaned_data | {"delta_eggs": 1, "delta_chicks": 0}
        )

    def test_nest_check_hatch_egg(self):
        initial = {"location": self.nest, "eggs": 1, "chicks": 0}
        form = NestCheckForm(
            {"location": self.nest, "eggs": 0, "chicks": 1}, initial=initial
        )
        self.assertTrue(form.is_valid())
        # delta_eggs is only negative if the egg was lost
        self.assertDictEqual(
            form.cleaned_data, form.cleaned_data | {"delta_eggs": 0, "delta_chicks": 1}
        )

    def test_nest_check_lose_egg(self):
        initial = {"location": self.nest, "eggs": 1, "chicks": 0}
        form = NestCheckForm(
            {"location": self.nest, "eggs": 0, "chicks": 0}, initial=initial
        )
        self.assertTrue(form.is_valid())
        self.assertDictEqual(
            form.cleaned_data, form.cleaned_data | {"delta_eggs": -1, "delta_chicks": 0}
        )

    def test_nest_check_cannot_hatch_without_egg(self):
        initial = {"location": self.nest, "eggs": 1, "chicks": 0}
        form = NestCheckForm(
            {"location": self.nest, "eggs": 0, "chicks": 2}, initial=initial
        )
        self.assertFalse(form.is_valid())

    def test_nest_check_cannot_lose_chick(self):
        initial = {"location": self.nest, "eggs": 0, "chicks": 1}
        form = NestCheckForm(
            {"location": self.nest, "eggs": 0, "chicks": 0}, initial=initial
        )
        self.assertFalse(form.is_valid())

    def test_nest_check_cannot_add_egg_with_too_many_males(self):
        birthday = datetime.date.today() - datetime.timedelta(days=365)
        extra_male = Animal.objects.create_with_event(
            species=Species.objects.get(pk=1),
            status=models.get_birth_event_type(),
            date=birthday,
            entered_by=models.get_sentinel_user(),
            location=self.nest,
            sex=Animal.Sex.MALE,
        )
        form = NestCheckForm({"location": self.nest, "eggs": 1, "chicks": 0})
        self.assertFalse(form.is_valid())

    def test_nest_check_cannot_add_egg_without_a_male(self):
        _ = models.Event.objects.create(
            animal=self.sire,
            date=datetime.date.today(),
            status=Status.objects.get(name="moved"),
            location=Location.objects.get(pk=1),
            entered_by=models.get_sentinel_user(),
        )
        form = NestCheckForm({"location": self.nest, "eggs": 1, "chicks": 0})
        self.assertFalse(form.is_valid())

    def test_nest_check_cannot_add_egg_with_too_many_females(self):
        birthday = datetime.date.today() - datetime.timedelta(days=365)
        extra_male = Animal.objects.create_with_event(
            species=Species.objects.get(pk=1),
            status=models.get_birth_event_type(),
            date=birthday,
            entered_by=models.get_sentinel_user(),
            location=self.nest,
            sex=Animal.Sex.FEMALE,
        )
        form = NestCheckForm({"location": self.nest, "eggs": 1, "chicks": 0})
        self.assertFalse(form.is_valid())

    def test_nest_check_cannot_add_egg_without_a_female(self):
        _ = models.Event.objects.create(
            animal=self.dam,
            date=datetime.date.today(),
            status=Status.objects.get(name="moved"),
            location=Location.objects.get(pk=1),
            entered_by=models.get_sentinel_user(),
        )
        form = NestCheckForm({"location": self.nest, "eggs": 1, "chicks": 0})
        self.assertFalse(form.is_valid())

    def test_nest_check_formset(self):
        initial = [{"location": self.nest, "eggs": 0, "chicks": 1}]
        NestCheckFormSet = formset_factory(NestCheckForm, extra=0)
        formset = NestCheckFormSet(
            {
                "form-TOTAL_FORMS": 1,
                "form-INITIAL_FORMS": 1,
                "form-0-location": self.nest,
                "form-0-eggs": 1,
                "form-0-chicks": 1,
            },
            initial=initial,
        )
        self.assertTrue(formset.is_valid())
