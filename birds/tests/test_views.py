# -*- mode: python -*-
import datetime
import uuid
import warnings

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import make_aware

from birds import models
from birds.models import (
    Animal,
    Color,
    Event,
    Location,
    Measure,
    Measurement,
    NestCheck,
    Pairing,
    Sample,
    SampleLocation,
    SampleType,
    Species,
    Status,
)

warnings.filterwarnings("error")
User = get_user_model()


def today() -> datetime.date:
    return datetime.date.today()


def dt_days(days: int) -> datetime.timedelta:
    return datetime.timedelta(days=days)


class BaseColonyTest(TestCase):
    """Base class for tests that need a pre-populated colony"""

    fixtures = ["bird_colony_starter_kit"]

    @classmethod
    def setUpTestData(cls):
        birthday = today() - dt_days(365)
        status = models.get_birth_event_type()
        user = models.get_sentinel_user()
        species = Species.objects.get(pk=1)
        band_color = Color.objects.get(pk=1)
        measure = Measure.objects.get(pk=1)
        cls.sire = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=birthday,
            entered_by=user,
            location=Location.objects.get(pk=1),
            sex=Animal.Sex.MALE,
            band_color=band_color,
            band_number=1,
        )
        cls.sire.add_measurements([(measure, 15.0)], today(), user)
        cls.dam = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=birthday,
            entered_by=user,
            location=Location.objects.get(pk=1),
            sex=Animal.Sex.FEMALE,
            band_color=band_color,
            band_number=2,
        )
        cls.n_children = 10
        cls.n_eggs = 5
        cls.nest = Location.objects.filter(nest=True).first()
        pairing = Pairing.objects.create_with_events(
            sire=cls.sire,
            dam=cls.dam,
            began_on=birthday + dt_days(80),
            purpose="old pairing",
            entered_by=user,
            location=cls.nest,
        )
        pairing.close(
            ended_on=birthday + dt_days(120),
            entered_by=user,
            location=Location.objects.get(pk=1),
            comment="ended old pairing",
        )
        for i in range(cls.n_children):
            _child = Animal.objects.create_from_parents(
                sire=cls.sire,
                dam=cls.dam,
                date=birthday + datetime.timedelta(days=90 + i),
                status=status,
                entered_by=user,
                location=cls.nest,
                description="for unto us a child is born",
                sex=Animal.Sex.UNKNOWN_SEX,
                band_color=band_color,
                band_number=10 + i,
            )
        cls.pairing = Pairing.objects.create_with_events(
            sire=cls.sire,
            dam=cls.dam,
            began_on=today() - dt_days(20),
            purpose="new pairing",
            entered_by=user,
            location=cls.nest,
        )
        status = models.get_unborn_creation_event_type()
        for i in range(cls.n_eggs):
            _child = Animal.objects.create_from_parents(
                sire=cls.sire,
                dam=cls.dam,
                date=today() - datetime.timedelta(days=i),
                status=status,
                entered_by=user,
                location=cls.nest,
                description=f"egg {i} laid",
                sex=Animal.Sex.UNKNOWN_SEX,
            )


class MiscellaneousViewTests(TestCase):
    def test_index(self):
        response = self.client.get(reverse("birds:index"))
        self.assertEqual(response.status_code, 200)


class AnimalViewTests(BaseColonyTest):
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
        self.assertDictEqual(response.context["query"], {"living": ["True"]})

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
            len(response.context["animal_list"]), self.n_children
        )
        # one hatch, old pairing started and ended, new pairing started, measurement
        self.assertEqual(len(response.context["event_list"]), 5)
        self.assertEqual(len(response.context["pairing_list"]), 2)
        self.assertEqual(len(response.context["animal_measurements"]), 1)

    def test_child_detail_view_contains_all_related_objects(self):
        child = self.sire.children.first()
        response = self.client.get(reverse("birds:animal", args=[child.uuid]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["animal_list"]), 0)
        # one event for hatch, no pairings, no measurements
        self.assertEqual(len(response.context["event_list"]), 1)
        self.assertEqual(len(response.context["pairing_list"]), 0)
        self.assertEqual(len(response.context["animal_measurements"]), 0)


