# -*- coding: utf-8 -*-
# -*- mode: python -*-
from __future__ import unicode_literals

from rest_framework import serializers
from django.contrib.auth.models import User
from birds.models import Animal, Parent, Event, Color, Species, Status, Location, Recording

# class ColorSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Color
#         fields = ('name',)


# class SpeciesSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Species
#         fields = ('code',)


# class UserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ('name',)

class AnimalUUIDField(serializers.RelatedField):
    def to_representation(self, value):
        return str(value.uuid)


class AnimalSerializer(serializers.ModelSerializer):
    #species = SpeciesSerializer()
    #band_color = serializers.StringRelatedField()#ColorSerializer()
    #reserved_by = serializers.StringRelatedField()#queryset=User.objects.all(), read_only=False)
    parents = serializers.PrimaryKeyRelatedField(many=True, read_only=False, queryset=Animal.objects.all())

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
        fields = ('uuid', 'species', 'sex', 'band_color', 'band_number', 'parents', 'reserved_by', 'created')

class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ('name', 'count', 'category')


class EventSerializer(serializers.ModelSerializer):
    animal = serializers.PrimaryKeyRelatedField(read_only=False, queryset=Animal.objects.all())
    #status = StatusSerializer()
    #location = serializers.StringRelatedField()#queryset=Location.objects.all(), read_only=False)
    #entered_by = serializers.StringRelatedField()#queryset=User.objects.all(), read_only=False)
    class Meta:
        model = Event
        fields = ('animal', 'date', 'status', 'location', 'description', 'entered_by', 'created')
