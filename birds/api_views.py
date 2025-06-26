# -*- mode: python -*-

from django.db.models import Prefetch
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_link_header_pagination import LinkHeaderPagination
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
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
)


class LargeResultsSetPagination(LinkHeaderPagination):
    page_size = 1000
    page_size_query_param = "page_size"
    max_page_size = 10000


class JSONLRenderer(JSONRenderer):
    media_type = "application/x-jsonlines"
    format = "jsonl"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        out = super().render(data, accepted_media_type, renderer_context)
        return out + b"\n"

    @classmethod
    def requested_by(cls, request):
        return (
            request.accepted_renderer.format == cls.format
            or cls.media_type in request.META.get("HTTP_ACCEPT", "")
        )


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
        Animal.objects.with_related()
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
            animal.children.with_related()
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
        qs = Event.objects.select_related(
            "location", "status", "entered_by"
        ).prefetch_related("measurements", "measurements__type")
        try:
            animal = get_object_or_404(Animal, uuid=self.kwargs["animal"])
            return qs.filter(animal=animal)
        except KeyError:
            return qs

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


@api_view(["GET"])
@renderer_classes([JSONRenderer, BrowsableAPIRenderer, JSONLRenderer])
def measurement_list(request, format=None):
    """Get measurements attached to events as streamed line-delimited JSON or as standard JSON"""
    qs = Measurement.objects.select_related("type", "event")
    f = MeasurementFilter(request.GET, queryset=qs)
    if format == "jsonl" or JSONLRenderer.requested_by(request):
        renderer = JSONLRenderer()
        gen = (renderer.render(MeasurementSerializer(obj).data) for obj in f.qs)
        return StreamingHttpResponse(gen)
    else:
        serializer = MeasurementSerializer(f.qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@renderer_classes([JSONRenderer, BrowsableAPIRenderer, JSONLRenderer])
def animal_pedigree(request, format=None):
    """Streams a list of animals with their parents and various statistics important for breeding.

    Only animals that are currently alive or have descendents are included in
    the pedigree. The results can be further filtered using standard Animal query
    params.

    """
    qs = (
        Animal.objects.for_pedigree()
        .prefetch_related(
            Prefetch("parents"),
            Prefetch("parents__parents"),
            Prefetch("children"),
            # used when calculating parent breeding outcomes in the dabase
            # Prefetch("parents__children", queryset=Animal.objects.with_dates()),
        )
        .select_related("species", "band_color", "plumage")
    )
    f = AnimalFilter(request.GET, qs)

    if format == "jsonl" or JSONLRenderer.requested_by(request):
        renderer = JSONLRenderer()
        gen = (renderer.render(AnimalPedigreeSerializer(obj).data) for obj in f.qs)
        return StreamingHttpResponse(gen)
    else:
        serializer = AnimalPedigreeSerializer(f.qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