class EventViewTests(BaseColonyTest):
    def test_event_view_url_exists_at_desired_location(self):
        response = self.client.get("/birds/events/")
        self.assertEqual(response.status_code, 200)

    def test_event_view_contains_all_events(self):
        response = self.client.get(reverse("birds:events"))
        self.assertEqual(response.status_code, 200)
        # one event per animal + 3 events per parent for pairing start/end + 1
        # event for sire measurement
        #
        self.assertEqual(
            len(response.context["event_list"]),
            2 + self.n_children + self.n_eggs + 6 + 1,
        )

    def test_bird_events_404_invalid_bird_id(self):
        id = uuid.uuid4()
        response = self.client.get(reverse("birds:events", args=[id]))
        self.assertEqual(response.status_code, 404)

    def test_parent_event_list_at_correct_url(self):
        url = f"/birds/animals/{self.sire.uuid}/events/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_animal_event_view_contains_all_related_objects(self):
        response = self.client.get(reverse("birds:events", args=[self.sire.uuid]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["event_list"]), 5)
        response = self.client.get(reverse("birds:events", args=[self.dam.uuid]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["event_list"]), 4)

    def test_location_event_view(self):
        response = self.client.get(reverse("birds:events", args=[self.nest.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["event_list"]), 19)


class MeasurmentViewTests(BaseColonyTest):
    def test_measurement_view_url_exists_at_desired_location(self):
        response = self.client.get("/birds/measurements/")
        self.assertEqual(response.status_code, 200)

    def test_measurement_view_contains_all_events(self):
        response = self.client.get(reverse("birds:measurements"))
        self.assertEqual(response.status_code, 200)
        # one event for sire, none for dam
        self.assertEqual(len(response.context["measurement_list"]), 1)

    def test_bird_measurements_404_invalid_bird_id(self):
        id = uuid.uuid4()
        response = self.client.get(reverse("birds:measurements", args=[id]))
        self.assertEqual(response.status_code, 404)

    def test_parent_measurement_list_at_correct_url(self):
        url = f"/birds/animals/{self.sire.uuid}/measurements/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_animal_measurement_view_contains_all_related_objects(self):
        response = self.client.get(reverse("birds:measurements", args=[self.sire.uuid]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["measurement_list"]), 1)


class PairingViewTests(BaseColonyTest):
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

    def test_pairing_detail_404_invalid_id(self):
        n_pairings = Pairing.objects.count()
        response = self.client.get(reverse("birds:pairing", args=[n_pairings + 1]))
        self.assertEqual(response.status_code, 404)

    def test_pairing_detail_view_url_exists_at_desired_location(self):
        pairing_id = self.pairing.id
        url = f"/birds/pairings/{pairing_id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class LocationViewTests(BaseColonyTest):
    def test_location_list_url_exists_at_desired_location(self):
        response = self.client.get("/birds/locations/")
        self.assertEqual(response.status_code, 200)

    def test_location_list_contains_all_locations(self):
        response = self.client.get(reverse("birds:locations"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["location_list"]), 2)

    def test_location_detail_404_invalid_id(self):
        response = self.client.get(reverse("birds:location", args=[99]))
        self.assertEqual(response.status_code, 404)

    def test_location_detail_view_contains_all_living_birds(self):
        response = self.client.get(reverse("birds:location", args=[self.nest.id]))
        self.assertEqual(len(response.context["animal_list"]), 2 + self.n_children)


class UserViewTest(BaseColonyTest):
    def setUp(self):
        self.test_user1 = User.objects.create_user(
            username="testuser1", password="1X<ISRUkw+tuK"
        )
        self.test_user1.save()

    def test_user_list_url_exists_at_desired_location(self):
        response = self.client.get("/birds/users/")
        self.assertEqual(response.status_code, 200)

    def test_user_list_contains_all_users(self):
        response = self.client.get(reverse("birds:users"))
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            response.context["user_list"],
            [self.test_user1, models.get_sentinel_user()],
        )

    def test_user_detail_404_invalid_id(self):
        response = self.client.get(reverse("birds:user", args=[100223]))
        self.assertEqual(response.status_code, 404)

    def test_user_detail_view_contains_all_reserved_birds(self):
        species = Species.objects.get(pk=1)
        animal = Animal.objects.create(species=species, reserved_by=self.test_user1)
        response = self.client.get(reverse("birds:user", args=[self.test_user1.id]))
        self.assertCountEqual(response.context["animal_list"], [animal])


class BreedingReportTests(BaseColonyTest):
    def test_breeding_report_url_exists_at_desired_location(self):
        response = self.client.get("/birds/summary/breeding/")
        self.assertEqual(response.status_code, 200)

    def test_breeding_report_default_dates(self):
        response = self.client.get(reverse("birds:breeding-summary"))
        self.assertEqual(response.status_code, 200)
        dates = response.context["dates"]
        self.assertEqual(len(dates), 5)
        self.assertEqual(dates[0], today() - dt_days(4))
        self.assertEqual(dates[-1], today())

    def test_nest_check_list(self):
        nest_check = NestCheck.objects.create(
            entered_by=models.get_sentinel_user(),
            datetime=make_aware(datetime.datetime.now()),
            comments="much nesting",
        )
        response = self.client.get(reverse("birds:breeding-summary"))
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.context["checks"], [nest_check])

    def test_nest_report_bird_counts(self):
        response = self.client.get(reverse("birds:breeding-summary"))
        pairing = response.context["pairs"][0]
        self.assertEqual(pairing["pair"], self.pairing)
        for i, day in enumerate(pairing["counts"]):
            self.assertDictEqual(day, {"egg": i + 1})


