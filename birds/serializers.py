# -*- coding: utf-8 -*-
# -*- mode: python -*-
from __future__ import unicode_literals

from rest_framework import serializers
from django.contrib.auth.models import User
from birds.models import Animal, Parent, Event, Color, Species, Status, Location


class AnimalSerializer(serializers.ModelSerializer):
    species = serializers.StringRelatedField()
    band_color = serializers.StringRelatedField()
    reserved_by = serializers.StringRelatedField()
    sire = serializers.PrimaryKeyRelatedField(read_only=True)
    dam = serializers.PrimaryKeyRelatedField(read_only=True)
    alive = serializers.BooleanField(required=False)

    class Meta:
        model = Animal
        fields = ('name', 'uuid', 'species', 'sex', 'band_color', 'band_number',
                  'sire', 'dam', 'alive', 'reserved_by',)


class AnimalDetailSerializer(AnimalSerializer):
    last_location = serializers.StringRelatedField()

    class Meta:
        model = Animal
        fields = ('name', 'uuid', 'species', 'sex', 'band_color', 'band_number',
                  'sire', 'dam', 'reserved_by', "age_days", "alive", "last_location",)


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ('name', 'count', 'category')


class EventSerializer(serializers.ModelSerializer):
    animal = serializers.PrimaryKeyRelatedField(read_only=False,
                                                queryset=Animal.objects.all())
    entered_by = serializers.StringRelatedField()
    location = serializers.StringRelatedField()
    status = serializers.StringRelatedField()

    class Meta:
        model = Event
        fields = ('animal', 'date', 'status', 'location', 'description', 'entered_by')
