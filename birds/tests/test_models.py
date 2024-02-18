# -*- coding: utf-8 -*-
# -*- mode: python -*-
import datetime

from django.test import TestCase

from birds import models
from birds.models import Animal, Species, Event, Color, Status, Location


class AnimalModelTests(TestCase):
    fixtures = ["bird_colony_starter_kit"]

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
        bird = Animal(species=species)
        bird.save()
        self.assertIs(bird.acquisition_event(), None)
        self.assertIs(bird.age(), None)
        self.assertIs(bird.alive(), False)
        random_date = datetime.date.today() - datetime.timedelta(days=5)
        self.assertIs(bird.age(date=random_date), None)
        self.assertNotIn(bird, Animal.objects.alive())
        self.assertNotIn(bird, Animal.objects.hatched())

    def test_status_of_hatched_bird(self):
        species = Species.objects.get(pk=1)
        bird = Animal(species=species)
        bird.save()
        status = models.get_birth_event_type()
        age = datetime.timedelta(days=5)
        birthday = datetime.date.today() - age
        user = models.get_sentinel_user()
        event = Event(animal=bird, status=status, date=birthday, entered_by=user)
        event.save()
        self.assertEqual(bird.acquisition_event(), event)
        self.assertEqual(bird.age(), age)
        self.assertEqual(bird.age(date=birthday), datetime.timedelta(days=0))
        self.assertIs(bird.age(date=birthday - datetime.timedelta(days=1)), None)

        self.assertIs(bird.alive(), True)
        self.assertIs(bird.alive(date=birthday), True)
        self.assertIs(bird.alive(date=birthday - datetime.timedelta(days=1)), False)
        self.assertIs(bird.expected_hatch(), None)

        annotated_bird = Animal.objects.with_status().get(pk=bird.pk)
        self.assertIs(annotated_bird.alive, True)

        annotated_bird = Animal.objects.with_dates().get(pk=bird.pk)
        self.assertEqual(annotated_bird.born_on, birthday)
        self.assertEqual(annotated_bird.acquired_on, birthday)
        self.assertIs(annotated_bird.died_on, None)
        self.assertEqual(annotated_bird.age, age)

        self.assertIn(bird, Animal.objects.alive())
        self.assertIn(bird, Animal.objects.hatched())
        self.assertNotIn(bird, Animal.objects.unhatched())
        self.assertIn(bird, Animal.objects.alive_on(birthday))
        self.assertNotIn(
            bird, Animal.objects.alive_on(birthday - datetime.timedelta(days=1))
        )
        self.assertIn(bird, Animal.objects.existed_on(birthday))
        self.assertNotIn(
            bird, Animal.objects.existed_on(birthday - datetime.timedelta(days=1))
        )

    def test_status_of_transferred_bird(self):
        species = Species.objects.get(pk=1)
        bird = Animal(species=species)
        bird.save()
        status = Status.objects.get(name="transferred in")
        self.assertEqual(status.adds, 1)
        acq_on = datetime.date.today() - datetime.timedelta(days=10)
        user = models.get_sentinel_user()
        event = Event(animal=bird, status=status, date=acq_on, entered_by=user)
        event.save()

        self.assertEqual(bird.acquisition_event(), event)
        self.assertIs(bird.age(), None)
        self.assertIs(bird.age(date=acq_on), None)
        self.assertIs(bird.alive(), True)
        self.assertIs(bird.alive(date=acq_on), True)
        self.assertIs(bird.alive(date=acq_on - datetime.timedelta(days=1)), False)
        self.assertIs(bird.expected_hatch(), None)

        annotated_bird = Animal.objects.with_status().get(pk=bird.pk)
        self.assertIs(annotated_bird.alive, True)

        annotated_bird = Animal.objects.with_dates().get(pk=bird.pk)
        self.assertIs(annotated_bird.born_on, None)
        self.assertEqual(annotated_bird.acquired_on, acq_on)
        self.assertIs(annotated_bird.died_on, None)
        self.assertIs(annotated_bird.age, None)
        self.assertEqual(annotated_bird.age_group(), models.ADULT_ANIMAL_NAME)

        self.assertIn(bird, Animal.objects.alive())
        self.assertNotIn(bird, Animal.objects.hatched())
        self.assertIn(bird, Animal.objects.unhatched())
        self.assertIn(bird, Animal.objects.alive_on(acq_on))
        self.assertNotIn(
            bird, Animal.objects.alive_on(acq_on - datetime.timedelta(days=1))
        )
        self.assertIn(bird, Animal.objects.existed_on(acq_on))
        self.assertNotIn(
            bird, Animal.objects.existed_on(acq_on - datetime.timedelta(days=1))
        )

    def test_status_of_dead_bird(self):
        species = Species.objects.get(pk=1)
        bird = Animal(species=species)
        bird.save()
        user = models.get_sentinel_user()
        status_born = models.get_birth_event_type()
        self.assertEqual(status_born.adds, 1)
        born_on = datetime.date.today() - datetime.timedelta(days=10)
        event_born = Event(
            animal=bird, status=status_born, date=born_on, entered_by=user
        )
        event_born.save()
        status_died = Status.objects.get(name="died")
        self.assertEqual(status_died.removes, 1)
        died_on = datetime.date.today() - datetime.timedelta(days=1)
        event_died = Event(
            animal=bird, status=status_died, date=died_on, entered_by=user
        )
        event_died.save()

        self.assertEqual(bird.acquisition_event(), event_born)
        self.assertIs(bird.alive(), False)
        self.assertIs(bird.alive(date=died_on - datetime.timedelta(days=1)), True)
        self.assertIs(bird.alive(date=born_on - datetime.timedelta(days=1)), False)

        self.assertEqual(bird.age(), died_on - born_on)
        self.assertEqual(bird.age(date=died_on), died_on - born_on)
        self.assertIs(bird.expected_hatch(), None)

        annotated_bird = Animal.objects.with_status().get(pk=bird.pk)
        self.assertIs(annotated_bird.alive, False)

        annotated_bird = Animal.objects.with_dates().get(pk=bird.pk)
        self.assertEqual(annotated_bird.born_on, born_on)
        self.assertEqual(annotated_bird.acquired_on, born_on)
        self.assertEqual(annotated_bird.died_on, died_on)
        self.assertEqual(annotated_bird.age, died_on - born_on)

        self.assertNotIn(bird, Animal.objects.alive())
        self.assertIn(bird, Animal.objects.hatched())
        self.assertNotIn(bird, Animal.objects.unhatched())
        self.assertIn(bird, Animal.objects.alive_on(born_on))
        self.assertIn(
            bird, Animal.objects.alive_on(died_on - datetime.timedelta(days=1))
        )
        self.assertNotIn(
            bird, Animal.objects.alive_on(born_on - datetime.timedelta(days=1))
        )
        self.assertIn(bird, Animal.objects.existed_on(born_on))
        self.assertIn(
            bird, Animal.objects.existed_on(died_on - datetime.timedelta(days=1))
        )
        self.assertNotIn(
            bird, Animal.objects.existed_on(born_on - datetime.timedelta(days=1))
        )

    def test_status_of_egg(self):
        species = Species.objects.get(pk=1)
        egg = Animal(species=species)
        egg.save()
        user = models.get_sentinel_user()
        status_laid = models.get_unborn_creation_event_type()
        self.assertEqual(status_laid.adds, 0)
        laid_on = datetime.date.today() - datetime.timedelta(days=10)
        event_laid = Event(
            animal=egg, status=status_laid, date=laid_on, entered_by=user
        )
        event_laid.save()

        self.assertIs(egg.acquisition_event(), None)
        self.assertIs(egg.alive(), False)
        self.assertIs(egg.age(), None)
        eggspected_hatch = laid_on + datetime.timedelta(days=species.incubation_days)
        self.assertEqual(egg.expected_hatch(), eggspected_hatch)

        annotated_egg = Animal.objects.with_status().get(pk=egg.pk)
        self.assertIs(annotated_egg.alive, False)

        annotated_egg = Animal.objects.with_dates().get(pk=egg.pk)
        self.assertIs(annotated_egg.born_on, None)
        self.assertIs(annotated_egg.acquired_on, None)
        self.assertIs(annotated_egg.died_on, None)
        self.assertIs(annotated_egg.age, None)
        self.assertEqual(annotated_egg.age_group(), models.UNBORN_ANIMAL_NAME)

        self.assertNotIn(egg, Animal.objects.alive())
        self.assertNotIn(egg, Animal.objects.hatched())
        self.assertIn(egg, Animal.objects.unhatched())
        self.assertIn(egg, Animal.objects.existed_on(laid_on))
        self.assertNotIn(
            egg, Animal.objects.existed_on(laid_on - datetime.timedelta(days=1))
        )

    def test_age_grouping(self):
        species = Species.objects.get(pk=1)
        status = models.get_birth_event_type()
        user = models.get_sentinel_user()
        for age_group in species.age_set.all():
            bird = Animal(species=species)
            bird.save()
            birthday = datetime.date.today() - datetime.timedelta(
                days=age_group.min_days
            )
            event = Event(animal=bird, status=status, date=birthday, entered_by=user)
            event.save()
            abird = Animal.objects.with_dates().get(pk=bird.pk)
            self.assertEqual(abird.age_group(), age_group.name)

    def test_bird_locations(self):
        species = Species.objects.get(pk=1)
        bird = Animal(species=species)
        bird.save()
        self.assertIs(bird.last_location(), None)
        user = models.get_sentinel_user()
        status_1 = models.get_birth_event_type()
        birthday = datetime.date.today() - datetime.timedelta(days=10)
        location_1 = Location.objects.get(pk=2)
        event_1 = Event(
            animal=bird,
            status=status_1,
            date=birthday,
            entered_by=user,
            location=location_1,
        )
        event_1.save()
        self.assertEqual(bird.last_location(), location_1)

        status_2 = Status.objects.get(name="moved")
        date_2 = datetime.date.today() - datetime.timedelta(days=1)
        location_2 = Location.objects.get(pk=1)
        event_2 = Event(
            animal=bird,
            status=status_2,
            date=date_2,
            entered_by=user,
            location=location_2,
        )
        event_2.save()
        self.assertIs(bird.alive(), True)
        self.assertEqual(bird.last_location(), location_2)
        self.assertEqual(bird.last_location(date=birthday), location_1)
        self.assertIs(
            bird.last_location(date=birthday - datetime.timedelta(days=1)), None
        )
