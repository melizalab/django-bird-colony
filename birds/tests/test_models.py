# -*- coding: utf-8 -*-
# -*- mode: python -*-
import datetime

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase

from birds import models
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


def make_child(sire, dam, birthday=None, **kwargs):
    """Convenience function to make a child"""
    child = Animal.objects.create(species=sire.species, **kwargs)
    child.parents.set([sire, dam])
    if birthday is not None:
        status = models.get_birth_event_type()
        user = models.get_sentinel_user()
        Event.objects.create(
            animal=child, status=status, date=birthday, entered_by=user
        )
    return child


def today() -> datetime.date:
    return datetime.date.today()


def dt_days(days: int) -> datetime.timedelta:
    return datetime.timedelta(days=days)


class AnimalModelTests(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    def test_create_bird_with_event(self):
        species = Species.objects.get(pk=1)
        status = models.get_birth_event_type()
        age = datetime.timedelta(days=5)
        birthday = today() - age
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=2)
        bird = Animal.objects.create_with_event(
            species=species,
            date=birthday,
            status=status,
            entered_by=user,
            location=location,
            sex=Animal.Sex.MALE,
        )
        self.assertEqual(bird.age(), age)
        self.assertEqual(bird.sex, Animal.Sex.MALE)
        self.assertEqual(bird.event_set.count(), 1)
        event = bird.event_set.first()
        self.assertEqual(event.location, location)
        self.assertEqual(event.date, birthday)
        self.assertEqual(event.status, status)

    def test_name_of_banded_bird(self):
        band_number = 10
        species = Species.objects.get(pk=1)
        bird = Animal(species=species, band_number=band_number)
        self.assertEqual(bird.name, f"{species.code}_{band_number}")

    def test_name_of_color_banded_bird(self):
        band_number = 10
        species = Species.objects.get(pk=1)
        color = Color.objects.get(pk=1)
        bird = Animal(species=species, band_number=band_number, band_color=color)
        self.assertEqual(bird.name, f"{species.code}_{color.name}_{band_number}")

    def test_status_of_bird_without_events(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        self.assertIs(bird.acquisition_event(), None)
        self.assertIs(bird.age(), None)
        self.assertIs(bird.alive(), False)
        random_date = today() - datetime.timedelta(days=5)
        self.assertIs(bird.age(on_date=random_date), None)
        self.assertNotIn(bird, Animal.objects.alive())
        self.assertNotIn(bird, Animal.objects.hatched())
        self.assertIs(
            bird.expected_hatch(),
            None,
            "bird without events should not have expected hatch",
        )
        annotated_bird = Animal.objects.with_dates().get(pk=bird.pk)
        self.assertIs(annotated_bird.born_on, None)
        self.assertIs(annotated_bird.acquired_on, None)
        self.assertIs(annotated_bird.died_on, None)
        self.assertIs(annotated_bird.first_event_on, None)
        self.assertFalse(annotated_bird.alive)
        annotated_bird = Animal.objects.with_dates(random_date).get(pk=bird.pk)
        self.assertIs(annotated_bird.born_on, None)
        self.assertIs(annotated_bird.acquired_on, None)
        self.assertIs(annotated_bird.died_on, None)
        self.assertIs(annotated_bird.first_event_on, None)

    def test_status_of_hatched_bird(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        status = models.get_birth_event_type()
        age = dt_days(5)
        birthday = today() - age
        user = models.get_sentinel_user()

        event = Event.objects.create(
            animal=bird, status=status, date=birthday, entered_by=user
        )
        self.assertEqual(bird.acquisition_event(), event)
        self.assertEqual(bird.age(), age)
        self.assertEqual(bird.age(on_date=birthday), dt_days(0))
        self.assertIs(bird.age(on_date=birthday - dt_days(1)), None)

        self.assertIs(bird.alive(), True)
        self.assertIs(bird.alive(on_date=birthday), True)
        self.assertIs(bird.alive(on_date=birthday - dt_days(1)), False)
        self.assertIs(bird.expected_hatch(), None)

        annotated_bird = Animal.objects.with_dates().get(pk=bird.pk)
        self.assertEqual(annotated_bird.first_event_on, birthday)
        self.assertEqual(annotated_bird.born_on, birthday)
        self.assertEqual(annotated_bird.acquired_on, birthday)
        self.assertIs(annotated_bird.died_on, None)
        self.assertIs(annotated_bird.alive, True)
        self.assertEqual(annotated_bird.age, age)

        self.assertIn(bird, Animal.objects.alive())
        self.assertIn(bird, Animal.objects.hatched())
        self.assertNotIn(bird, Animal.objects.unhatched())
        self.assertIn(bird, Animal.objects.alive(birthday))
        self.assertNotIn(bird, Animal.objects.alive(birthday - dt_days(1)))
        self.assertIn(bird, Animal.objects.existing(birthday))
        self.assertNotIn(bird, Animal.objects.existing(birthday - dt_days(1)))

    def test_status_of_transferred_bird(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        status = Status.objects.get(name="transferred in")
        self.assertEqual(status.adds, 1)
        acq_on = today() - dt_days(10)
        user = models.get_sentinel_user()
        event = Event.objects.create(
            animal=bird, status=status, date=acq_on, entered_by=user
        )

        self.assertEqual(bird.acquisition_event(), event)
        self.assertIs(bird.age(), None)
        self.assertIs(bird.age(on_date=acq_on), None)
        self.assertIs(bird.alive(), True)
        self.assertIs(bird.alive(on_date=acq_on), True)
        self.assertIs(bird.alive(on_date=acq_on - dt_days(1)), False)
        self.assertIs(bird.expected_hatch(), None)

        annotated_bird = Animal.objects.with_dates().get(pk=bird.pk)
        self.assertEqual(annotated_bird.first_event_on, acq_on)
        self.assertIs(annotated_bird.born_on, None)
        self.assertEqual(annotated_bird.acquired_on, acq_on)
        self.assertIs(annotated_bird.died_on, None)
        self.assertIs(annotated_bird.age, None)
        self.assertIs(annotated_bird.alive, True)
        self.assertEqual(annotated_bird.age_group(), models.ADULT_ANIMAL_NAME)

        self.assertIn(bird, Animal.objects.alive())
        self.assertNotIn(bird, Animal.objects.hatched())
        self.assertIn(bird, Animal.objects.unhatched())
        self.assertIn(bird, Animal.objects.unhatched().alive())
        self.assertIn(bird, Animal.objects.alive(acq_on))
        self.assertNotIn(bird, Animal.objects.alive(acq_on - dt_days(1)))
        self.assertIn(bird, Animal.objects.existing(acq_on))
        self.assertNotIn(bird, Animal.objects.existing(acq_on - dt_days(1)))

    def test_status_of_dead_bird(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        user = models.get_sentinel_user()
        status_born = models.get_birth_event_type()
        self.assertEqual(status_born.adds, 1)
        born_on = today() - dt_days(10)
        event_born = Event.objects.create(
            animal=bird, status=status_born, date=born_on, entered_by=user
        )
        status_died = Status.objects.get(name="died")
        self.assertEqual(status_died.removes, 1)
        died_on = today() - dt_days(1)
        Event.objects.create(
            animal=bird, status=status_died, date=died_on, entered_by=user
        )

        self.assertEqual(bird.acquisition_event(), event_born)
        self.assertIs(bird.alive(), False)
        self.assertIs(bird.alive(on_date=died_on - dt_days(1)), True)
        self.assertIs(bird.alive(on_date=born_on - dt_days(1)), False)

        self.assertEqual(bird.age(), died_on - born_on)
        self.assertEqual(bird.age(on_date=died_on), died_on - born_on)
        self.assertIs(bird.expected_hatch(), None)

        annotated_bird = Animal.objects.with_dates().get(pk=bird.pk)
        self.assertEqual(annotated_bird.first_event_on, born_on)
        self.assertEqual(annotated_bird.born_on, born_on)
        self.assertEqual(annotated_bird.acquired_on, born_on)
        self.assertEqual(annotated_bird.died_on, died_on)
        self.assertIs(annotated_bird.alive, False)
        self.assertEqual(annotated_bird.age, died_on - born_on)

        self.assertNotIn(bird, Animal.objects.alive())
        self.assertIn(bird, Animal.objects.hatched())
        self.assertNotIn(bird, Animal.objects.unhatched())
        self.assertIn(bird, Animal.objects.alive(born_on))
        self.assertIn(bird, Animal.objects.alive(died_on - dt_days(1)))
        self.assertNotIn(bird, Animal.objects.alive(born_on - dt_days(1)))
        self.assertIn(bird, Animal.objects.existing(born_on))
        self.assertIn(bird, Animal.objects.existing(died_on - dt_days(1)))
        self.assertNotIn(bird, Animal.objects.existing(born_on - dt_days(1)))

    def test_bird_hatched_alive_order(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        user = models.get_sentinel_user()
        status_born = models.get_birth_event_type()
        self.assertEqual(status_born.adds, 1)
        born_on = today() - dt_days(10)
        Event.objects.create(
            animal=bird, status=status_born, date=born_on, entered_by=user
        )
        # it should not matter what order these are called in
        self.assertIn(bird, Animal.objects.alive().hatched())
        self.assertIn(bird, Animal.objects.hatched().alive())
        self.assertNotIn(bird, Animal.objects.unhatched().alive())
        self.assertNotIn(bird, Animal.objects.alive().unhatched())
        self.assertIs(
            bird.expected_hatch(), None, "hatched bird should not have expected hatch"
        )

        status_died = Status.objects.get(name="died")
        self.assertEqual(status_died.removes, 1)
        died_on = today() - dt_days(1)
        Event.objects.create(
            animal=bird, status=status_died, date=died_on, entered_by=user
        )
        self.assertNotIn(bird, Animal.objects.hatched().alive())
        self.assertNotIn(bird, Animal.objects.alive().hatched())
        self.assertNotIn(bird, Animal.objects.unhatched().alive())
        self.assertNotIn(bird, Animal.objects.alive().unhatched())

    def test_status_of_egg(self):
        species = Species.objects.get(pk=1)
        egg = Animal.objects.create(species=species)
        user = models.get_sentinel_user()
        status_laid = models.get_unborn_creation_event_type()
        self.assertEqual(status_laid.adds, 0)
        laid_on = today() - dt_days(10)
        Event.objects.create(
            animal=egg, status=status_laid, date=laid_on, entered_by=user
        )

        self.assertIs(egg.acquisition_event(), None)
        self.assertIs(egg.alive(), False)
        self.assertIs(egg.age(), None)
        eggspected_hatch = laid_on + datetime.timedelta(days=species.incubation_days)
        self.assertEqual(egg.expected_hatch(), eggspected_hatch)

        annotated_egg = Animal.objects.with_dates().get(pk=egg.pk)
        self.assertEqual(annotated_egg.first_event_on, laid_on)
        self.assertIs(annotated_egg.born_on, None)
        self.assertIs(annotated_egg.acquired_on, None)
        self.assertIs(annotated_egg.died_on, None)
        self.assertIs(annotated_egg.age, None)
        self.assertIs(annotated_egg.alive, False, "an egg is not alive")
        self.assertEqual(annotated_egg.age_group(), models.UNBORN_ANIMAL_NAME)

        self.assertNotIn(egg, Animal.objects.alive())
        self.assertNotIn(egg, Animal.objects.hatched())
        self.assertIn(egg, Animal.objects.unhatched())
        self.assertIn(egg, Animal.objects.existing(laid_on))
        self.assertNotIn(egg, Animal.objects.existing(laid_on - dt_days(1)))

    def test_status_of_lost_egg(self):
        species = Species.objects.get(pk=1)
        egg = Animal.objects.create(species=species)
        user = models.get_sentinel_user()
        status_laid = models.get_unborn_creation_event_type()
        status_lost = Status.objects.get(name=models.LOST_EVENT_NAME)
        laid_on = today() - dt_days(10)
        Event.objects.create(
            animal=egg, status=status_laid, date=laid_on, entered_by=user
        )
        lost_on = today() - dt_days(2)
        Event.objects.create(
            animal=egg, status=status_lost, date=lost_on, entered_by=user
        )

        self.assertIs(egg.acquisition_event(), None)
        self.assertIs(egg.alive(), False)
        self.assertIs(egg.age(), None)
        self.assertIs(
            egg.expected_hatch(), None, "lost egg should not have expected hatch"
        )

        annotated_egg = Animal.objects.with_dates().get(pk=egg.pk)
        self.assertEqual(annotated_egg.first_event_on, laid_on)
        self.assertIs(annotated_egg.born_on, None)
        self.assertIs(annotated_egg.acquired_on, None)
        self.assertEqual(annotated_egg.died_on, lost_on)
        self.assertIs(annotated_egg.age, None)
        self.assertIs(annotated_egg.alive, False, "an egg is not alive")
        self.assertEqual(annotated_egg.age_group(), models.UNBORN_ANIMAL_NAME)

        self.assertNotIn(egg, Animal.objects.alive())
        self.assertNotIn(egg, Animal.objects.hatched())
        self.assertIn(egg, Animal.objects.unhatched())
        self.assertNotIn(egg, Animal.objects.unhatched().existing())
        self.assertIn(egg, Animal.objects.existing(laid_on))
        self.assertNotIn(egg, Animal.objects.existing(laid_on - dt_days(1)))
        self.assertNotIn(egg, Animal.objects.existing(lost_on))

    def test_with_dates_as_of_date(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        models.get_birth_event_type()
        age = dt_days(5)
        birthday = today() - age
        user = models.get_sentinel_user()
        laid_on = today() - dt_days(10)
        Event.objects.create(
            animal=bird,
            status=models.get_unborn_creation_event_type(),
            date=laid_on,
            entered_by=user,
        )
        Event.objects.create(
            animal=bird,
            status=models.get_birth_event_type(),
            date=birthday,
            entered_by=user,
        )
        Event.objects.create(
            animal=bird,
            status=models.get_death_event_type(),
            date=today(),
            entered_by=user,
        )
        annotated_bird = Animal.objects.with_dates().get(pk=bird.pk)
        self.assertEqual(annotated_bird.first_event_on, laid_on)
        self.assertEqual(annotated_bird.born_on, birthday)
        self.assertEqual(annotated_bird.acquired_on, birthday)
        self.assertEqual(annotated_bird.died_on, today())
        self.assertEqual(annotated_bird.age, age)

        annotated_bird = Animal.objects.with_dates(birthday).get(pk=bird.pk)
        self.assertEqual(annotated_bird.first_event_on, laid_on)
        self.assertEqual(annotated_bird.born_on, birthday)
        self.assertEqual(annotated_bird.acquired_on, birthday)
        self.assertIs(annotated_bird.died_on, None)
        self.assertEqual(annotated_bird.age, dt_days(0))

        annotated_bird = Animal.objects.with_dates(birthday - dt_days(1)).get(
            pk=bird.pk
        )
        self.assertEqual(annotated_bird.first_event_on, laid_on)
        self.assertIs(annotated_bird.born_on, None)
        self.assertIs(annotated_bird.acquired_on, None)
        self.assertIs(annotated_bird.died_on, None)
        self.assertIs(annotated_bird.age, None)

        annotated_bird = Animal.objects.with_dates(laid_on - dt_days(1)).get(pk=bird.pk)
        self.assertIs(annotated_bird.first_event_on, None)
        self.assertIs(annotated_bird.born_on, None)
        self.assertIs(annotated_bird.acquired_on, None)
        self.assertIs(annotated_bird.died_on, None)
        self.assertIs(annotated_bird.age, None)

    def test_age_grouping(self):
        species = Species.objects.get(pk=1)
        status = models.get_birth_event_type()
        user = models.get_sentinel_user()
        youngest_group = species.age_set.get(min_days=0)
        for age_group in species.age_set.all():
            bird = Animal.objects.create(species=species)
            birthday = today() - datetime.timedelta(days=age_group.min_days)
            Event.objects.create(
                animal=bird, status=status, date=birthday, entered_by=user
            )
            abird = Animal.objects.with_dates().get(pk=bird.pk)
            self.assertEqual(abird.age_group(), age_group.name)
            abird = Animal.objects.with_dates().get(pk=bird.pk)
            self.assertEqual(abird.age_group(birthday), youngest_group.name)
            abird = Animal.objects.with_dates().get(pk=bird.pk)
            self.assertIs(abird.age_group(birthday - dt_days(1)), None)

    def test_age_grouping_of_egg(self):
        species = Species.objects.get(pk=1)
        status = models.get_unborn_creation_event_type()
        user = models.get_sentinel_user()
        laid_on = today() - dt_days(7)
        egg = Animal.objects.create(species=species)
        _event = Event.objects.create(
            animal=egg, status=status, date=laid_on, entered_by=user
        )
        aegg = Animal.objects.with_dates().get(pk=egg.pk)
        self.assertEqual(aegg.age_group(), models.UNBORN_ANIMAL_NAME)
        aegg = Animal.objects.with_dates().get(pk=egg.pk)
        self.assertEqual(aegg.age_group(laid_on), models.UNBORN_ANIMAL_NAME)
        aegg = Animal.objects.with_dates().get(pk=egg.pk)
        self.assertIs(aegg.age_group(laid_on - dt_days(1)), None)
        # Adding a hatch event
        _event = Event.objects.create(
            animal=egg,
            status=models.get_birth_event_type(),
            date=today(),
            entered_by=user,
        )
        aegg = Animal.objects.with_dates().get(pk=egg.pk)
        self.assertEqual(aegg.age_group(), "hatchling")
        aegg = Animal.objects.with_dates().get(pk=egg.pk)
        self.assertEqual(aegg.age_group(laid_on), models.UNBORN_ANIMAL_NAME)
        aegg = Animal.objects.with_dates().get(pk=egg.pk)
        self.assertEqual(
            aegg.age_group(today() - dt_days(1)),
            models.UNBORN_ANIMAL_NAME,
        )

    def test_bird_locations(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        self.assertIs(bird.last_location(), None)
        user = models.get_sentinel_user()
        status_1 = models.get_birth_event_type()
        birthday = today() - dt_days(10)
        location_1 = Location.objects.get(pk=2)
        Event.objects.create(
            animal=bird,
            status=status_1,
            date=birthday,
            entered_by=user,
            location=location_1,
        )
        self.assertEqual(bird.last_location(), location_1)
        abird = Animal.objects.with_location().get(pk=bird.pk)
        self.assertEqual(abird.last_location, location_1.name)

        status_2 = Status.objects.get(name="moved")
        date_2 = today() - dt_days(1)
        location_2 = Location.objects.get(pk=1)
        Event.objects.create(
            animal=bird,
            status=status_2,
            date=date_2,
            entered_by=user,
            location=location_2,
        )
        self.assertIs(bird.alive(), True)
        self.assertEqual(bird.last_location(), location_2)
        abird = Animal.objects.with_location().get(pk=bird.pk)
        self.assertEqual(abird.last_location, location_2.name)
        self.assertEqual(bird.last_location(on_date=birthday), location_1)
        abird = Animal.objects.with_location(on_date=birthday).get(pk=bird.pk)
        self.assertEqual(abird.last_location, location_1.name)
        self.assertIs(bird.last_location(on_date=birthday - dt_days(1)), None)
        abird = Animal.objects.with_location(on_date=birthday - dt_days(1)).get(
            pk=bird.pk
        )
        self.assertIs(abird.last_location, None)

    def test_updating_sex(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        self.assertFalse(bird.sexed())
        self.assertEqual(bird.sex, Animal.Sex.UNKNOWN_SEX)

        user = models.get_sentinel_user()
        date = today()
        event = bird.update_sex(Animal.Sex.FEMALE, date=date, entered_by=user)
        # force refresh from database
        bird = Animal.objects.get(pk=bird.pk)
        self.assertTrue(bird.sexed())
        self.assertEqual(bird.sex, Animal.Sex.FEMALE)
        self.assertIn(event, bird.event_set.all())

    def test_updating_band(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        self.assertEqual(bird.sex, Animal.Sex.UNKNOWN_SEX)
        self.assertIs(bird.band_number, None)
        self.assertIs(bird.band_color, None)
        self.assertIs(bird.plumage, None)
        user = models.get_sentinel_user()
        color = Color.objects.get(pk=1)
        event = bird.update_band(
            band_number=100,
            band_color=color,
            date=today(),
            entered_by=user,
        )
        # force refresh from database
        bird = Animal.objects.get(pk=bird.pk)
        self.assertFalse(bird.sexed())
        self.assertEqual(bird.band_number, 100)
        self.assertEqual(bird.band_color, color)
        self.assertIs(bird.plumage, None)
        self.assertIs(event.location, None)
        self.assertIn(event, bird.event_set.all())

    def test_updating_band_does_not_clear_properties(self):
        species = Species.objects.get(pk=1)
        plumage = Plumage.objects.get(pk=1)
        bird = Animal.objects.create(
            species=species, sex=Animal.Sex.MALE, plumage=plumage
        )
        user = models.get_sentinel_user()
        color = Color.objects.get(pk=1)
        bird.update_band(
            band_number=100,
            band_color=color,
            date=today(),
            entered_by=user,
        )
        # force refresh from database
        bird = Animal.objects.get(pk=bird.pk)
        self.assertEqual(bird.sex, Animal.Sex.MALE)
        self.assertEqual(bird.band_number, 100)
        self.assertEqual(bird.band_color, color)
        self.assertEqual(bird.plumage, plumage)


class ParentModelTests(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    def test_bird_parents(self):
        species = Species.objects.get(pk=1)
        sire = Animal.objects.create(species=species, sex=Animal.Sex.MALE)
        dam = Animal.objects.create(species=species, sex=Animal.Sex.FEMALE)
        child = make_child(sire, dam)
        self.assertEqual(child.sire(), sire)
        self.assertEqual(child.dam(), dam)
        self.assertTrue(sire.children.contains(child))
        self.assertTrue(dam.children.contains(child))
        self.assertEqual(
            sire.children.unhatched().count(),
            0,
            "a bird with no events should not be in the unhatched group",
        )
        self.assertEqual(
            sire.children.hatched().count(),
            0,
            "a bird with no events should not be in the hatched group",
        )
        self.assertEqual(
            sire.children.alive().count(),
            0,
            "a bird with no events should not be in the alive group",
        )

    def test_create_bird_from_parents(self):
        species = Species.objects.get(pk=1)
        sire = Animal.objects.create(species=species, sex=Animal.Sex.MALE)
        dam = Animal.objects.create(species=species, sex=Animal.Sex.FEMALE)
        status = models.get_birth_event_type()
        age = dt_days(5)
        birthday = today() - age
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=2)
        bird = Animal.objects.create_from_parents(
            sire=sire,
            dam=dam,
            date=birthday,
            status=status,
            entered_by=user,
            location=location,
            description="testing 123",
            sex=Animal.Sex.FEMALE,
        )
        self.assertEqual(bird.age(), age)
        self.assertEqual(bird.sex, Animal.Sex.FEMALE)
        self.assertEqual(bird.event_set.count(), 1)
        event = bird.event_set.first()
        self.assertEqual(event.location, location)
        self.assertEqual(event.date, birthday)
        self.assertEqual(event.status, status)
        self.assertEqual(bird.sire(), sire)
        self.assertEqual(bird.dam(), dam)
        self.assertTrue(sire.children.contains(bird))
        self.assertTrue(dam.children.contains(bird))

    def test_bird_child_counts(self):
        species = Species.objects.get(pk=1)
        sire = Animal.objects.create(species=species, sex=Animal.Sex.MALE)
        dam = Animal.objects.create(species=species, sex=Animal.Sex.FEMALE)
        age = dt_days(5)
        birthday = today() - age
        make_child(sire, dam, birthday)
        self.assertEqual(sire.children.unhatched().count(), 0)
        self.assertEqual(sire.children.hatched().count(), 1)
        self.assertEqual(sire.children.alive().count(), 1)

    def test_genealogy(self):
        species = Species.objects.get(pk=1)
        born_status = models.get_birth_event_type()
        died_status = models.get_death_event_type()
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=2)

        birthday = today() - dt_days(365)
        sire = Animal.objects.create_with_event(
            species=species,
            date=birthday,
            entered_by=user,
            location=location,
            status=born_status,
            sex=Animal.Sex.MALE,
        )
        dam = Animal.objects.create_with_event(
            species=species,
            date=birthday,
            entered_by=user,
            location=location,
            status=born_status,
            sex=Animal.Sex.FEMALE,
        )
        # add death event for dam to check that alive status is correct
        Event.objects.create(
            animal=dam,
            date=today() - dt_days(5),
            entered_by=user,
            status=died_status,
        )
        son = Animal.objects.create_from_parents(
            sire=sire,
            dam=dam,
            date=today() - dt_days(100),
            status=born_status,
            entered_by=user,
            location=location,
            sex=Animal.Sex.MALE,
        )
        wife = Animal.objects.create_with_event(
            species=species,
            date=today() - dt_days(99),
            location=location,
            status=born_status,
            entered_by=user,
            sex=Animal.Sex.FEMALE,
        )
        grandson = make_child(
            son,
            wife,
            today() - dt_days(50),
            sex=Animal.Sex.MALE,
        )
        granddaughter_1 = make_child(
            son,
            wife,
            today() - dt_days(50),
            sex=Animal.Sex.FEMALE,
        )
        granddaughter_2 = make_child(
            son,
            wife,
            today() - dt_days(45),
            sex=Animal.Sex.FEMALE,
        )
        # add death event to check that alive status of descendents is correct
        Event.objects.create(
            animal=granddaughter_2,
            date=today() - dt_days(1),
            entered_by=user,
            status=died_status,
        )
        children = Animal.objects.descendents_of(sire, generation=1)
        self.assertCountEqual(children, [son])
        grandchildren = Animal.objects.descendents_of(sire, generation=2)
        self.assertCountEqual(
            grandchildren, [grandson, granddaughter_1, granddaughter_2]
        )
        self.assertCountEqual(
            grandchildren.hatched(), [grandson, granddaughter_1, granddaughter_2]
        )
        self.assertCountEqual(
            grandchildren.hatched().alive(), [grandson, granddaughter_1]
        )
        self.assertCountEqual(grandchildren.alive(), [grandson, granddaughter_1])
        self.assertCountEqual(
            Animal.objects.ancestors_of(son, generation=1), [sire, dam]
        )
        self.assertCountEqual(
            Animal.objects.descendents_of(son, generation=1),
            [grandson, granddaughter_1, granddaughter_2],
        )
        parents = Animal.objects.ancestors_of(grandson, generation=1)
        self.assertCountEqual(parents, [son, wife])
        grandparents = Animal.objects.ancestors_of(grandson, generation=2)
        self.assertCountEqual(grandparents, [sire, dam])
        self.assertCountEqual(grandparents.alive(), [sire])


class EventModelTests(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    def test_age_at_event_time(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        status = models.get_birth_event_type()
        age = dt_days(5)
        birthday = today() - age
        user = models.get_sentinel_user()
        event = Event.objects.create(
            animal=bird, status=status, date=birthday, entered_by=user
        )
        self.assertEqual(event.age(), dt_days(0))
        status_2 = Status.objects.get(name="moved")
        date_2 = today() - dt_days(1)
        event_2 = Event(
            animal=bird,
            status=status_2,
            date=date_2,
            entered_by=user,
        )
        self.assertEqual(event_2.age(), date_2 - birthday)

    def test_age_at_event_time_for_unhatched_bird(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        user = models.get_sentinel_user()
        status_2 = Status.objects.get(name="moved")
        date_2 = today() - dt_days(1)
        event_2 = Event(
            animal=bird,
            status=status_2,
            date=date_2,
            entered_by=user,
        )
        self.assertEqual(event_2.age(), None)

    def test_most_recent_event(self):
        species = Species.objects.get(pk=1)
        bird_1 = Animal.objects.create(species=species)
        # add two events to each bird
        user = models.get_sentinel_user()
        status = Status.objects.get(name="moved")
        event_1_1 = Event.objects.create(
            animal=bird_1,
            status=status,
            date=today() - dt_days(1),
            entered_by=user,
        )
        Event.objects.create(
            animal=bird_1,
            status=status,
            date=today() - dt_days(10),
            entered_by=user,
        )

        bird_2 = Animal.objects.create(species=species)
        Event.objects.create(
            animal=bird_2,
            status=status,
            date=today() - dt_days(50),
            entered_by=user,
        )

        event_2_2 = Event.objects.create(
            animal=bird_2,
            status=status,
            date=today() - dt_days(25),
            entered_by=user,
        )

        latest_events = Event.objects.latest_by_animal()
        self.assertCountEqual(latest_events, [event_1_1, event_2_2])

    def test_this_month_filter(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        status = models.get_birth_event_type()
        user = models.get_sentinel_user()
        event = Event.objects.create(
            animal=bird, status=status, date=today(), entered_by=user
        )
        self.assertCountEqual(Event.objects.in_month(), [event])

    def test_specific_month_filter(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        status = Status.objects.get(name="note")
        user = models.get_sentinel_user()
        month = datetime.date(2024, 4, 1)
        Event.objects.create(
            animal=bird, status=status, date=datetime.date(2024, 3, 1), entered_by=user
        )
        event_2 = Event.objects.create(
            animal=bird, status=status, date=month, entered_by=user
        )
        Event.objects.create(
            animal=bird, status=status, date=datetime.date(2024, 5, 1), entered_by=user
        )
        self.assertCountEqual(Event.objects.in_month(month), [event_2])

    def test_event_counts(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        user = models.get_sentinel_user()
        status_1 = Status.objects.get(name="note")
        _event = Event.objects.create(
            animal=bird, status=status_1, date=today(), entered_by=user
        )
        _event = Event.objects.create(
            animal=bird, status=status_1, date=today(), entered_by=user
        )
        status_2 = Status.objects.get(name="moved")
        _event = Event.objects.create(
            animal=bird, status=status_2, date=today(), entered_by=user
        )
        counts = {
            item["status__name"]: item["count"]
            for item in Event.objects.in_month().count_by_status()
        }
        self.assertEqual(counts, {"note": 2, "moved": 1})


class PairingModelTests(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    @classmethod
    def setUpTestData(cls):
        species = Species.objects.get(pk=1)
        cls.sire = Animal.objects.create(species=species, sex=Animal.Sex.MALE)
        cls.dam = Animal.objects.create(species=species, sex=Animal.Sex.FEMALE)

    def test_create_pairing_with_events(self):
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=1)
        date = today()
        pairing = Pairing.objects.create_with_events(
            sire=self.sire,
            dam=self.dam,
            began_on=date,
            purpose="testing",
            entered_by=user,
            location=location,
        )
        self.assertTrue(pairing.active())
        sire_events = self.sire.event_set.all()
        self.assertEqual(sire_events.count(), 1)
        self.assertEqual(sire_events.first().date, date)
        dam_events = self.dam.event_set.all()
        self.assertEqual(dam_events.count(), 1)
        self.assertEqual(dam_events.first().date, date)

    def test_create_pairing_with_invalid_sexes(self):
        pairing = Pairing(
            sire=self.dam,
            dam=self.sire,
            began_on=today(),
        )
        with self.assertRaises(ValidationError):
            pairing.full_clean()

    def test_create_pairing_with_invalid_dates(self):
        with self.assertRaises(IntegrityError):
            Pairing.objects.create(
                sire=self.sire,
                dam=self.dam,
                began_on=today(),
                ended_on=today() - dt_days(5),
            )

    def test_pairing_active_on_date(self):
        # the date logic for whether a pair is active is a little different from
        # some of the other statuses.
        pairing_began_on = today() - dt_days(10)
        pairing_ended_on = today() - dt_days(2)
        pairing = Pairing.objects.create(
            sire=self.sire, dam=self.dam, began_on=pairing_began_on
        )
        self.assertFalse(
            pairing.active(on_date=pairing_began_on - dt_days(1)),
            "unclosed pairing is inactive before it began",
        )
        self.assertNotIn(
            pairing,
            Pairing.objects.active(on_date=pairing_began_on - dt_days(1)),
            "unclosed pairing is inactive before it began",
        )
        self.assertTrue(
            pairing.active(on_date=pairing_began_on),
            "unclosed pairing is active on the day it began",
        )
        self.assertIn(
            pairing,
            Pairing.objects.active(on_date=pairing_began_on),
            "unclosed pairing is active on the day it began",
        )
        self.assertTrue(
            pairing.active(on_date=pairing_ended_on),
            "unclosed pairing is active after it began",
        )
        self.assertIn(
            pairing,
            Pairing.objects.active(on_date=pairing_began_on),
            "unclosed pairing is active after it began",
        )
        pairing.ended_on = pairing_ended_on
        pairing.save()
        self.assertFalse(
            pairing.active(on_date=pairing_began_on - dt_days(1)),
            "closed pairing is inactive before it began",
        )
        self.assertNotIn(
            pairing,
            Pairing.objects.active(on_date=pairing_began_on - dt_days(1)),
            "closed pairing is inactive before it began",
        )
        self.assertTrue(
            pairing.active(on_date=pairing_began_on),
            "closed pairing is active on the day it began",
        )
        self.assertIn(
            pairing,
            Pairing.objects.active(on_date=pairing_began_on),
            "closed pairing is active on the day it began",
        )
        self.assertFalse(
            pairing.active(on_date=pairing_ended_on),
            "closed pairing is inactive on the day it ended",
        )
        self.assertNotIn(
            pairing,
            Pairing.objects.active(on_date=pairing_ended_on),
            "closed pairing is inactive on the day it ended",
        )
        self.assertFalse(
            pairing.active(),
            "closed pairing is inactive after it ended",
        )
        self.assertNotIn(
            pairing,
            Pairing.objects.active(),
            "closed pairing is inactive after it ended",
        )

    def test_pairing_active_between_dates(self):
        pairing_began_on = today() - dt_days(10)
        pairing_ended_on = today() - dt_days(2)
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began_on=pairing_began_on,
            ended_on=pairing_ended_on,
        )
        active_before = Pairing.objects.active_between(
            pairing_began_on - dt_days(10),
            pairing_began_on - dt_days(1),
        )
        self.assertEqual(
            active_before.count(),
            0,
            "pairing should not be active in a window before the pairing began",
        )
        active_around_start = Pairing.objects.active_between(
            pairing_began_on - dt_days(2),
            pairing_began_on + dt_days(2),
        )
        self.assertIn(
            pairing,
            active_around_start,
            "pairing should be active in a window that includes began_on",
        )
        active_within_pairing = Pairing.objects.active_between(
            pairing_began_on + dt_days(2),
            pairing_ended_on - dt_days(2),
        )
        self.assertIn(
            pairing,
            active_within_pairing,
            "pairing should be active in a window between began_on and ended_on",
        )
        active_around_end = Pairing.objects.active_between(
            pairing_ended_on - dt_days(2),
            pairing_ended_on + dt_days(2),
        )
        self.assertIn(
            pairing,
            active_around_end,
            "pairing should be active in a window between began_on and ended_on",
        )
        active_after_end = Pairing.objects.active_between(
            pairing_ended_on + dt_days(2),
            pairing_ended_on + dt_days(4),
        )
        self.assertEqual(
            active_after_end.count(),
            0,
            "pairing should be not be active in a window after ended_on",
        )

    def test_bird_pairing_lists(self):
        pairing_1 = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began_on=today() - dt_days(100),
            ended_on=today() - dt_days(70),
        )
        other_bird = Animal.objects.create(
            species=Species.objects.get(pk=1), sex=Animal.Sex.FEMALE
        )
        pairing_2 = Pairing.objects.create(
            sire=self.sire,
            dam=other_bird,
            began_on=today() - dt_days(50),
            ended_on=today() - dt_days(20),
        )
        pairing_3 = Pairing.objects.create(
            sire=self.sire, dam=self.dam, began_on=today()
        )
        self.assertFalse(pairing_1.active())
        self.assertFalse(pairing_2.active())
        self.assertTrue(pairing_3.active())
        self.assertCountEqual(self.sire.pairings(), [pairing_1, pairing_2, pairing_3])
        self.assertCountEqual(self.dam.pairings(), [pairing_1, pairing_3])
        self.assertCountEqual(pairing_1.other_pairings(), [pairing_3])
        self.assertEqual(pairing_2.other_pairings().count(), 0)
        self.assertCountEqual(pairing_3.other_pairings(), [pairing_1])

    def test_pairing_egg_list(self):
        pairing_began_on = today() - dt_days(10)
        pairing_ended_on = today()
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began_on=pairing_began_on,
            ended_on=pairing_ended_on,
        )
        self.assertEqual(pairing.eggs().count(), 0)
        user = models.get_sentinel_user()
        status_laid = models.get_unborn_creation_event_type()

        egg = Animal.objects.create(species=self.sire.species)
        egg.parents.set([self.sire, self.dam])
        laid_on = pairing_began_on - dt_days(1)
        Event.objects.create(
            animal=egg, status=status_laid, date=laid_on, entered_by=user
        )
        self.assertEqual(
            pairing.eggs().count(),
            0,
            "egg laid before pairing is incorrectly associated with the pairing",
        )

        laid_on = pairing_ended_on - dt_days(4)
        egg = pairing.create_egg(date=laid_on, entered_by=user)
        self.assertCountEqual(
            pairing.eggs(),
            [egg],
            "egg laid during the pairing is not associated with it",
        )
        self.assertNotIn(
            egg,
            pairing.eggs().existing(pairing_ended_on - dt_days(5)),
            "egg laid in pairing does not exist before it was created",
        )
        self.assertIn(
            egg,
            pairing.eggs().existing(pairing_ended_on - dt_days(3)),
            "egg laid in pairing exists after it was created",
        )

        egg = Animal.objects.create(species=self.sire.species)
        egg.parents.set([self.sire, self.dam])
        laid_on = pairing_ended_on + dt_days(1)
        Event.objects.create(
            animal=egg, status=status_laid, date=laid_on, entered_by=user
        )
        self.assertNotIn(
            egg,
            pairing.eggs(),
            "egg laid after the pairing is incorrectly associated with the pairing",
        )

        # check that the annotation counts eggs correctly
        annotated_pairing = Pairing.objects.with_progeny_stats().get(pk=pairing.pk)
        self.assertEqual(annotated_pairing.n_eggs, pairing.eggs().count())

    def test_pairing_progeny_status(self):
        pairing_began_on = today() - dt_days(10)
        pairing_ended_on = today()
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began_on=pairing_began_on,
            ended_on=pairing_ended_on,
        )
        self.assertEqual(pairing.eggs().count(), 0)
        user = models.get_sentinel_user()
        laid_on = pairing_ended_on - dt_days(4)
        egg = pairing.create_egg(date=laid_on, entered_by=user)
        Event.objects.create(
            animal=egg,
            status=models.get_unborn_creation_event_type(),
            date=laid_on,
            entered_by=user,
        )
        lost_on = laid_on + dt_days(2)
        Event.objects.create(
            animal=egg,
            status=Status.objects.get(name="lost"),
            date=lost_on,
            entered_by=user,
        )
        self.assertNotIn(
            egg,
            pairing.eggs().existing(laid_on - dt_days(1)),
            "egg laid in pairing does not exist before it was created",
        )
        self.assertIn(
            egg,
            pairing.eggs().existing(laid_on + dt_days(1)),
            "egg laid in pairing exists after it was created",
        )
        self.assertNotIn(
            egg,
            pairing.eggs().existing(lost_on + dt_days(1)),
            "egg laid in pairing does not exist after it was lost",
        )

    def test_pairing_progeny_stats(self):
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began_on=today() - dt_days(10),
            ended_on=today(),
        )
        chick_1 = make_child(self.sire, self.dam, today() - dt_days(5))
        chick_2 = make_child(self.sire, self.dam, today() - dt_days(4))
        # chicks count as eggs even if there is no event marking when the egg
        # was laid
        self.assertCountEqual(pairing.eggs(), [chick_1, chick_2])

        self.assertEqual(pairing.oldest_living_progeny_age(), chick_1.age())

        # check that the annotation counts eggs and progeny correctly. But in
        # this case the chicks do not count as eggs unless there is a laid
        # event. Should probably try to be consistent, though the discrepancy is
        # not a huge deal
        annotated_pairing = Pairing.objects.with_progeny_stats().get(pk=pairing.pk)
        self.assertEqual(annotated_pairing.n_eggs, 0)
        self.assertEqual(annotated_pairing.n_progeny, 2)

    def test_animal_birth_pairing(self):
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began_on=today() - dt_days(10),
            ended_on=today(),
        )
        chick_1 = make_child(self.sire, self.dam, today() - dt_days(5))
        self.assertEqual(chick_1.birth_pairing(), pairing)

    def test_related_events(self):
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began_on=today() - dt_days(10),
            ended_on=today() - dt_days(5),
        )
        user = models.get_sentinel_user()
        status = Status.objects.get(name="moved")
        Event.objects.create(
            animal=self.sire,
            status=status,
            date=today() - dt_days(20),
            entered_by=user,
        )
        self.assertEqual(pairing.events().count(), 0)

        event_during = Event.objects.create(
            animal=self.sire,
            status=status,
            date=today() - dt_days(6),
            entered_by=user,
        )
        self.assertCountEqual(pairing.events(), [event_during])

        Event.objects.create(
            animal=self.sire,
            status=status,
            date=today(),
            entered_by=user,
        )
        self.assertCountEqual(pairing.events(), [event_during])

    def test_pairing_last_location(self):
        # create pairing without a location
        pairing_began_on = today() - dt_days(10)
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began_on=pairing_began_on,
        )
        self.assertIn(pairing, Pairing.objects.active())
        self.assertIs(
            pairing.last_location(),
            None,
            "pairing without events should have no location",
        )
        self.assertIs(
            pairing.last_location(on_date=today() - dt_days(12)),
            None,
            "pairing without events should have no location before pairing started",
        )
        annotated_pairing = Pairing.objects.with_location().get(pk=pairing.pk)
        self.assertIs(
            annotated_pairing.last_location,
            None,
            "pairing without events should have no location",
        )

        # add an event before the pairing
        user = models.get_sentinel_user()
        status = Status.objects.get(name="moved")
        location = Location.objects.get(pk=1)
        _ = Event.objects.create(
            animal=self.sire,
            status=status,
            date=pairing_began_on - dt_days(10),
            entered_by=user,
            location=location,
        )
        self.assertIs(
            pairing.last_location(),
            None,
            "events before the pairing should not affect the location",
        )
        self.assertIs(
            pairing.last_location(on_date=pairing_began_on - dt_days(2)),
            None,
            "events before pairing should not affect location on any date",
        )
        annotated_pairing = Pairing.objects.with_location().get(pk=pairing.pk)
        self.assertIs(
            annotated_pairing.last_location,
            None,
            "events before the pairing began should not affect last_location",
        )

        # create an event during the pairing
        event_1 = Event.objects.create(
            animal=self.sire,
            status=status,
            date=today() - dt_days(6),
            entered_by=user,
            location=location,
        )
        self.assertEqual(
            pairing.last_location(),
            location,
            "pairing location should be the location of the most recent event",
        )
        self.assertIs(
            pairing.last_location(on_date=pairing_began_on),
            None,
            "pairing location should not include events before the specified date",
        )
        annotated_pairing = Pairing.objects.with_location().get(pk=pairing.pk)
        self.assertEqual(
            annotated_pairing.last_location,
            location.name,
            "pairing location should be the location of the most recent event",
        )

        # create a move event during the pairing - this time for the dam
        location_2 = Location.objects.get(pk=2)
        _ = Event.objects.create(
            animal=self.dam,
            status=status,
            date=today() - dt_days(4),
            entered_by=user,
            location=location_2,
        )
        self.assertEqual(
            pairing.last_location(),
            location_2,
            "pairing location should be the location of the most recent event",
        )
        self.assertEqual(
            pairing.last_location(on_date=event_1.date),
            event_1.location,
            "pairing location on date should not include events before the specified date",
        )
        annotated_pairing = Pairing.objects.with_location().get(pk=pairing.pk)
        self.assertEqual(
            annotated_pairing.last_location,
            location_2.name,
            "pairing location should be the location of the most recent event",
        )

    def test_pairing_last_location_on_date(self):
        # very similar to previous test but create all the events first and then
        # do the tests
        pairing_began_on = today() - dt_days(10)
        pairing_ended_on = today() - dt_days(3)
        user = models.get_sentinel_user()
        location_1 = Location.objects.get(pk=1)
        location_2 = Location.objects.get(pk=2)
        pairing = Pairing.objects.create_with_events(
            sire=self.sire,
            dam=self.dam,
            began_on=pairing_began_on,
            purpose="testing",
            entered_by=user,
            location=location_2,
        )
        pairing.close(ended_on=pairing_ended_on, entered_by=user, location=location_1)
        _ = Event.objects.create(
            animal=self.dam,
            status=Status.objects.get(name="moved"),
            date=today(),
            entered_by=user,
            location=location_2,
        )
        self.assertIs(
            pairing.last_location(on_date=pairing_began_on - dt_days(1)),
            None,
            "pairing location before pairing began should be None",
        )
        self.assertEqual(
            pairing.last_location(on_date=pairing_began_on),
            location_2,
            "pairing location after pairing began should be last location of sire or dam",
        )
        self.assertEqual(
            pairing.last_location(on_date=pairing_ended_on),
            location_1,
            "pairing location when pairing ended should be last location in the pairing interval",
        )
        self.assertEqual(
            pairing.last_location(on_date=pairing_ended_on + datetime.timedelta(1)),
            location_1,
            "pairing location after pairing ended should be last location in the pairing interval",
        )

    def test_pairing_close_with_location(self):
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began_on=today() - dt_days(10),
        )
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=1)
        date = today()
        pairing.close(
            ended_on=date,
            entered_by=user,
            location=location,
            comment="test comment",
        )
        self.assertFalse(pairing.active())
        sire_events = self.sire.event_set.all()
        # one event because we didn't supply a location on creation
        self.assertEqual(
            sire_events.count(),
            1,
            "sire should have one event from closing the pairing",
        )
        self.assertEqual(
            sire_events.first().date,
            date,
            "sire's event date should be the date when the pairing closed",
        )
        self.assertEqual(
            pairing.last_location(),
            location,
            "closed pairing's location should be that of the last event in the pairing",
        )
        dam_events = self.dam.event_set.all()
        self.assertEqual(
            dam_events.count(),
            1,
            "dam should have one event from closing the pairing",
        )
        self.assertEqual(
            dam_events.first().date,
            date,
            "dam's event date should be the date when the pairing closed",
        )
        with self.assertRaises(ValueError):
            pairing.close(
                ended_on=date,
                entered_by=user,
                location=location,
            )

    def test_pairing_close_without_location(self):
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began_on=today() - dt_days(10),
        )
        user = models.get_sentinel_user()
        date = today()
        pairing.close(
            ended_on=date,
            entered_by=user,
        )
        self.assertFalse(pairing.active())
        sire_events = self.sire.event_set.all()
        self.assertEqual(
            sire_events.count(),
            0,
            "sire should not have any events after closing without a location",
        )
        dam_events = self.dam.event_set.all()
        self.assertEqual(
            dam_events.count(),
            0,
            "dam should not have any events after closing pairing without a location",
        )
        with self.assertRaises(ValueError):
            pairing.close(
                ended_on=date,
                entered_by=user,
            )

    def test_close_pairing_removes_eggs(self):
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began_on=today() - dt_days(10),
        )
        user = models.get_sentinel_user()
        _egg = pairing.create_egg(date=today() - dt_days(1), entered_by=user)
        pairing.close(ended_on=today(), entered_by=user, remove_unhatched=True)
        eggs = pairing.eggs().existing()
        self.assertEqual(eggs.count(), 0)

    def test_close_pairing_default_does_not_remove_eggs(self):
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began_on=today() - dt_days(10),
        )
        user = models.get_sentinel_user()
        egg = pairing.create_egg(date=today() - dt_days(1), entered_by=user)
        pairing.close(ended_on=today(), entered_by=user)
        eggs = pairing.eggs().existing()
        self.assertTrue(egg in eggs)


class LocationModelTests(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    def test_location_birds(self):
        location = Location.objects.get(pk=2)
        self.assertFalse(location.birds().exists())
        species = Species.objects.get(pk=1)
        user = models.get_sentinel_user()
        bird = Animal.objects.create_with_event(
            species,
            date=today(),
            status=models.get_birth_event_type(),
            entered_by=user,
            location=location,
        )
        self.assertCountEqual(location.birds(), [bird])

    def test_location_birds_on_date(self):
        location_1 = Location.objects.get(pk=2)
        location_2 = Location.objects.get(pk=1)
        self.assertFalse(
            location_1.birds().exists(),
            "no birds should exist in location at start of test",
        )
        self.assertFalse(
            location_2.birds().exists(),
            "no birds should exist in location at start of test",
        )

        species = Species.objects.get(pk=1)
        user = models.get_sentinel_user()
        status = Status.objects.get(name="moved")
        last_week = today() - dt_days(7)
        # bird starts in location 1 one week ago
        bird = Animal.objects.create_with_event(
            species,
            date=last_week,
            status=models.get_birth_event_type(),
            entered_by=user,
            location=location_1,
        )
        # bird moves to location 2 yesterday
        yesterday = today() - dt_days(1)
        _event = Event.objects.create(
            animal=bird,
            date=yesterday,
            status=status,
            entered_by=user,
            location=location_2,
        )

        self.assertFalse(
            location_1.birds().exists(), "bird should not be in location 1 today"
        )
        self.assertCountEqual(
            location_2.birds(), [bird], "bird should be in location 2 today"
        )
        self.assertFalse(
            location_1.birds(on_date=yesterday).exists(),
            "bird should not be in location 1 yesterday",
        )
        self.assertCountEqual(
            location_2.birds(on_date=yesterday),
            [bird],
            "bird should be in location 2 yesterday",
        )
        self.assertCountEqual(
            location_1.birds(on_date=last_week),
            [bird],
            "bird should be in location 1 last week",
        )
        self.assertFalse(
            location_2.birds(on_date=last_week).exists(),
            "bird should not be in location 2 last week",
        )

    def test_location_birds_on_date_with_events(self):
        location_1 = Location.objects.get(pk=2)
        self.assertFalse(
            location_1.birds().exists(),
            "no birds should exist in location at start of test",
        )
        species = Species.objects.get(pk=1)
        user = models.get_sentinel_user()
        last_week = today() - dt_days(7)
        # bird starts in location 1 as an egg
        bird = Animal.objects.create_with_event(
            species,
            date=last_week,
            status=models.get_unborn_creation_event_type(),
            entered_by=user,
            location=location_1,
        )
        # then it hatches yesterday
        yesterday = today() - dt_days(1)
        _event = Event.objects.create(
            animal=bird,
            date=yesterday,
            status=models.get_birth_event_type(),
            entered_by=user,
            location=location_1,
        )
        self.assertTrue(
            location_1.birds().exists(), "bird should be in location 1 today"
        )
        self.assertTrue(
            location_1.birds(yesterday).exists(),
            "bird should be in location 1 yesterday",
        )
        self.assertTrue(
            location_1.birds(last_week).exists(),
            "bird should be in location 1 one week ago",
        )
        # check that age group calculations still work as expected
        self.assertEqual(
            location_1.birds(last_week).with_dates(last_week).first().age_group(),
            models.UNBORN_ANIMAL_NAME,
            f"bird age group should be '{models.UNBORN_ANIMAL_NAME}' after laid event",
        )
        self.assertEqual(
            location_1.birds(yesterday).with_dates(yesterday).first().age_group(),
            "hatchling",
            "bird age group should be 'hatchling' after hatch event",
        )
        self.assertEqual(
            location_1.birds().with_dates().first().age_group(),
            "hatchling",
            "bird age group should be 'hatchling' on today",
        )
