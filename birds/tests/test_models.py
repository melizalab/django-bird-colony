# -*- coding: utf-8 -*-
# -*- mode: python -*-
import datetime

from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.utils import IntegrityError

from birds import models
from birds.models import Animal, Species, Event, Color, Status, Location, Pairing


def make_child(sire, dam, birthday=None, **kwargs):
    """Convenience function to make a child"""
    child = Animal.objects.create(species=sire.species, **kwargs)
    child.parents.set([sire, dam])
    if birthday is not None:
        status = models.get_birth_event_type()
        user = models.get_sentinel_user()
        event = Event.objects.create(
            animal=child, status=status, date=birthday, entered_by=user
        )
    return child


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
        bird = Animal.objects.create(species=species)
        self.assertIs(bird.acquisition_event(), None)
        self.assertIs(bird.age(), None)
        self.assertIs(bird.alive(), False)
        random_date = datetime.date.today() - datetime.timedelta(days=5)
        self.assertIs(bird.age(date=random_date), None)
        self.assertNotIn(bird, Animal.objects.alive())
        self.assertNotIn(bird, Animal.objects.hatched())

    def test_status_of_hatched_bird(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        status = models.get_birth_event_type()
        age = datetime.timedelta(days=5)
        birthday = datetime.date.today() - age
        user = models.get_sentinel_user()
        event = Event.objects.create(
            animal=bird, status=status, date=birthday, entered_by=user
        )
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
        bird = Animal.objects.create(species=species)
        status = Status.objects.get(name="transferred in")
        self.assertEqual(status.adds, 1)
        acq_on = datetime.date.today() - datetime.timedelta(days=10)
        user = models.get_sentinel_user()
        event = Event.objects.create(
            animal=bird, status=status, date=acq_on, entered_by=user
        )

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
        bird = Animal.objects.create(species=species)
        user = models.get_sentinel_user()
        status_born = models.get_birth_event_type()
        self.assertEqual(status_born.adds, 1)
        born_on = datetime.date.today() - datetime.timedelta(days=10)
        event_born = Event.objects.create(
            animal=bird, status=status_born, date=born_on, entered_by=user
        )
        status_died = Status.objects.get(name="died")
        self.assertEqual(status_died.removes, 1)
        died_on = datetime.date.today() - datetime.timedelta(days=1)
        event_died = Event.objects.create(
            animal=bird, status=status_died, date=died_on, entered_by=user
        )

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
        egg = Animal.objects.create(species=species)
        user = models.get_sentinel_user()
        status_laid = models.get_unborn_creation_event_type()
        self.assertEqual(status_laid.adds, 0)
        laid_on = datetime.date.today() - datetime.timedelta(days=10)
        event_laid = Event.objects.create(
            animal=egg, status=status_laid, date=laid_on, entered_by=user
        )

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
            bird = Animal.objects.create(species=species)
            birthday = datetime.date.today() - datetime.timedelta(
                days=age_group.min_days
            )
            event = Event.objects.create(
                animal=bird, status=status, date=birthday, entered_by=user
            )
            abird = Animal.objects.with_dates().get(pk=bird.pk)
            self.assertEqual(abird.age_group(), age_group.name)

    def test_bird_locations(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        self.assertIs(bird.last_location(), None)
        user = models.get_sentinel_user()
        status_1 = models.get_birth_event_type()
        birthday = datetime.date.today() - datetime.timedelta(days=10)
        location_1 = Location.objects.get(pk=2)
        event_1 = Event.objects.create(
            animal=bird,
            status=status_1,
            date=birthday,
            entered_by=user,
            location=location_1,
        )
        self.assertEqual(bird.last_location(), location_1)

        status_2 = Status.objects.get(name="moved")
        date_2 = datetime.date.today() - datetime.timedelta(days=1)
        location_2 = Location.objects.get(pk=1)
        event_2 = Event.objects.create(
            animal=bird,
            status=status_2,
            date=date_2,
            entered_by=user,
            location=location_2,
        )
        self.assertIs(bird.alive(), True)
        self.assertEqual(bird.last_location(), location_2)
        self.assertEqual(bird.last_location(date=birthday), location_1)
        self.assertIs(
            bird.last_location(date=birthday - datetime.timedelta(days=1)), None
        )

    def test_updating_sex(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        self.assertFalse(bird.sexed())
        self.assertEqual(bird.sex, Animal.Sex.UNKNOWN_SEX)

        user = models.get_sentinel_user()
        date = datetime.date.today()
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
        date = datetime.date.today()
        color = Color.objects.get(pk=1)
        event = bird.update_band(
            band_number=100,
            band_color=color,
            date=datetime.date.today(),
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
        # child has no hatch event
        self.assertEqual(sire.children.unhatched().count(), 1)
        self.assertEqual(sire.children.hatched().count(), 0)
        self.assertEqual(sire.children.alive().count(), 0)

    def test_bird_child_counts(self):
        species = Species.objects.get(pk=1)
        sire = Animal.objects.create(species=species, sex=Animal.Sex.MALE)
        dam = Animal.objects.create(species=species, sex=Animal.Sex.FEMALE)
        age = datetime.timedelta(days=5)
        birthday = datetime.date.today() - age
        child = make_child(sire, dam, birthday)
        self.assertEqual(sire.children.unhatched().count(), 0)
        self.assertEqual(sire.children.hatched().count(), 1)
        self.assertEqual(sire.children.alive().count(), 1)

    def test_genealogy(self):
        species = Species.objects.get(pk=1)
        sire = Animal.objects.create(species=species, sex=Animal.Sex.MALE)
        dam = Animal.objects.create(species=species, sex=Animal.Sex.FEMALE)
        birthday = datetime.date.today()  # date doesn't matter for birthdays
        son = make_child(
            sire,
            dam,
            birthday,
            sex=Animal.Sex.MALE,
        )
        wife = Animal.objects.create(species=species, sex=Animal.Sex.FEMALE)
        grandson = make_child(son, wife, birthday, sex=Animal.Sex.MALE)
        granddaughter = make_child(son, wife, birthday, sex=Animal.Sex.FEMALE)
        children = Animal.objects.descendents_of(sire, generation=1)
        self.assertCountEqual(children, [son])
        grandchildren = Animal.objects.descendents_of(sire, generation=2)
        self.assertCountEqual(grandchildren, [grandson, granddaughter])
        parents = Animal.objects.ancestors_of(grandson, generation=1)
        self.assertCountEqual(parents, [son, wife])
        grandparents = Animal.objects.ancestors_of(grandson, generation=2)
        self.assertCountEqual(grandparents, [sire, dam])


class EventModelTests(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    def test_age_at_event_time(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        status = models.get_birth_event_type()
        age = datetime.timedelta(days=5)
        birthday = datetime.date.today() - age
        user = models.get_sentinel_user()
        event = Event.objects.create(
            animal=bird, status=status, date=birthday, entered_by=user
        )
        self.assertEqual(event.age(), datetime.timedelta(days=0))
        status_2 = Status.objects.get(name="moved")
        date_2 = datetime.date.today() - datetime.timedelta(days=1)
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
        date_2 = datetime.date.today() - datetime.timedelta(days=1)
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
            date=datetime.date.today() - datetime.timedelta(days=1),
            entered_by=user,
        )
        event_1_2 = Event.objects.create(
            animal=bird_1,
            status=status,
            date=datetime.date.today() - datetime.timedelta(days=10),
            entered_by=user,
        )

        bird_2 = Animal.objects.create(species=species)
        event_2_1 = Event.objects.create(
            animal=bird_2,
            status=status,
            date=datetime.date.today() - datetime.timedelta(days=50),
            entered_by=user,
        )

        event_2_2 = Event.objects.create(
            animal=bird_2,
            status=status,
            date=datetime.date.today() - datetime.timedelta(days=25),
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
            animal=bird, status=status, date=datetime.date.today(), entered_by=user
        )
        self.assertCountEqual(Event.objects.in_month(), [event])

    def test_specific_month_filter(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        status = Status.objects.get(name="note")
        user = models.get_sentinel_user()
        month = datetime.date(2024, 4, 1)
        event_1 = Event.objects.create(
            animal=bird, status=status, date=datetime.date(2024, 3, 1), entered_by=user
        )
        event_2 = Event.objects.create(
            animal=bird, status=status, date=month, entered_by=user
        )
        event_3 = Event.objects.create(
            animal=bird, status=status, date=datetime.date(2024, 5, 1), entered_by=user
        )
        self.assertCountEqual(Event.objects.in_month(month), [event_2])

    def test_event_counts(self):
        species = Species.objects.get(pk=1)
        bird = Animal.objects.create(species=species)
        user = models.get_sentinel_user()
        status_1 = Status.objects.get(name="note")
        _event = Event.objects.create(
            animal=bird, status=status_1, date=datetime.date.today(), entered_by=user
        )
        _event = Event.objects.create(
            animal=bird, status=status_1, date=datetime.date.today(), entered_by=user
        )
        status_2 = Status.objects.get(name="moved")
        _event = Event.objects.create(
            animal=bird, status=status_2, date=datetime.date.today(), entered_by=user
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
        date = datetime.date.today()
        pairing = Pairing.objects.create_with_events(
            sire=self.sire,
            dam=self.dam,
            began=date,
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

    def test_pairing_invalid_sexes(self):
        pairing = Pairing(
            sire=self.dam,
            dam=self.sire,
            began=datetime.date.today(),
        )
        with self.assertRaises(ValidationError):
            pairing.full_clean()

    def test_pairing_invalid_dates(self):
        with self.assertRaises(IntegrityError):
            pairing = Pairing.objects.create(
                sire=self.sire,
                dam=self.dam,
                began=datetime.date.today(),
                ended=datetime.date.today() - datetime.timedelta(days=5),
            )

    def test_bird_pairing_lists(self):
        pairing_1 = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began=datetime.date.today() - datetime.timedelta(days=100),
            ended=datetime.date.today() - datetime.timedelta(days=70),
        )
        other_bird = Animal.objects.create(
            species=Species.objects.get(pk=1), sex=Animal.Sex.FEMALE
        )
        pairing_2 = Pairing.objects.create(
            sire=self.sire,
            dam=other_bird,
            began=datetime.date.today() - datetime.timedelta(days=50),
            ended=datetime.date.today() - datetime.timedelta(days=20),
        )
        pairing_3 = Pairing.objects.create(
            sire=self.sire, dam=self.dam, began=datetime.date.today()
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
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began=datetime.date.today() - datetime.timedelta(days=10),
            ended=datetime.date.today(),
        )
        self.assertEqual(pairing.eggs().count(), 0)
        user = models.get_sentinel_user()
        status_laid = models.get_unborn_creation_event_type()

        # this egg was laid before the pairing began, so should not be in the list
        egg = Animal.objects.create(species=self.sire.species)
        egg.parents.set([self.sire, self.dam])
        laid_on = datetime.date.today() - datetime.timedelta(days=11)
        event_laid = Event.objects.create(
            animal=egg, status=status_laid, date=laid_on, entered_by=user
        )
        self.assertEqual(pairing.eggs().count(), 0)
        self.assertNotIn(egg, pairing.eggs())

        # this egg was laid after the pairing began, so should be in the list
        egg = Animal.objects.create(species=self.sire.species)
        egg.parents.set([self.sire, self.dam])
        laid_on = datetime.date.today() - datetime.timedelta(days=1)
        event_laid = Event.objects.create(
            animal=egg, status=status_laid, date=laid_on, entered_by=user
        )
        self.assertCountEqual(pairing.eggs(), [egg])

        # this egg was laid after the pairing ended, so should not be in the list
        egg = Animal.objects.create(species=self.sire.species)
        egg.parents.set([self.sire, self.dam])
        laid_on = datetime.date.today() + datetime.timedelta(days=1)
        event_laid = Event.objects.create(
            animal=egg, status=status_laid, date=laid_on, entered_by=user
        )
        self.assertEqual(pairing.eggs().count(), 1)
        self.assertNotIn(egg, pairing.eggs())

        # check that the annotation counts eggs correctly
        annotated_pairing = Pairing.objects.with_progeny_stats().get(pk=pairing.pk)
        self.assertEqual(annotated_pairing.n_eggs, pairing.eggs().count())

    def test_pairing_progeny_stats(self):
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began=datetime.date.today() - datetime.timedelta(days=10),
            ended=datetime.date.today(),
        )
        chick_1 = make_child(
            self.sire, self.dam, datetime.date.today() - datetime.timedelta(days=5)
        )
        chick_2 = make_child(
            self.sire, self.dam, datetime.date.today() - datetime.timedelta(days=4)
        )
        # chicks count as eggs even if there is no event marking when the egg
        # was laid
        self.assertCountEqual(pairing.eggs(), [chick_1, chick_2])

        self.assertEqual(pairing.oldest_living_progeny_age(), chick_1.age().days)

        # check that the annotation counts eggs and progeny correctly. But in
        # this case the chicks do not count as eggs unless there is a laid
        # event. Should probably try to be consistent, though the discrepancy is
        # not a huge deal
        annotated_pairing = Pairing.objects.with_progeny_stats().get(pk=pairing.pk)
        self.assertEqual(annotated_pairing.n_eggs, 0)
        self.assertEqual(annotated_pairing.n_progeny, 2)

    def test_pairing_lookup(self):
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began=datetime.date.today() - datetime.timedelta(days=10),
            ended=datetime.date.today(),
        )
        chick_1 = make_child(
            self.sire, self.dam, datetime.date.today() - datetime.timedelta(days=5)
        )
        self.assertEqual(chick_1.birth_pairing(), pairing)

    def test_related_events(self):
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began=datetime.date.today() - datetime.timedelta(days=10),
            ended=datetime.date.today() - datetime.timedelta(days=5),
        )
        user = models.get_sentinel_user()
        status = Status.objects.get(name="moved")
        event_before = Event.objects.create(
            animal=self.sire,
            status=status,
            date=datetime.date.today() - datetime.timedelta(days=20),
            entered_by=user,
        )
        self.assertEqual(pairing.related_events().count(), 0)

        event_during = Event.objects.create(
            animal=self.sire,
            status=status,
            date=datetime.date.today() - datetime.timedelta(days=6),
            entered_by=user,
        )
        self.assertCountEqual(pairing.related_events(), [event_during])

        event_after = Event.objects.create(
            animal=self.sire,
            status=status,
            date=datetime.date.today(),
            entered_by=user,
        )
        self.assertCountEqual(pairing.related_events(), [event_during])

    def test_last_location(self):
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began=datetime.date.today() - datetime.timedelta(days=10),
        )
        self.assertIn(pairing, Pairing.objects.active())
        annotated_pairing = Pairing.objects.with_location().get(pk=pairing.pk)
        self.assertIs(pairing.last_location(), None)
        self.assertIs(annotated_pairing.last_location, None)

        user = models.get_sentinel_user()
        status = Status.objects.get(name="moved")
        location = Location.objects.get(pk=1)
        _ = Event.objects.create(
            animal=self.sire,
            status=status,
            date=datetime.date.today() - datetime.timedelta(days=20),
            entered_by=user,
            location=location,
        )
        annotated_pairing = Pairing.objects.with_location().get(pk=pairing.pk)
        self.assertIs(pairing.last_location(), None)
        self.assertIs(annotated_pairing.last_location, None)

        _ = Event.objects.create(
            animal=self.sire,
            status=status,
            date=datetime.date.today() - datetime.timedelta(days=5),
            entered_by=user,
            location=location,
        )
        annotated_pairing = Pairing.objects.with_location().get(pk=pairing.pk)
        self.assertEqual(pairing.last_location(), location)
        self.assertEqual(annotated_pairing.last_location, location.name)

        location_2 = Location.objects.get(pk=2)
        _ = Event.objects.create(
            animal=self.sire,
            status=status,
            date=datetime.date.today() - datetime.timedelta(days=1),
            entered_by=user,
            location=location_2,
        )
        annotated_pairing = Pairing.objects.with_location().get(pk=pairing.pk)
        self.assertEqual(pairing.last_location(), location_2)
        self.assertEqual(annotated_pairing.last_location, location_2.name)

    def test_pairing_close_with_location(self):
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began=datetime.date.today() - datetime.timedelta(days=10),
        )
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=1)
        date = datetime.date.today()
        pairing.close(
            ended=date,
            entered_by=user,
            location=location,
            comment="test comment",
        )
        self.assertFalse(pairing.active())
        sire_events = self.sire.event_set.all()
        self.assertEqual(sire_events.count(), 1)
        self.assertEqual(sire_events.first().date, date)
        dam_events = self.dam.event_set.all()
        self.assertEqual(dam_events.count(), 1)
        self.assertEqual(dam_events.first().date, date)
        with self.assertRaises(ValueError):
            pairing.close(
                ended=date,
                entered_by=user,
                location=location,
            )

    def test_pairing_close_without_location(self):
        pairing = Pairing.objects.create(
            sire=self.sire,
            dam=self.dam,
            began=datetime.date.today() - datetime.timedelta(days=10),
        )
        user = models.get_sentinel_user()
        date = datetime.date.today()
        pairing.close(
            ended=date,
            entered_by=user,
        )
        self.assertFalse(pairing.active())
        sire_events = self.sire.event_set.all()
        self.assertEqual(sire_events.count(), 0)
        dam_events = self.dam.event_set.all()
        self.assertEqual(dam_events.count(), 0)
        with self.assertRaises(ValueError):
            pairing.close(
                ended=date,
                entered_by=user,
            )
