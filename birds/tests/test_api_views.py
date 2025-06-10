# -*- mode: python -*-
import datetime
import warnings

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from birds import models
from birds.models import (
    Animal,
    Location,
    Measure,
    Measurement,
    Species,
)

warnings.filterwarnings("error")
User = get_user_model()


class ApiViewTests(APITestCase):
    fixtures = ["bird_colony_starter_kit"]
    maxDiff = None

    def setUp(self):
        self.species = Species.objects.get(pk=1)
        self.sire = Animal.objects.create(species=self.species, sex=Animal.Sex.MALE)
        self.dam = Animal.objects.create(species=self.species, sex=Animal.Sex.FEMALE)
        self.event_type = models.get_birth_event_type()
        self.age = datetime.timedelta(days=5)
        self.birthday = datetime.date.today() - self.age
        self.user = models.get_sentinel_user()
        self.location = Location.objects.get(pk=2)
        self.children = [
            Animal.objects.create_from_parents(
                sire=self.sire,
                dam=self.dam,
                date=self.birthday,
                status=self.event_type,
                entered_by=self.user,
                location=self.location,
                sex=Animal.Sex.MALE,
            )
            for _ in range(2)
        ]
        self.all_birds = [*self.children, self.sire, self.dam]
        self.uuids = {str(bird.uuid) for bird in self.all_birds}
        self.n_birds = len(self.children) + 2
        self.user = User.objects.create_user(username="testuser1", password="testpass")

    def test_bird_list_view(self):
        response = self.client.get(reverse("birds:animals_api"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), self.n_birds)
        self.assertEqual({bird["uuid"] for bird in response.data}, self.uuids)

    def test_bird_detail_view(self):
        for child in self.children:
            response = self.client.get(reverse("birds:animal_api", args=[child.uuid]))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertDictEqual(
                response.data,
                response.data
                | {
                    "uuid": str(child.uuid),
                    "species": self.species.common_name,
                    "sex": Animal.Sex.MALE,
                    "sire": self.sire.uuid,
                    "dam": self.dam.uuid,
                    "age_days": self.age.days,
                    "last_location": self.location.name,
                    "alive": True,
                },
            )
        for parent in (self.sire, self.dam):
            response = self.client.get(reverse("birds:animal_api", args=[parent.uuid]))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertDictEqual(
                response.data,
                response.data
                | {
                    "uuid": str(parent.uuid),
                    "species": self.species.common_name,
                    "sex": parent.sex,
                    "sire": None,
                    "dam": None,
                    "age_days": None,
                    "last_location": None,
                    "alive": False,
                },
            )

    def test_bird_children_list_view(self):
        response = self.client.get(reverse("birds:children_api", args=[self.sire.uuid]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(
            {bird["uuid"] for bird in response.data},
            {str(child.uuid) for child in self.children},
        )
        response = self.client.get(reverse("birds:children_api", args=[self.dam.uuid]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(
            {bird["uuid"] for bird in response.data},
            {str(child.uuid) for child in self.children},
        )
        for child in self.children:
            response = self.client.get(reverse("birds:children_api", args=[child.uuid]))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 0)

    def test_event_list_view(self):
        response = self.client.get(reverse("birds:events_api"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        for ret in response.data:
            self.assertDictEqual(
                ret,
                ret
                | {
                    "date": str(self.birthday),
                    "status": self.event_type.name,
                    "location": self.location.name,
                },
            )

    def test_event_list_with_animal(self):
        response = self.client.get(
            reverse("birds:events_api", args=[self.children[0].uuid])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        ret = response.data[0]
        self.assertDictEqual(
            ret,
            ret
            | {
                "date": str(self.birthday),
                "status": self.event_type.name,
                "location": self.location.name,
            },
        )

    def test_event_list_with_measurements_view(self):
        bird = self.sire
        date = datetime.date.today()
        value = 12.1
        measure = Measure.objects.get(name="weight")
        _ = bird.add_measurements([(measure, value)], date=date, entered_by=self.user)
        response = self.client.get(reverse("birds:events_api"), data={"date": date})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        ret = response.data[0]["measurements"]
        self.assertCountEqual(
            ret, [{"measure": "weight", "value": value, "units": "g"}]
        )

    def test_create_event_requires_login(self):
        response = self.client.post(
            reverse("birds:events_api"),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_event(self):
        bird = self.sire
        date = datetime.date.today()
        value = 12.1
        measure = Measure.objects.get(name="weight")
        self.client.login(username="testuser1", password="testpass")
        response = self.client.post(
            reverse("birds:events_api"),
            {
                "animal": bird.uuid,
                "date": date,
                "status": "note",
                "measurements": [
                    {
                        "measure": measure.name,
                        "value": value,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_event(self):
        bird = self.children[0]
        event = bird.event_set.first()
        value = 12.1
        measure = Measure.objects.get(name="weight")
        self.client.login(username="testuser1", password="testpass")
        measurement = {
            "measure": measure.name,
            "value": value,
        }
        response = self.client.patch(
            reverse("birds:event_api", args=[event.id]),
            {"measurements": [measurement]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(
            response.data["measurements"][0],
            response.data["measurements"][0] | measurement,
        )

    def test_measurement_list_view(self):
        bird = self.children[0]
        event = bird.event_set.first()
        measure = Measure.objects.get(name="weight")
        measurement = Measurement.objects.create(
            event=event, type=measure, value=10.123
        )
        response = self.client.get(reverse("birds:measurements_api"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        ret = response.data[0]
        self.assertDictEqual(
            ret,
            ret
            | {
                "animal": bird.uuid,
                "date": str(event.date),
                "measure": measure.name,
                "value": measurement.value,
                "units": measure.unit_sym,
            },
        )

    def test_pedigree_view(self):
        response = self.client.get(reverse("birds:pedigree_api"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertIsInstance(response, StreamingHttpResponse)
        # data = list(response.streaming_content)
        # pedigree will include parents even though they aren't alive
        self.assertEqual(len(response.data), self.n_birds)
        self.assertEqual({d["uuid"] for d in response.data}, self.uuids)
        for bird in response.data:
            self.assertEqual(bird["inbreeding"], 0.0)
        # needs more testing - should be in creation order, with correct relationships
