# -*- coding: utf-8 -*-
# -*- mode: python -*-
from django_filters import rest_framework as filters

from birds.models import Animal, Event, Measurement, Sample


class AnimalFilter(filters.FilterSet):
    uuid = filters.CharFilter(field_name="uuid", lookup_expr="istartswith")
    color = filters.CharFilter(field_name="band_color__name", lookup_expr="iexact")
    band = filters.NumberFilter(field_name="band_number", lookup_expr="exact")
    species = filters.CharFilter(field_name="species__code", lookup_expr="iexact")
    plumage = filters.CharFilter(field_name="plumage__name", lookup_expr="icontains")
    living = filters.BooleanFilter(field_name="alive", method="is_alive")
    available = filters.BooleanFilter(field_name="reserved_by", lookup_expr="isnull")
    reserved_by = filters.CharFilter(
        field_name="reserved_by__username", lookup_expr="iexact"
    )
    parent = filters.CharFilter(field_name="parents__uuid", lookup_expr="istartswith")
    child = filters.CharFilter(field_name="children__uuid", lookup_expr="istartswith")

    def is_alive(self, queryset, name, value):
        return queryset.filter(alive__gt=0)

    class Meta:
        model = Animal
        fields = ["sex"]


class EventFilter(filters.FilterSet):
    animal = filters.CharFilter(field_name="animal__uuid", lookup_expr="istartswith")
    color = filters.CharFilter(
        field_name="animal__band_color__name", lookup_expr="iexact"
    )
    band = filters.NumberFilter(field_name="animal__band_number", lookup_expr="exact")
    species = filters.CharFilter(
        field_name="animal__species__code", lookup_expr="iexact"
    )
    status = filters.CharFilter(field_name="status__name", lookup_expr="istartswith")
    location = filters.CharFilter(field_name="location__name", lookup_expr="icontains")
    entered_by = filters.CharFilter(
        field_name="entered_by__username", lookup_expr="icontains"
    )
    description = filters.CharFilter(field_name="description", lookup_expr="icontains")

    class Meta:
        model = Event
        fields = {
            "date": ["exact", "year", "range"],
        }


class PairingFilter(filters.FilterSet):
    active = filters.BooleanFilter(field_name="active", method="is_active")
    sire = filters.CharFilter(field_name="sire__uuid", lookup_expr="istartswith")
    sire_color = filters.CharFilter(
        field_name="sire__band_color__name", lookup_expr="iexact"
    )
    sire_band = filters.NumberFilter(
        field_name="sire__band_number", lookup_expr="exact"
    )
    dam = filters.CharFilter(field_name="dam__uuid", lookup_expr="istartswith")
    dam_color = filters.CharFilter(
        field_name="dam__band_color__name", lookup_expr="iexact"
    )
    dam_band = filters.NumberFilter(field_name="dam__band_number", lookup_expr="exact")
    description = filters.CharFilter(field_name="description", lookup_expr="icontains")

    def is_active(self, queryset, name, value):
        return queryset.filter(ended__isnull=value)


class SampleFilter(filters.FilterSet):
    uuid = filters.CharFilter(field_name="uuid", lookup_expr="istartswith")
    type = filters.CharFilter(field_name="type__name", lookup_expr="istartswith")
    location = filters.CharFilter(
        field_name="location__name", lookup_expr="istartswith"
    )
    available = filters.BooleanFilter(field_name="location", method="is_available")
    color = filters.CharFilter(
        field_name="animal__band_color__name", lookup_expr="iexact"
    )
    band = filters.NumberFilter(field_name="animal__band_number", lookup_expr="exact")
    species = filters.CharFilter(
        field_name="animal__species__code", lookup_expr="iexact"
    )
    collected_by = filters.CharFilter(
        field_name="collected_by__username", lookup_expr="iexact"
    )

    def is_available(self, queryset, name, value):
        return queryset.exclude(location__isnull=True)

    class Meta:
        model = Sample
        fields = {
            "date": ["exact", "year", "range"],
        }


class MeasurementFilter(filters.FilterSet):
    animal = filters.CharFilter(
        field_name="event__animal__uuid", lookup_expr="istartswith"
    )
    color = filters.CharFilter(
        field_name="event__animal__band_color__name", lookup_expr="iexact"
    )
    band = filters.NumberFilter(
        field_name="event__animal__band_number", lookup_expr="exact"
    )
    species = filters.CharFilter(
        field_name="event__animal__species__code", lookup_expr="iexact"
    )
    entered_by = filters.CharFilter(
        field_name="event__entered_by__username", lookup_expr="icontains"
    )
    date = filters.DateFromToRangeFilter(field_name="event__date")
    type = filters.CharFilter(field_name="type__name", lookup_expr="icontains")
    value = filters.RangeFilter()

    class Meta:
        model = Measurement
        exclude = ["event"]
