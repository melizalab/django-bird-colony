# -*- coding: utf-8 -*-
# -*- mode: python -*-
import datetime

from rest_framework import serializers

from birds.models import Animal, Event, Measure, Measurement, Status


class AgeSerializer(serializers.Field):
    """Serialize age into days"""

    def to_representation(self, value: datetime.timedelta):
        return value.days


class AnimalSerializer(serializers.ModelSerializer):
    species = serializers.StringRelatedField()
    band_color = serializers.StringRelatedField()
    plumage = serializers.StringRelatedField()
    reserved_by = serializers.StringRelatedField()
    sire = serializers.PrimaryKeyRelatedField(read_only=True)
    dam = serializers.PrimaryKeyRelatedField(read_only=True)
    alive = serializers.BooleanField(required=False)

    class Meta:
        model = Animal
        fields = (
            "name",
            "uuid",
            "species",
            "sex",
            "plumage",
            "band_color",
            "band_number",
            "sire",
            "dam",
            "alive",
            "reserved_by",
        )


class AnimalPedigreeSerializer(serializers.ModelSerializer):
    sire = serializers.StringRelatedField()
    dam = serializers.StringRelatedField()
    plumage = serializers.StringRelatedField()
    alive = serializers.BooleanField()
    acquired_on = serializers.DateField(read_only=True)

    class Meta:
        model = Animal
        fields = (
            "uuid",
            "name",
            "sire",
            "dam",
            "sex",
            "alive",
            "plumage",
            "acquired_on",
        )


class PedigreeRequestSerializer(serializers.Serializer):
    """Used to parse requests for pedigree"""

    restrict = serializers.BooleanField(default=True)


class AnimalDetailSerializer(AnimalSerializer):
    species = serializers.StringRelatedField()
    band_color = serializers.StringRelatedField()
    plumage = serializers.StringRelatedField()
    reserved_by = serializers.StringRelatedField()
    sire = serializers.PrimaryKeyRelatedField(read_only=True)
    dam = serializers.PrimaryKeyRelatedField(read_only=True)
    age_days = AgeSerializer(source="age", read_only=True)
    alive = serializers.BooleanField()
    last_location = serializers.StringRelatedField()

    class Meta:
        model = Animal
        fields = (
            "name",
            "uuid",
            "species",
            "sex",
            "plumage",
            "band_color",
            "band_number",
            "sire",
            "dam",
            "reserved_by",
            "age_days",
            "alive",
            "last_location",
            "attributes",
        )


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ("name", "count")


class MeasurementSerializer(serializers.ModelSerializer):
    event_id = serializers.PrimaryKeyRelatedField(
        source="event", queryset=Event.objects.all()
    )
    animal = serializers.PrimaryKeyRelatedField(source="event.animal", read_only=True)
    date = serializers.DateField(source="event.date", read_only=True)
    measure = serializers.SlugRelatedField(
        source="type", slug_field="name", queryset=Measure.objects.all()
    )
    units = serializers.CharField(source="type.unit_sym", read_only=True)

    class Meta:
        model = Measurement
        fields = ("event_id", "animal", "date", "measure", "value", "units")


class EventSerializer(serializers.ModelSerializer):
    animal = serializers.PrimaryKeyRelatedField(
        read_only=False, queryset=Animal.objects.all()
    )
    entered_by = serializers.StringRelatedField()
    location = serializers.StringRelatedField()
    status = serializers.StringRelatedField()

    class Meta:
        model = Event
        fields = ("animal", "date", "status", "location", "description", "entered_by")
