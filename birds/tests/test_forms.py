# -*- mode: python -*-
import datetime
import importlib
import types
import warnings
from contextlib import contextmanager
from unittest import mock, skip

from django.forms import formset_factory
from django.test import TestCase

from birds import forms as birds_forms
from birds import models
from birds.forms import (
    BreedingCheckForm,
    NewAnimalForm,
    NewBandForm,
    NewPairingForm,
    SexForm,
    TagChangeForm,
)
from birds.models import (
    Animal,
    Color,
    Event,
    Location,
    Pairing,
    Plumage,
    Species,
    Status,
)

warnings.filterwarnings("error")


def today() -> datetime.date:
    return datetime.date.today()


def dt_days(days: int) -> datetime.timedelta:
    return datetime.timedelta(days=days)


@contextmanager
def forms_imported_on(day: datetime.date):
    """Reload birds.forms as if the server had been started on `day`"""

    class FakeDate(datetime.date):
        @classmethod
        def today(cls):
            return day

    fake = types.SimpleNamespace(
        **{k: v for k, v in vars(datetime).items() if not k.startswith("__")}
    )
    fake.date = FakeDate
    try:
        with mock.patch.object(models, "datetime", fake):
            module = importlib.reload(birds_forms)
        yield module
    finally:
        importlib.reload(birds_forms)


class SexFormTest(TestCase):
    def test_without_note_status(self):
        user = models.get_sentinel_user()
        form = SexForm({"date": today(), "sex": "M", "entered_by": user})
        self.assertFalse(form.is_valid())

    def test_with_note_status(self):
        _ = Status.objects.get_or_create(name=models.NOTE_EVENT_NAME)
        user = models.get_sentinel_user()
        form = SexForm({"date": today(), "sex": "M", "entered_by": user})
        self.assertTrue(form.is_valid())


class TagChangeFormTest(TestCase):
    def test_without_reservation_status(self):
        user = models.get_sentinel_user()
        form = TagChangeForm({"date": today(), "entered_by": user})
        self.assertFalse(form.is_valid())

    def test_with_reservation_status(self):
        _ = Status.objects.get_or_create(name=models.RESERVATION_EVENT_NAME)
        user = models.get_sentinel_user()
        form = TagChangeForm({"date": today(), "entered_by": user})
        self.assertTrue(form.is_valid())


class NewBandFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        species = Species.objects.create(
            common_name="eurasian magpie", genus="pica", species="pica", code="EUMA"
        )
        cls.plumage = Plumage.objects.create(name="standard")
        cls.color = Color.objects.create(name="blue", abbrv="bl", kind="available")
        cls.historical_color = Color.objects.create(
            name="old", abbrv="ol", kind=Color.BandType.HISTORICAL
        )
        cls.external_color = Color.objects.create(
            name="other", abbrv="ot", kind=Color.BandType.EXTERNAL
        )
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
                "banding_date": today(),
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
                "banding_date": today(),
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
                "banding_date": today(),
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
                "banding_date": today(),
                "band_color": self.color,
                "plumage": self.plumage,
                "location": self.location,
                "band_number": 40,
                "sex": "F",
                "user": user,
            }
        )
        self.assertTrue(form.is_valid())

    def test_band_color_options_exclude_historical_and_external(self):
        form = NewBandForm()
        self.assertCountEqual(form.fields["band_color"].queryset, [self.color])
        html = str(form["band_color"])
        self.assertIn(self.color.name, html)
        self.assertNotIn(self.historical_color.name, html)
        self.assertNotIn(self.external_color.name, html)

    def test_historical_and_external_band_colors_rejected(self):
        _ = Status.objects.get_or_create(name=models.BANDED_EVENT_NAME)
        user = models.get_sentinel_user()
        for color in (self.historical_color, self.external_color):
            with self.subTest(kind=color.kind):
                form = NewBandForm(
                    {
                        "banding_date": today(),
                        "band_color": color.pk,
                        "band_number": 10,
                        "sex": "M",
                        "user": user,
                    }
                )
                self.assertFalse(form.is_valid())
                self.assertIn("band_color", form.errors)


