# -*- coding: utf-8 -*-
# -*- mode: python -*-
from __future__ import unicode_literals

from rest_framework import serializers
from django.contrib.auth.models import User
from birds.models import Animal, Parent, Event, Color, Species, Status, Location


class AnimalUUIDField(serializers.RelatedField):
    def to_representation(self, value):
        return str(value.uuid)


class AnimalSerializer(serializers.ModelSerializer):
    species = serializers.StringRelatedField()
    band_color = serializers.StringRelatedField()
    reserved_by = serializers.StringRelatedField()
    parents = serializers.PrimaryKeyRelatedField(many=True, read_only=False,
                                                 queryset=Animal.objects.all())

    def create(self, validated_data):
        # can't add the parents directly
        d = validated_data.copy()
        parents = d.pop("parents")
        animal = Animal.objects.create(**d)
        for p in parents:
            Parent.objects.create(child=animal, parent=p)
        return animal

    class Meta:
        model = Animal
        fields = ('name', 'uuid', 'species', 'sex', 'band_color', 'band_number',
                  'parents', 'reserved_by',)


class AnimalDetailSerializer(AnimalSerializer):
    last_location = serializers.StringRelatedField()
    class Meta:
        model = Animal
        fields = ('name', 'uuid', 'species', 'sex', 'band_color', 'band_number',
                  'parents', 'reserved_by', "age_days", "alive", "last_location",)


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
