# -*- coding: utf-8 -*-
# -*- mode: python -*-
from __future__ import unicode_literals

from rest_framework import serializers
from birds.models import Animal, Parent, Event, Color, Species, Status, Location


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
    alive = serializers.BooleanField(required=False)
    acquisition_event = serializers.SlugRelatedField(read_only=True, slug_field='date')

    class Meta:
        model = Animal
        fields = ("uuid", "name", "sire", "dam", "sex", "alive", "plumage", "acquisition_event")


class AnimalDetailSerializer(AnimalSerializer):
    species = serializers.StringRelatedField()
    band_color = serializers.StringRelatedField()
    plumage = serializers.StringRelatedField()
    reserved_by = serializers.StringRelatedField()
    sire = serializers.PrimaryKeyRelatedField(read_only=True)
    dam = serializers.PrimaryKeyRelatedField(read_only=True)
    alive = serializers.BooleanField(required=False)
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