class NewAnimalFormTest(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    @classmethod
    def setUpTestData(cls):
        status = models.get_birth_event_type()
        birthday = today() - dt_days(365)
        cls.user = models.get_sentinel_user()
        cls.location = Location.objects.get(pk=2)
        cls.species = Species.objects.get(pk=1)
        cls.color = Color.objects.create(name="teal", abbrv="tl")
        cls.historical_color = Color.objects.create(
            name="old", abbrv="ol", kind=Color.BandType.HISTORICAL
        )
        cls.external_color = Color.objects.create(
            name="other", abbrv="ot", kind=Color.BandType.EXTERNAL
        )
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
        acq_on = today() - dt_days(10)
        acq_status = Status.objects.get(name="transferred in")
        form = NewAnimalForm(
            {
                "acq_status": acq_status,
                "acq_date": acq_on,
                "banding_date": today(),
                "sex": "M",
                "species": self.species,
                "band_number": 100,
                "location": self.location,
                "user": self.user,
            }
        )
        self.assertTrue(form.is_valid())

    def test_band_color_options_exclude_historical_and_external(self):
        form = NewAnimalForm()
        options = form.fields["band_color"].queryset
        self.assertIn(self.color, options)
        self.assertNotIn(self.historical_color, options)
        self.assertNotIn(self.external_color, options)
        html = str(form["band_color"])
        self.assertIn(self.color.name, html)
        self.assertNotIn(self.historical_color.name, html)
        self.assertNotIn(self.external_color.name, html)

    def test_default_band_color_kind_is_available(self):
        self.assertEqual(self.color.kind, Color.BandType.AVAILABLE)

    def test_historical_and_external_band_colors_rejected(self):
        acq_status = Status.objects.get(name="transferred in")
        for color in (self.historical_color, self.external_color):
            with self.subTest(kind=color.kind):
                form = NewAnimalForm(
                    {
                        "acq_status": acq_status,
                        "acq_date": today() - dt_days(10),
                        "banding_date": today(),
                        "sex": "M",
                        "species": self.species,
                        "band_color": color.pk,
                        "band_number": 100,
                        "location": self.location,
                        "user": self.user,
                    }
                )
                self.assertFalse(form.is_valid())
                self.assertIn("band_color", form.errors)

    def test_available_band_color_accepted(self):
        acq_status = Status.objects.get(name="transferred in")
        form = NewAnimalForm(
            {
                "acq_status": acq_status,
                "acq_date": today() - dt_days(10),
                "banding_date": today(),
                "sex": "M",
                "species": self.species,
                "band_color": self.color.pk,
                "band_number": 100,
                "location": self.location,
                "user": self.user,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_add_by_transfer_requires_species(self):
        acq_on = today() - dt_days(10)
        acq_status = Status.objects.get(name="transferred in")
        form = NewAnimalForm(
            {
                "acq_status": acq_status,
                "acq_date": acq_on,
                "banding_date": today(),
                "sex": "M",
                "band_number": 100,
                "location": self.location,
                "user": self.user,
            }
        )
        self.assertFalse(form.is_valid())

    def test_add_from_parents(self):
        acq_on = today() - dt_days(10)
        acq_status = models.get_birth_event_type()
        form = NewAnimalForm(
            {
                "acq_status": acq_status,
                "acq_date": acq_on,
                "banding_date": today(),
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
        acq_on = today() - dt_days(10)
        acq_status = models.get_birth_event_type()
        form = NewAnimalForm(
            {
                "acq_status": acq_status,
                "acq_date": acq_on,
                "banding_date": today(),
                "sex": "U",
                "sire": self.sire,
                "band_number": 100,
                "location": self.location,
                "user": self.user,
            }
        )
        self.assertFalse(form.is_valid())

    def test_add_from_mismatched_parent(self):
        acq_on = today() - dt_days(10)
        acq_status = models.get_birth_event_type()
        species = Species.objects.create(
            common_name="eurasian magpie", genus="pica", species="pica", code="EUMA"
        )
        wrong_dam = Animal.objects.create_with_event(
            species=species,
            status=acq_status,
            date=today() - dt_days(10),
            entered_by=self.user,
            location=self.location,
            sex=Animal.Sex.MALE,
        )
        form = NewAnimalForm(
            {
                "acq_status": acq_status,
                "acq_date": acq_on,
                "banding_date": today(),
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
        acq_on = today() - dt_days(10)
        acq_status = Status.objects.get(name="transferred in")
        form = NewAnimalForm(
            {
                "acq_status": acq_status,
                "acq_date": acq_on,
                "banding_date": today(),
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
        birthday = today() - dt_days(365)
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
                "began_on": today(),
            }
        )
        self.assertTrue(form.is_valid())

    def test_wrong_sex(self):
        form = NewPairingForm(
            {
                "sire": self.dam,
                "dam": self.sire,
                "entered_by": self.user,
                "began_on": today(),
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
                "began_on": today(),
            }
        )
        self.assertFalse(form.is_valid())
        dead_dam = Animal.objects.create(species=self.species, sex=Animal.Sex.FEMALE)
        form = NewPairingForm(
            {
                "sire": self.sire,
                "dam": dead_dam,
                "entered_by": self.user,
                "began_on": today(),
            }
        )
        self.assertFalse(form.is_valid())

    def test_not_adults(self):
        invalid_sire = Animal.objects.create_with_event(
            species=self.species,
            status=self.status,
            date=today() - dt_days(5),
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
                "began_on": today(),
            }
        )
        self.assertFalse(form.is_valid())
        invalid_dam = Animal.objects.create_with_event(
            species=self.species,
            status=self.status,
            date=today() - dt_days(5),
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
                "began_on": today(),
            }
        )
        self.assertFalse(form.is_valid())

    def test_in_active_pairing(self):
        _pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began_on=today() - dt_days(10),
        )
        form = NewPairingForm(
            {
                "sire": self.dam,
                "dam": self.sire,
                "entered_by": self.user,
                "began_on": today(),
            }
        )
        self.assertFalse(form.is_valid())

    def test_overlaps_pairing(self):
        _pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began_on=today() - dt_days(50),
            ended_on=today() - dt_days(5),
        )
        form = NewPairingForm(
            {
                "sire": self.dam,
                "dam": self.sire,
                "entered_by": self.user,
                "began_on": today() - dt_days(10),
            }
        )
        self.assertFalse(form.is_valid())


class BreedingCheckFormTest(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    @classmethod
    def setUpTestData(cls):
        birthday = today() - dt_days(365)
        status = models.get_birth_event_type()
        cls.user = models.get_sentinel_user()
        location = Location.objects.get(pk=1)
        species = Species.objects.get(pk=1)
        cls.sire = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=birthday,
            entered_by=cls.user,
            location=location,
            sex=Animal.Sex.MALE,
            band_number=1,
        )
        cls.dam = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=birthday,
            entered_by=cls.user,
            location=location,
            sex=Animal.Sex.FEMALE,
            band_number=2,
        )
        cls.nest = Location.objects.filter(nest=True).first()
        cls.pairing = Pairing.objects.create_with_events(
            sire=cls.sire,
            dam=cls.dam,
            began_on=today() - dt_days(10),
            purpose="testing",
            entered_by=cls.user,
            location=cls.nest,
        )

    def test_nest_check_no_change(self):
        _egg = self.pairing.create_egg(today() - dt_days(5), entered_by=self.user)
        child = self.pairing.create_egg(today() - dt_days(5), entered_by=self.user)
        _event = Event.objects.create(
            animal=child,
            date=today(),
            status=models.get_birth_event_type(),
            entered_by=self.user,
        )
        form = BreedingCheckForm(
            {"pairing": self.pairing, "location": self.nest, "eggs": 1, "chicks": 1},
        )
        self.assertTrue(form.is_valid())
        self.assertFalse(form.cleaned_data["hatched_eggs"].exists())
        self.assertCountEqual(form.cleaned_data["lost_eggs"], [])
        self.assertEqual(form.cleaned_data["added_eggs"], 0)
        self.assertCountEqual(form.change_summary(), ["no changes"])

    def test_nest_check_add_egg(self):
        form = BreedingCheckForm(
            {"pairing": self.pairing, "location": self.nest, "eggs": 1, "chicks": 0}
        )
        self.assertTrue(form.is_valid())
        self.assertFalse(form.cleaned_data["hatched_eggs"].exists())
        self.assertCountEqual(form.cleaned_data["lost_eggs"], [])
        self.assertEqual(form.cleaned_data["added_eggs"], 1)
        self.assertCountEqual(form.change_summary(), ["laid an egg"])

    def test_nest_check_hatch_egg(self):
        egg = self.pairing.create_egg(today() - dt_days(5), entered_by=self.user)
        form = BreedingCheckForm(
            {"pairing": self.pairing, "location": self.nest, "eggs": 0, "chicks": 1},
        )
        self.assertTrue(form.is_valid())
        self.assertCountEqual(form.cleaned_data["hatched_eggs"], [egg])
        self.assertCountEqual(form.cleaned_data["lost_eggs"], [])
        self.assertEqual(form.cleaned_data["added_eggs"], 0)
        self.assertCountEqual(form.change_summary(), [f"{egg} hatched"])

    def test_nest_check_hatch_egg_from_many(self):
        egg_1 = self.pairing.create_egg(today() - dt_days(5), entered_by=self.user)
        _egg_2 = self.pairing.create_egg(today() - dt_days(4), entered_by=self.user)
        _egg_3 = self.pairing.create_egg(today() - dt_days(3), entered_by=self.user)
        form = BreedingCheckForm(
            {"pairing": self.pairing, "location": self.nest, "eggs": 2, "chicks": 1},
        )
        self.assertTrue(form.is_valid())
        self.assertCountEqual(form.cleaned_data["hatched_eggs"], [egg_1])
        self.assertCountEqual(form.cleaned_data["lost_eggs"], [])
        self.assertEqual(form.cleaned_data["added_eggs"], 0)
        self.assertCountEqual(form.change_summary(), [f"{egg_1} hatched"])

    def test_nest_check_lose_egg(self):
        egg = self.pairing.create_egg(today() - dt_days(5), entered_by=self.user)
        form = BreedingCheckForm(
            {"pairing": self.pairing, "location": self.nest, "eggs": 0, "chicks": 0},
        )
        self.assertTrue(form.is_valid())
        self.assertFalse(form.cleaned_data["hatched_eggs"].exists())
        self.assertCountEqual(form.cleaned_data["lost_eggs"], [egg])
        self.assertEqual(form.cleaned_data["added_eggs"], 0)
        self.assertCountEqual(form.change_summary(), [f"{egg} lost"])

    def test_nest_check_hatch_egg_lose_egg(self):
        egg_1 = self.pairing.create_egg(today() - dt_days(5), entered_by=self.user)
        egg_2 = self.pairing.create_egg(today() - dt_days(4), entered_by=self.user)
        form = BreedingCheckForm(
            {"pairing": self.pairing, "location": self.nest, "eggs": 0, "chicks": 1},
        )
        self.assertTrue(form.is_valid())
        self.assertCountEqual(form.cleaned_data["hatched_eggs"], [egg_1])
        self.assertCountEqual(form.cleaned_data["lost_eggs"], [egg_2])
        self.assertEqual(form.cleaned_data["added_eggs"], 0)
        self.assertCountEqual(
            form.change_summary(), [f"{egg_1} hatched", f"{egg_2} lost"]
        )

    def test_nest_check_dead_chicks_not_counted(self):
        _egg = self.pairing.create_egg(today() - dt_days(5), entered_by=self.user)
        child = self.pairing.create_egg(today() - dt_days(5), entered_by=self.user)
        _event = Event.objects.create(
            animal=child,
            date=today() - dt_days(4),
            status=models.get_birth_event_type(),
            entered_by=self.user,
        )
        _event = Event.objects.create(
            animal=child,
            date=today(),
            status=models.get_death_event_type(),
            entered_by=self.user,
        )
        form = BreedingCheckForm(
            {"pairing": self.pairing, "location": self.nest, "eggs": 1, "chicks": 0},
        )
        self.assertTrue(form.is_valid(), "Dead chick was counted as alive")
        self.assertFalse(form.cleaned_data["hatched_eggs"].exists())
        self.assertCountEqual(form.cleaned_data["lost_eggs"], [])
        self.assertEqual(form.cleaned_data["added_eggs"], 0)

    def test_nest_check_lost_eggs_not_counted(self):
        egg = self.pairing.create_egg(today() - dt_days(5), entered_by=self.user)
        _event = Event.objects.create(
            animal=egg,
            date=today() - dt_days(2),
            status=Status.objects.get(name=models.BAD_EGG_EVENT_NAME),
            entered_by=self.user,
        )
        form = BreedingCheckForm(
            {"pairing": self.pairing, "location": self.nest, "eggs": 0, "chicks": 0},
        )
        self.assertTrue(form.is_valid())
        self.assertFalse(form.cleaned_data["hatched_eggs"].exists())
        self.assertCountEqual(form.cleaned_data["lost_eggs"], [])
        self.assertEqual(form.cleaned_data["added_eggs"], 0)

    def test_nest_check_cannot_hatch_without_egg(self):
        _egg = self.pairing.create_egg(today() - dt_days(5), entered_by=self.user)
        form = BreedingCheckForm({"pairing": self.pairing, "eggs": 0, "chicks": 2})
        self.assertFalse(form.is_valid())

    def test_nest_check_cannot_lose_chick(self):
        chick = self.pairing.create_egg(today() - dt_days(5), entered_by=self.user)
        _event = Event.objects.create(
            animal=chick,
            date=today(),
            status=models.get_birth_event_type(),
            entered_by=self.user,
        )
        form = BreedingCheckForm({"pairing": self.pairing, "eggs": 0, "chicks": 0})
        self.assertFalse(form.is_valid())

    def test_nest_check_formset(self):
        _egg = self.pairing.create_egg(today() - dt_days(5), entered_by=self.user)
        BreedingCheckFormSet = formset_factory(BreedingCheckForm, extra=0)
        formset = BreedingCheckFormSet(
            {
                "form-TOTAL_FORMS": 1,
                "form-INITIAL_FORMS": 1,
                "form-0-pairing": self.pairing,
                "form-0-location": self.nest,
                "form-0-eggs": 1,
                "form-0-chicks": 1,
            },
        )
        self.assertTrue(formset.is_valid())


class BreedingCheckNewPairingFormTest(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    @classmethod
    def setUpTestData(cls):
        birthday = today() - dt_days(365)
        status = models.get_birth_event_type()
        cls.user = models.get_sentinel_user()
        location = Location.objects.get(pk=1)
        species = Species.objects.get(pk=1)
        cls.sire = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=birthday,
            entered_by=cls.user,
            location=location,
            sex=Animal.Sex.MALE,
            band_number=1,
        )
        cls.dam = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=birthday,
            entered_by=cls.user,
            location=location,
            sex=Animal.Sex.FEMALE,
            band_number=2,
        )
        cls.nest = Location.objects.filter(nest=True).first()

    def test_nest_check_same_day(self):
        pairing = Pairing.objects.create_with_events(
            sire=self.sire,
            dam=self.dam,
            began_on=today(),
            purpose="testing",
            entered_by=self.user,
            location=self.nest,
        )
        form = BreedingCheckForm(
            {"pairing": pairing, "location": self.nest, "eggs": 0, "chicks": 0},
        )
        self.assertTrue(form.is_valid())
        self.assertFalse(form.cleaned_data["hatched_eggs"].exists())
        self.assertCountEqual(form.cleaned_data["lost_eggs"], [])
        self.assertEqual(form.cleaned_data["added_eggs"], 0)
        self.assertCountEqual(form.change_summary(), ["no changes"])

    @skip("no longer checked in validation")
    def test_nest_check_inactive_pair(self):
        pairing = Pairing.objects.create_with_events(
            sire=self.sire,
            dam=self.dam,
            began_on=today() - dt_days(10),
            purpose="testing",
            entered_by=self.user,
            location=self.nest,
        )
        pairing.close(ended_on=today(), entered_by=self.user)
        form = BreedingCheckForm(
            {"pairing": pairing, "location": self.nest, "eggs": 0, "chicks": 0},
        )
        self.assertFalse(form.is_valid())


class ParentChoicesDateTest(TestCase):
    """Parent choices have to be calculated when a form is created, not when the
    module is imported, or birds that arrive after a long-running server has
    started are not offered until the server is restarted (#97)"""

    fixtures = ["bird_colony_starter_kit"]

    @classmethod
    def setUpTestData(cls):
        arrival = today() - dt_days(5)
        status = models.get_birth_event_type()
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=2)
        species = Species.objects.get(pk=1)
        cls.sire = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=arrival,
            entered_by=user,
            location=location,
            sex=Animal.Sex.MALE,
            band_number=1,
        )
        cls.dam = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=arrival,
            entered_by=user,
            location=location,
            sex=Animal.Sex.FEMALE,
            band_number=2,
        )

    def check_choices(self, form_name):
        # the server was started before the birds arrived
        with forms_imported_on(today() - dt_days(10)) as module:
            form = getattr(module, form_name)()
            self.assertIn(self.sire, form.fields["sire"].queryset)
            self.assertIn(self.dam, form.fields["dam"].queryset)
            self.assertNotIn(self.dam, form.fields["sire"].queryset)

    def test_new_pairing_form_choices_follow_the_date(self):
        self.check_choices("NewPairingForm")

    def test_new_animal_form_choices_follow_the_date(self):
        self.check_choices("NewAnimalForm")
