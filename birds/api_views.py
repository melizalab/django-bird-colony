# -*- coding: utf-8 -*-
# -*- mode: python -*-

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_link_header_pagination import LinkHeaderPagination
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from birds import __version__, api_version
from birds.filters import (
    AnimalFilter,
    EventFilter,
    MeasurementFilter,
)
from birds.models import (
    Animal,
    Event,
    Measurement,
)
from birds.serializers import (
    AnimalDetailSerializer,
    AnimalPedigreeSerializer,
    AnimalSerializer,
    EventSerializer,
    MeasurementSerializer,
    PedigreeRequestSerializer,
)


class LargeResultsSetPagination(LinkHeaderPagination):
    page_size = 1000
    page_size_query_param = "page_size"
    max_page_size = 10000


@api_view(["GET"])
def info(request, format=None):
    return Response(
        {
            "name": "django-bird-colony",
            "version": __version__,
            "api_version": api_version,
        }
    )


class AnimalsList(generics.ListAPIView):
    queryset = (
        Animal.objects.with_dates()
        .select_related("reserved_by", "species", "band_color")
        .prefetch_related("parents")
        .order_by("band_color", "band_number")
    )
    serializer_class = AnimalSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = AnimalFilter


class AnimalChildList(AnimalsList):
    """List all the children of an animal"""

    def get_queryset(self):
        animal = get_object_or_404(Animal, uuid=self.kwargs["pk"])
        return (
            animal.children.with_dates()
            .select_related("reserved_by", "species", "band_color")
            .prefetch_related("parents")
            .order_by("band_color", "band_number")
        )


@api_view(["GET"])
def animal_detail(request, pk: str, format=None):
    animal = get_object_or_404(Animal, pk=pk)
    serializer = AnimalDetailSerializer(animal)
    return Response(serializer.data)


class EventList(generics.ListCreateAPIView):
    serializer_class = EventSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = EventFilter
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        try:
            animal = get_object_or_404(Animal, uuid=self.kwargs["animal"])
            return Event.objects.filter(animal=animal)
        except KeyError:
            return Event.objects.all()

    def perform_create(self, serializer):
        serializer.save(entered_by=self.request.user)


@api_view(["GET", "PATCH"])
def event_detail(request, pk: int, format=None):
    event = Event.objects.get(pk=pk)
    if request.method == "GET":
        serializer = EventSerializer(event)
        return Response(serializer.data)
    elif request.method == "PATCH":
        if not request.user.is_authenticated:
            return Response(
                {"detail": "login required to update events"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        serializer = EventSerializer(event, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MeasurementsList(generics.ListAPIView):
    queryset = Measurement.objects.all()
    serializer_class = MeasurementSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = MeasurementFilter


class AnimalPedigree(generics.ListAPIView):
    """A list of animals and their parents.

    If query param restrict is False, includes all animals, not just
    the ones useful for constructing a pedigree.
    """

    serializer_class = AnimalPedigreeSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = AnimalFilter
    pagination_class = LargeResultsSetPagination

    def get_queryset(self):
        queryset = (
            Animal.objects.with_dates()
            .select_related("reserved_by", "species", "band_color", "plumage")
            .prefetch_related("parents__species")
            .prefetch_related("parents__band_color")
            .order_by("band_color", "band_number")
        )
        request_parsed = PedigreeRequestSerializer(data=self.request.query_params)
        if request_parsed.is_valid() and request_parsed.data["restrict"]:
            queryset = queryset.annotate(nchildren=Count("children")).filter(
                Q(alive__gt=0) | Q(nchildren__gt=0)
            )
        return queryset
