# -*- coding: utf-8 -*-
# -*- mode: python -*-
import datetime

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

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


class ApiViewTests(APITestCase):
    fixtures = ["bird_colony_starter_kit"]

    def test_bird_list_view(self):
        species = Species.objects.get(pk=1)
        event_type = models.get_birth_event_type()
        age = datetime.timedelta(days=5)
        birthday = datetime.date.today() - age
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=2)
        bird_1 = Animal.objects.create_with_event(
            species=species,
            date=birthday,
            status=event_type,
            entered_by=user,
            location=location,
            sex=Animal.Sex.MALE,
        )
        bird_2 = Animal.objects.create_with_event(
            species=species,
            date=birthday,
            status=event_type,
            entered_by=user,
            location=location,
            sex=Animal.Sex.FEMALE,
        )
        response = self.client.get(reverse("birds:animals_api"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(
            {bird["uuid"] for bird in response.data},
            {str(bird_1.uuid), str(bird_2.uuid)},
        )

    def test_bird_detail_view(self):
        species = Species.objects.get(pk=1)
        event_type = models.get_birth_event_type()
        age = datetime.timedelta(days=5)
        birthday = datetime.date.today() - age
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=2)
        bird = Animal.objects.create_with_event(
            species=species,
            date=birthday,
            status=event_type,
            entered_by=user,
            location=location,
            sex=Animal.Sex.MALE,
        )
        response = self.client.get(reverse("birds:animal_api", args=[bird.uuid]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictContainsSubset(
            {
                "uuid": str(bird.uuid),
                "species": species.common_name,
                "sex": Animal.Sex.MALE,
                "sire": None,
                "dam": None,
                "age_days": age.days,
                "last_location": location.name,
                "alive": True,
            },
            response.data,
        )

    def test_bird_with_parents_detail_view(self):
        species = Species.objects.get(pk=1)
        sire = Animal.objects.create(species=species, sex=Animal.Sex.MALE)
        dam = Animal.objects.create(species=species, sex=Animal.Sex.FEMALE)
        event_type = models.get_birth_event_type()
        age = datetime.timedelta(days=5)
        birthday = datetime.date.today() - age
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=2)
        bird = Animal.objects.create_from_parents(
            sire=sire,
            dam=dam,
            date=birthday,
            status=event_type,
            entered_by=user,
            location=location,
            description="testing 123",
            sex=Animal.Sex.FEMALE,
        )
        response = self.client.get(reverse("birds:animal_api", args=[bird.uuid]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictContainsSubset(
            {
                "uuid": str(bird.uuid),
                "species": species.common_name,
                "sex": Animal.Sex.FEMALE,
                "sire": sire.uuid,
                "dam": dam.uuid,
                "age_days": age.days,
                "last_location": location.name,
                "alive": True,
            },
            response.data,
        )

    def test_bird_children_list_view(self):
        species = Species.objects.get(pk=1)
        sire = Animal.objects.create(species=species, sex=Animal.Sex.MALE)
        dam = Animal.objects.create(species=species, sex=Animal.Sex.FEMALE)
        event_type = models.get_birth_event_type()
        age = datetime.timedelta(days=5)
        birthday = datetime.date.today() - age
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=2)
        birds = [
            Animal.objects.create_from_parents(
                sire=sire,
                dam=dam,
                date=birthday,
                status=event_type,
                entered_by=user,
                location=location,
            )
            for _ in range(2)
        ]
        response = self.client.get(reverse("birds:animal_api", args=[sire.uuid]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(reverse("birds:children_api", args=[sire.uuid]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(
            {bird["uuid"] for bird in response.data}, {str(bird.uuid) for bird in birds}
        )
        response = self.client.get(reverse("birds:animal_api", args=[dam.uuid]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(reverse("birds:children_api", args=[dam.uuid]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(
            {bird["uuid"] for bird in response.data}, {str(bird.uuid) for bird in birds}
        )
        bird_1 = birds[0]
        response = self.client.get(reverse("birds:animal_api", args=[bird_1.uuid]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(reverse("birds:children_api", args=[bird_1.uuid]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_event_list_view(self):
        species = Species.objects.get(pk=1)
        event_type = models.get_birth_event_type()
        age = datetime.timedelta(days=5)
        birthday = datetime.date.today() - age
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=2)
        bird = Animal.objects.create_with_event(
            species=species,
            date=birthday,
            status=event_type,
            entered_by=user,
            location=location,
            sex=Animal.Sex.MALE,
        )
        response = self.client.get(reverse("birds:events_api"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertDictContainsSubset(
            {
                "animal": bird.uuid,
                "date": str(birthday),
                "status": event_type.name,
                "location": location.name,
            },
            response.data[0],
        )

    def test_pedigree_view(self):
        species = Species.objects.get(pk=1)
        sire = Animal.objects.create(species=species, sex=Animal.Sex.MALE)
        dam = Animal.objects.create(species=species, sex=Animal.Sex.FEMALE)
        event_type = models.get_birth_event_type()
        age = datetime.timedelta(days=5)
        birthday = datetime.date.today() - age
        user = models.get_sentinel_user()
        location = Location.objects.get(pk=2)
        birds = [
            Animal.objects.create_from_parents(
                sire=sire,
                dam=dam,
                date=birthday,
                status=event_type,
                entered_by=user,
                location=location,
            )
            for _ in range(2)
        ]
        response = self.client.get(reverse("birds:pedigree_api"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        uuids = {bird["uuid"] for bird in response.data}
        # needs more testing
