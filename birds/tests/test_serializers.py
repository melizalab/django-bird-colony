# -*- coding: utf-8 -*-
# -*- mode: python -*-
import datetime
import warnings

from django.test import TestCase

from birds import models
from birds.models import Animal, Location, Measure, Species
from birds.serializers import (
    EventSerializer,
)

warnings.filterwarnings("error")


class EventSerializerTests(TestCase):
    fixtures = ["bird_colony_starter_kit"]

    def setUp(self):
        self.species = Species.objects.get(pk=1)
        self.bird = Animal.objects.create(species=self.species, sex=Animal.Sex.MALE)
        self.user = models.get_sentinel_user()
        self.location = Location.objects.get(pk=2)

    def test_event_serializer_no_measurements(self):
        # Test creating an event with no measurements
        event_data = {
            "animal": self.bird.uuid,
            "date": datetime.date.today(),
            "status": models.NOTE_EVENT_NAME,
            "location": self.location.name,
            "description": "Test event without measurements",
            "measurements": [],
        }

        serializer = EventSerializer(data=event_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        event = serializer.save(entered_by=self.user)
        self.assertEqual(event.measurements.count(), 0)

    def test_event_serializer_with_measurements(self):
        # Test creating an event with no measurements
        measure = Measure.objects.get(pk=1)
        event_data = {
            "animal": self.bird.uuid,
            "date": datetime.date.today(),
            "status": models.NOTE_EVENT_NAME,
            "location": self.location.name,
            "description": "Test event without measurements",
            "measurements": [{"measure": measure.name, "value": 1234}],
        }

        serializer = EventSerializer(data=event_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        event = serializer.save(entered_by=self.user)
        self.assertEqual(event.measurements.count(), 1)

    def test_update_event_with_measurements(self):
        measure = Measure.objects.get(pk=1)
        event = self.bird.add_measurements(
            [],
            date=datetime.date.today(),
            entered_by=self.user,
        )
        new_event_data = {
            "measurements": [{"measure": measure.name, "value": 1234}],
        }
        serializer = EventSerializer(event, data=new_event_data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        event = serializer.save()
        self.assertEqual(event.measurements.count(), 1)