class EventSummaryTests(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    @classmethod
    def setUpTestData(cls):
        # can't use BaseColonyTest because we need to make sure the events land
        # in specific months
        date = today()
        start_of_this_month = datetime.date(date.year, date.month, 1)
        end_of_last_month = start_of_this_month - dt_days(1)
        start_of_last_month = datetime.date(
            end_of_last_month.year, end_of_last_month.month, 1
        )
        laid_status = models.get_unborn_creation_event_type()
        hatch_status = models.get_birth_event_type()
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=1)
        cls.species = Species.objects.get(pk=1)
        birthday = date - dt_days(365)
        cls.sire = Animal.objects.create_with_event(
            species=cls.species,
            status=hatch_status,
            date=birthday,
            entered_by=user,
            location=location,
            sex=Animal.Sex.MALE,
            band_number=1,
        )
        cls.dam = Animal.objects.create_with_event(
            species=cls.species,
            status=hatch_status,
            date=birthday,
            entered_by=user,
            location=location,
            sex=Animal.Sex.FEMALE,
            band_number=2,
        )
        # move the parents in at the start of last month
        Pairing.objects.create_with_events(
            sire=cls.sire,
            dam=cls.dam,
            began_on=start_of_last_month,
            purpose="pairing",
            entered_by=user,
            location=location,
        )
        # add some eggs last month
        for i in range(4):
            _child = Animal.objects.create_from_parents(
                sire=cls.sire,
                dam=cls.dam,
                date=end_of_last_month - datetime.timedelta(days=i),
                status=laid_status,
                entered_by=user,
                location=location,
                description="behold the egg",
                sex=Animal.Sex.UNKNOWN_SEX,
                band_number=10 + i,
            )
        # make the eggs hatch this month
        for child in cls.sire.children.all():
            Event.objects.create(
                animal=child,
                status=hatch_status,
                date=start_of_this_month,
                entered_by=user,
            )

    def test_event_summary_url_exists_at_desired_location(self):
        date = today()
        response = self.client.get(f"/birds/summary/events/{date.year}/{date.month}/")
        self.assertEqual(response.status_code, 200)

    def test_event_summary_404_at_nonsense_dates(self):
        date = today()
        response = self.client.get(f"/birds/summary/events/{date.year}/13/")
        self.assertEqual(response.status_code, 404)
        response = self.client.get(f"/birds/summary/events/{date.year}/0/")
        self.assertEqual(response.status_code, 404)

    def test_event_summary_previous_month(self):
        date = today()
        start_of_this_month = datetime.date(date.year, date.month, 1)
        end_of_last_month = start_of_this_month - dt_days(1)
        response = self.client.get(
            reverse(
                "birds:event_summary",
                args=[end_of_last_month.year, end_of_last_month.month],
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            list(response.context["event_totals"]),
            [
                {"status__name": "moved", "count": 2},
                {"status__name": "laid", "count": 4},
            ],
        )
        self.assertEqual(len(response.context["bird_counts"]), 1)
        zf_counts = response.context["bird_counts"][0]
        self.assertEqual(zf_counts[0], self.species.common_name)
        self.assertListEqual(zf_counts[1], [("adult", {"M": 1, "F": 1})])

    def test_event_summary_current_month(self):
        date = today()
        response = self.client.get(
            reverse(
                "birds:event_summary",
                args=[date.year, date.month],
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            list(response.context["event_totals"]),
            [
                {"status__name": "hatched", "count": 4},
            ],
        )
        self.assertEqual(len(response.context["bird_counts"]), 1)
        zf_counts = response.context["bird_counts"][0]
        self.assertEqual(zf_counts[0], self.species.common_name)
        # the chicks age group will depend on how many days it's been since the
        # start of the month
        expected_chick_age_group = (
            self.species.age_set.filter(min_days__lt=date.day).first().name
        )
        self.assertListEqual(
            zf_counts[1],
            [("adult", {"M": 1, "F": 1}), (expected_chick_age_group, {"U": 4})],
        )


class SampleViewTests(TestCase):
    # fixture gives us a couple sample types and a sample location
    fixtures = ["bird_colony_starter_kit"]

    @classmethod
    def setUpTestData(cls):
        birthday = today() - dt_days(365)
        status = models.get_birth_event_type()
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=1)
        species = Species.objects.get(pk=1)
        band_color = Color.objects.get(pk=1)
        cls.bird = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=birthday,
            entered_by=user,
            location=location,
            sex=Animal.Sex.MALE,
            band_color=band_color,
            band_number=1,
        )
        cls.sample = Sample.objects.create(
            type=SampleType.objects.get(pk=1),
            animal=cls.bird,
            location=SampleLocation.objects.get(pk=1),
            attributes={"for testing": True},
            date=today(),
            collected_by=user,
        )

    def setUp(self):
        self.test_user1 = User.objects.create_user(
            username="testuser1", password="1X<ISRUkw+tuK"
        )
        self.test_user1.save()

    def test_sample_type_list_view(self):
        response = self.client.get(reverse("birds:sampletypes"))
        self.assertEqual(response.status_code, 200)

    def test_sample_list_view(self):
        response = self.client.get(reverse("birds:samples"))
        self.assertEqual(response.status_code, 200)
        all_samples = response.context["sample_list"]
        response = self.client.get(reverse("birds:samples", args=[self.bird.uuid]))
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(all_samples, response.context["sample_list"])

    def test_sample_list_404_invalid_bird_id(self):
        id = uuid.uuid4()
        response = self.client.get(reverse("birds:samples", args=[id]))
        self.assertEqual(response.status_code, 404)

    def test_detail_404_invalid_sample_id(self):
        id = uuid.uuid4()
        response = self.client.get(reverse("birds:sample", args=[id]))
        self.assertEqual(response.status_code, 404)

    def test_new_sample_redirect_if_not_logged_in(self):
        response = self.client.get(reverse("birds:new_sample", args=[self.bird.uuid]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_new_sample_initial_values(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("birds:new_sample", args=[self.bird.uuid]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"].initial["collected_by"], self.test_user1
        )

    def test_new_sample(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("birds:new_sample", args=[self.bird.uuid]),
            {
                "date": today() - dt_days(1),
                "location": self.sample.location.id,
                "type": self.sample.type.id,
                "collected_by": self.test_user1.id,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:animal", args=[self.bird.uuid]))
        self.assertEqual(self.bird.sample_set.count(), 2)
        self.assertEqual(self.sample.type.sample_set.count(), 2)


class NewAnimalFormViewTests(TestCase):
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
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("birds:new_animal"))
        self.assertEqual(response.status_code, 200)
        # TODO only status types that add should be given as options
        Status.objects.filter(adds=True)

    def test_transfer_creates_bird_and_events(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        status = Status.objects.get(name="transferred in")
        species = Species.objects.get(pk=1)
        location = Location.objects.get(pk=1)
        response = self.client.post(
            reverse("birds:new_animal"),
            {
                "acq_status": status.pk,
                "acq_date": today() - dt_days(10),
                "sex": "M",
                "species": species.pk,
                "banding_date": today(),
                "band_number": 10,
                "location": location.pk,
                "user": self.test_user1.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        animal = Animal.objects.with_dates().get(band_number=10)
        self.assertTrue(animal.alive)
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
            date=today() - dt_days(100),
            entered_by=self.test_user1,
            location=location,
            sex=Animal.Sex.MALE,
            band_number=1,
        )
        dam = Animal.objects.create_with_event(
            species=species,
            status=status,
            date=today() - dt_days(100),
            entered_by=self.test_user1,
            location=location,
            sex=Animal.Sex.FEMALE,
            band_number=2,
        )
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("birds:new_animal"),
            {
                "acq_status": status.pk,
                "acq_date": today() - dt_days(10),
                "sex": "U",
                "sire": sire.pk,
                "dam": dam.pk,
                "banding_date": today(),
                "band_number": 10,
                "location": location.pk,
                "user": self.test_user1.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        animal = Animal.objects.with_dates().get(band_number=10)
        self.assertTrue(animal.alive)
        # one event for transfer and one for banding
        self.assertEqual(animal.event_set.count(), 2)
        self.assertRedirects(response, reverse("birds:animal", args=[animal.uuid]))


class NewBandFormViewTests(TestCase):
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
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("birds:new_band", args=[self.animal.uuid]))
        self.assertEqual(response.status_code, 200)

    def test_update_band(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("birds:new_band", args=[self.animal.uuid]),
            {
                "banding_date": today(),
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


class UpdateSexFormViewTests(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    def setUp(self):
        # Create a user
        self.test_user1 = User.objects.create_user(
            username="testuser1", password="1X<ISRUkw+tuK"
        )
        self.test_user1.save()
        # Create an unsexed animal
        species = Species.objects.get(pk=1)
        self.animal = Animal.objects.create(species=species)

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse("birds:set_sex", args=[self.animal.uuid]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_initial_values_and_options(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("birds:set_sex", args=[self.animal.uuid]))
        self.assertEqual(response.status_code, 200)

    def test_404_invalid_bird_id(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        id = uuid.uuid4()
        response = self.client.get(reverse("birds:set_sex", args=[id]))
        self.assertEqual(response.status_code, 404)

    def test_set_sex(self):
        self.assertEqual(self.animal.sex, "U")
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("birds:set_sex", args=[self.animal.uuid]),
            {
                "date": today(),
                "sex": "M",
                "entered_by": self.test_user1.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:animal", args=[self.animal.uuid]))
        animal = Animal.objects.first()
        self.assertEqual(animal.sex, "M")
        self.assertEqual(animal.event_set.count(), 1)


class EventFormViewTests(TestCase):
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
            date=today() - dt_days(365),
            entered_by=models.get_sentinel_user(),
            location=Location.objects.get(pk=1),
            sex=Animal.Sex.MALE,
            band_color=Color.objects.get(pk=1),
            band_number=1,
        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse("birds:event_entry", args=[self.animal.uuid])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_initial_values_and_options(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(
            reverse("birds:event_entry", args=[self.animal.uuid])
        )
        self.assertEqual(response.status_code, 200)

    def test_add_event(self):
        self.assertEqual(self.animal.event_set.count(), 1)
        self.assertTrue(self.animal.alive())
        status = Status.objects.get(name=models.DEATH_EVENT_NAME)
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("birds:event_entry", args=[self.animal.uuid]),
            {
                "date": today(),
                "status": status.pk,
                "location": 1,
                "entered_by": self.test_user1.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:animal", args=[self.animal.uuid]))
        self.assertEqual(self.animal.event_set.count(), 2)
        self.assertFalse(self.animal.alive())

    def test_add_event_with_measurements(self):
        self.assertEqual(self.animal.event_set.count(), 1)
        self.assertEqual(self.animal.measurements().count(), 0)
        status = Status.objects.get(name=models.NOTE_EVENT_NAME)
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("birds:event_entry", args=[self.animal.uuid]),
            {
                "date": today(),
                "status": status.pk,
                "location": 1,
                "entered_by": self.test_user1.pk,
                "measurements-TOTAL_FORMS": 1,
                "measurements-INITIAL_FORMS": 1,
                "measurements-0-type": 1,
                "measurements-0-value": 20.0,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:animal", args=[self.animal.uuid]))
        self.assertEqual(self.animal.event_set.count(), 2)
        self.assertEqual(
            self.animal.measurements().count(),
            1,
            "wrong number of latest measurements for the animal",
        )
        event = self.animal.event_set.latest()
        self.assertEqual(
            event.measurements.count(),
            1,
            "wrong number of measurements associated with the event",
        )
        self.assertEqual(
            event.measurements.first().value,
            20.0,
            "not the expected measurement value",
        )

    def test_edit_event(self):
        event = self.animal.event_set.first()
        new_date = today()
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("birds:event_entry", args=[event.id]),
            {
                "date": new_date,
                "status": event.status.pk,
                "location": event.location.pk,
                "entered_by": self.test_user1.pk,
                "description": "updated",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:animal", args=[self.animal.uuid]))
        event = self.animal.event_set.first()
        self.assertEqual(event.date, new_date)
        self.assertEqual(event.description, "updated")

    def test_add_measurement_to_event(self):
        self.assertEqual(self.animal.event_set.count(), 1)
        self.assertEqual(self.animal.measurements().count(), 0)
        event = self.animal.event_set.first()
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("birds:event_entry", args=[event.id]),
            {
                "date": event.date,
                "status": event.status.pk,
                "location": event.location.pk,
                "entered_by": self.test_user1.pk,
                "measurements-TOTAL_FORMS": 1,
                "measurements-INITIAL_FORMS": 1,
                "measurements-0-type": 1,
                "measurements-0-value": 20.0,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:animal", args=[self.animal.uuid]))
        self.assertEqual(self.animal.event_set.count(), 1)
        self.assertEqual(self.animal.measurements().count(), 1)
        self.assertEqual(self.animal.event_set.first().measurements.first().value, 20.0)

    def test_remove_measurement_from_event(self):
        event = self.animal.event_set.first()
        measure = Measure.objects.get(pk=1)
        _ = Measurement.objects.create(event=event, type=measure, value=15.0)
        self.assertEqual(self.animal.event_set.count(), 1)
        self.assertEqual(self.animal.measurements().count(), 1)
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("birds:event_entry", args=[event.id]),
            {
                "date": event.date,
                "status": event.status.pk,
                "location": event.location.pk,
                "entered_by": self.test_user1.pk,
                "measurements-TOTAL_FORMS": 1,
                "measurements-INITIAL_FORMS": 1,
                "measurements-0-type": 1,
                "measurements-0-value": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:animal", args=[self.animal.uuid]))
        self.assertEqual(self.animal.event_set.count(), 1)
        self.assertEqual(self.animal.measurements().count(), 0)


class PairingTestCase(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    @classmethod
    def setUpTestData(cls):
        birthday = today() - dt_days(365)
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
            began_on=birthday + dt_days(80),
            purpose="old pairing",
            entered_by=user,
            location=location,
        )
        cls.pairing.close(
            ended_on=birthday + dt_days(120),
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


class PairingFormViewTests(PairingTestCase):
    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse("birds:new_pairing"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))
        response = self.client.get(reverse("birds:end_pairing", args=[self.pairing.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_initial_values_and_options(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("birds:new_pairing"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("sire", response.context["form"].initial)
        self.assertNotIn("dam", response.context["form"].initial)

    def test_initial_values_from_previous_pairing(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("birds:new_pairing", args=[self.pairing.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["sire"], self.sire)
        self.assertEqual(response.context["form"].initial["dam"], self.dam)

    def test_initial_values_ending_pairing(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        new_pairing = Pairing.objects.create_with_events(
            sire=self.sire,
            dam=self.dam,
            began_on=today() - dt_days(10),
            purpose="new pairing",
            entered_by=self.test_user1,
            location=Location.objects.get(pk=1),
        )
        response = self.client.get(reverse("birds:end_pairing", args=[new_pairing.pk]))
        self.assertEqual(response.status_code, 200)

    def test_create_pairing(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        location = Location.objects.filter(nest=True).first()
        response = self.client.post(
            reverse("birds:new_pairing"),
            {
                "sire": self.sire.pk,
                "dam": self.dam.pk,
                "began_on": today(),
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
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        new_pairing = Pairing.objects.create_with_events(
            sire=self.sire,
            dam=self.dam,
            began_on=today() - dt_days(10),
            purpose="new pairing",
            entered_by=self.test_user1,
            location=Location.objects.get(pk=1),
        )
        egg = new_pairing.create_egg(
            date=today() - dt_days(1), entered_by=self.test_user1
        )
        response = self.client.post(
            reverse("birds:end_pairing", args=[new_pairing.pk]),
            {
                "ended_on": today(),
                "location": 1,
                "entered_by": self.test_user1.pk,
                "comment": "testing",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:pairing", args=[new_pairing.pk]))
        eggs = new_pairing.eggs().existing()
        self.assertTrue(egg in eggs)

    def test_close_pairing_and_remove_unhatched(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        new_pairing = Pairing.objects.create_with_events(
            sire=self.sire,
            dam=self.dam,
            began_on=today() - dt_days(10),
            purpose="new pairing",
            entered_by=self.test_user1,
            location=Location.objects.get(pk=1),
        )
        _egg = new_pairing.create_egg(
            date=today() - dt_days(1), entered_by=self.test_user1
        )
        response = self.client.post(
            reverse("birds:end_pairing", args=[new_pairing.pk]),
            {
                "ended_on": today(),
                "location": 1,
                "remove_unhatched": "on",
                "entered_by": self.test_user1.pk,
                "comment": "testing",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:pairing", args=[new_pairing.pk]))
        eggs = new_pairing.eggs().existing()
        self.assertEqual(eggs.count(), 0)


class NewPairingEggFormTests(PairingTestCase):
    def test_initial_values_and_options(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(
            reverse("birds:new_pairing_egg", args=[self.pairing.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_cannot_add_egg_to_nonexistent_pairing(self):
        n_pairings = Pairing.objects.count()
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(
            reverse("birds:new_pairing_egg", args=[n_pairings + 1])
        )
        self.assertEqual(response.status_code, 404)

    def test_add_egg_to_pairing(self):
        pairing_id = self.pairing.id
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("birds:new_pairing_egg", args=[pairing_id]),
            {"date": self.pairing.ended_on - dt_days(1), "user": self.test_user1.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:pairing", args=[pairing_id]))
        eggs = self.pairing.eggs().existing()
        self.assertEqual(eggs.count(), 1)

    def test_cannot_add_egg_to_pairing_before_start(self):
        pairing_id = self.pairing.id
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("birds:new_pairing_egg", args=[pairing_id]),
            {"date": self.pairing.began_on - dt_days(1), "user": self.test_user1.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "birds/pairing_egg_entry.html")
        eggs = self.pairing.eggs().existing()
        self.assertEqual(eggs.count(), 0)


class NewPairingEventFormTests(PairingTestCase):
    def test_initial_values_and_options(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(
            reverse("birds:new_pairing_event", args=[self.pairing.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_cannot_add_event_to_nonexistent_pairing(self):
        n_pairings = Pairing.objects.count()
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(
            reverse("birds:new_pairing_event", args=[n_pairings + 1])
        )
        self.assertEqual(response.status_code, 404)

    def test_cannot_add_event_before_or_after_pairing(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        n_events = self.pairing.events().count()
        move_status = Status.objects.get(name=models.MOVED_EVENT_NAME)
        response = self.client.post(
            reverse("birds:new_pairing_event", args=[self.pairing.id]),
            {
                "date": self.pairing.began_on - dt_days(1),
                "entered_by": self.test_user1.pk,
                "location": 1,
                "status": move_status.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "birds/pairing_event_entry.html")
        self.assertEqual(self.pairing.events().count(), n_events)
        response = self.client.post(
            reverse("birds:new_pairing_event", args=[self.pairing.id]),
            {
                "date": self.pairing.ended_on + dt_days(1),
                "entered_by": self.test_user1.pk,
                "location": 1,
                "status": move_status.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "birds/pairing_event_entry.html")
        self.assertEqual(self.pairing.events().count(), n_events)

    def test_add_event_to_pairing_with_chicks(self):
        # add a kid
        child = self.pairing.create_egg(
            date=self.pairing.began_on, entered_by=self.test_user1
        )
        # hatch the egg
        hatch_status = models.get_birth_event_type()
        hatch_date = self.pairing.began_on + dt_days(14)
        move_status = Status.objects.get(name=models.MOVED_EVENT_NAME)
        _ = Event.objects.create(
            animal=child,
            date=hatch_date,
            entered_by=self.test_user1,
            status=hatch_status,
        )
        # 2 birthdays, pairing open and close, egg laid and hatched
        self.assertEqual(self.pairing.events().count(), 6)
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        # first add an event before the egg hatches - should only affect the parents
        event_date = hatch_date - dt_days(1)
        response = self.client.post(
            reverse("birds:new_pairing_event", args=[self.pairing.id]),
            {
                "date": event_date,
                "entered_by": self.test_user1.pk,
                "location": 1,
                "status": move_status.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:pairing", args=[self.pairing.id]))
        # adds two events, one for each parent
        self.assertEqual(self.pairing.events().count(), 8)
        self.assertEqual(
            self.pairing.events()
            .filter(date=event_date, status=move_status.pk)
            .count(),
            2,
        )
        # next add an event after the egg hatches but before pairing ends - should affect all 3 birds
        event_date = self.pairing.ended_on - dt_days(1)
        response = self.client.post(
            reverse("birds:new_pairing_event", args=[self.pairing.id]),
            {
                "date": event_date,
                "entered_by": self.test_user1.pk,
                "location": 1,
                "status": move_status.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:pairing", args=[self.pairing.id]))
        # adds two events, one for each parent and one for the chick
        self.assertEqual(self.pairing.events().count(), 11)
        self.assertEqual(
            self.pairing.events()
            .filter(date=event_date, status=move_status.pk)
            .count(),
            3,
        )

    def test_add_event_to_pairing(self):
        # add a kid
        child = self.pairing.create_egg(
            date=self.pairing.began_on, entered_by=self.test_user1
        )
        # hatch the egg
        hatch_status = models.get_birth_event_type()
        move_status = Status.objects.get(name=models.MOVED_EVENT_NAME)
        _ = Event.objects.create(
            animal=child,
            date=self.pairing.began_on + dt_days(14),
            entered_by=self.test_user1,
            status=hatch_status,
        )
        # 2 birthdays, pairing open and close, egg laid and hatched
        self.assertEqual(self.pairing.events().count(), 6)
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        event_date = self.pairing.ended_on - dt_days(1)
        response = self.client.post(
            reverse("birds:new_pairing_event", args=[self.pairing.id]),
            {
                "date": event_date,
                "entered_by": self.test_user1.pk,
                "location": 1,
                "status": move_status.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:pairing", args=[self.pairing.id]))
        # add three events, one for each bird
        self.assertEqual(self.pairing.events().count(), 9)
        self.assertEqual(
            self.pairing.events()
            .filter(date=event_date, status=move_status.pk)
            .count(),
            3,
        )


class BreedingCheckFormViewTests(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    @classmethod
    def setUpTestData(cls):
        birthday = today() - dt_days(365)
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
        cls.pairing = Pairing.objects.create_with_events(
            sire=cls.sire,
            dam=cls.dam,
            began_on=today() - dt_days(10),
            purpose="testing",
            entered_by=user,
            location=cls.nest,
        )

    def setUp(self):
        # Create a user
        self.test_user1 = User.objects.create_user(
            username="testuser1", password="1X<ISRUkw+tuK"
        )
        self.test_user1.save()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse("birds:breeding-check"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_initial_empty_nest(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("birds:breeding-check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["nest_formset"]), 1)
        form = response.context["nest_formset"][0]
        self.assertDictEqual(
            form.initial,
            {"pairing": self.pairing, "location": self.nest, "eggs": 0, "chicks": 0},
        )

    def test_initial_nest_with_egg_and_chick(self):
        user = models.get_sentinel_user()
        status_laid = models.get_unborn_creation_event_type()
        status_hatched = models.get_birth_event_type()
        chick = Animal.objects.create_from_parents(
            sire=self.sire,
            dam=self.dam,
            date=today() - dt_days(9),
            status=status_laid,
            entered_by=user,
            location=self.nest,
        )
        Event.objects.create(
            animal=chick,
            status=status_hatched,
            date=today(),
            entered_by=user,
        )
        Animal.objects.create_from_parents(
            sire=self.sire,
            dam=self.dam,
            date=today(),
            status=status_laid,
            entered_by=user,
            location=self.nest,
        )
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("birds:breeding-check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["nest_formset"]), 1)
        form = response.context["nest_formset"][0]
        self.assertDictEqual(
            form.initial,
            {"pairing": self.pairing, "location": self.nest, "eggs": 1, "chicks": 1},
        )

    def test_includes_open_pairings(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("birds:breeding-check"))
        formset = response.context["nest_formset"]
        self.assertEqual(len(formset), 1)
        self.assertEqual(formset[0].initial["pairing"], self.pairing)

    def test_omits_closed_pairings(self):
        self.pairing.close(today() - dt_days(1), entered_by=models.get_sentinel_user())
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("birds:breeding-check"))
        formset = response.context["nest_formset"]
        self.assertEqual(len(formset), 0)

    def test_error_returns_original_form(self):
        data = {
            "nests-TOTAL_FORMS": 1,
            "nests-INITIAL_FORMS": 1,
            "nests-0-location": self.nest.pk,
            "nests-0-pairing": self.pairing.pk,
            "nests-0-eggs": 0,
            "nests-0-chicks": 1,
        }
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(reverse("birds:breeding-check"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "birds/breeding_check.html")

    def test_form_with_no_changes(self):
        data = {
            "nests-TOTAL_FORMS": 1,
            "nests-INITIAL_FORMS": 1,
            "nests-0-location": self.nest.pk,
            "nests-0-pairing": self.pairing.pk,
            "nests-0-eggs": 0,
            "nests-0-chicks": 0,
        }
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(reverse("birds:breeding-check"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "birds/breeding_check_confirm.html")
        form = response.context["nest_formset"][0]
        self.assertFalse(form.cleaned_data["hatched_eggs"].exists())
        self.assertCountEqual(form.cleaned_data["lost_eggs"], [])
        self.assertEqual(form.cleaned_data["added_eggs"], 0)
        self.assertCountEqual(form.change_summary(), ["no changes"])

    def test_add_egg_with_form(self):
        data = {
            "nests-TOTAL_FORMS": 1,
            "nests-INITIAL_FORMS": 1,
            "nests-0-location": self.nest.pk,
            "nests-0-pairing": self.pairing.pk,
            "nests-0-eggs": 1,
            "nests-0-chicks": 0,
        }
        user_data = {
            "user-entered_by": models.get_sentinel_user().pk,
            "user-confirmed": "on",
        }
        # submit the form with confirmation; computed changes tested in the form
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(reverse("birds:breeding-check"), data | user_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:breeding-summary"))
        eggs = self.sire.children.with_dates().unhatched()
        self.assertEqual(eggs.count(), 1)
        egg = eggs.first()
        self.assertEqual(egg.sire(), self.sire)
        self.assertEqual(egg.dam(), self.dam)
        self.assertEqual(egg.laid_on, today())
        self.assertEqual(egg.age_group(), "egg")
        nest_checks = NestCheck.objects.all()
        self.assertEqual(nest_checks.count(), 1)

    def test_hatch_egg_with_form(self):
        user = models.get_sentinel_user()
        status_laid = models.get_unborn_creation_event_type()
        child_1 = Animal.objects.create_from_parents(
            sire=self.sire,
            dam=self.dam,
            date=today() - dt_days(1),
            status=status_laid,
            entered_by=user,
            location=self.nest,
        )
        data = {
            "nests-TOTAL_FORMS": 1,
            "nests-INITIAL_FORMS": 1,
            "nests-0-location": self.nest.pk,
            "nests-0-pairing": self.pairing.pk,
            "nests-0-eggs": 0,
            "nests-0-chicks": 1,
        }
        user_data = {
            "user-entered_by": models.get_sentinel_user().pk,
            "user-confirmed": "on",
        }
        # submit the form with confirmation; computed changes tested in the form
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(reverse("birds:breeding-check"), data | user_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("birds:breeding-summary"))
        children = self.sire.children.with_dates().alive()
        self.assertEqual(children.count(), 1)
        child = children.first()
        self.assertEqual(child, child_1)
        self.assertEqual(child.born_on, today())
        self.assertEqual(child.age_group(), "hatchling")
        nest_checks = NestCheck.objects.all()
        self.assertEqual(nest_checks.count(), 1)


class BreedingCheckFormNewPairingViewTests(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    @classmethod
    def setUpTestData(cls):
        birthday = today() - dt_days(365)
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

    def setUp(self):
        # Create a user
        self.test_user1 = User.objects.create_user(
            username="testuser1", password="1X<ISRUkw+tuK"
        )
        self.test_user1.save()

    def test_nest_check_same_day(self):
        user = models.get_sentinel_user()
        pairing = Pairing.objects.create_with_events(
            sire=self.sire,
            dam=self.dam,
            began_on=today(),
            purpose="testing",
            entered_by=user,
            location=self.nest,
        )
        data = {
            "nests-TOTAL_FORMS": 1,
            "nests-INITIAL_FORMS": 1,
            "nests-0-location": self.nest.pk,
            "nests-0-pairing": pairing.pk,
            "nests-0-eggs": 0,
            "nests-0-chicks": 0,
        }
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(reverse("birds:breeding-check"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "birds/breeding_check_confirm.html")
        form = response.context["nest_formset"][0]
        self.assertFalse(form.cleaned_data["hatched_eggs"].exists())
        self.assertCountEqual(form.cleaned_data["lost_eggs"], [])
        self.assertEqual(form.cleaned_data["added_eggs"], 0)
        self.assertCountEqual(form.change_summary(), ["no changes"])


# Views we don't test:
# animal_genealogy - covered well by the model tests
# reservation_entry - TODO
