# -*- mode: python -*-

from django.db.models import Count, Prefetch, Q, Window
from django.db.models.functions import RowNumber
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_link_header_pagination import LinkHeaderPagination
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response

from birds import __version__, api_version, pedigree
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
    animal = get_object_or_404(Animal.objects.with_dates(), pk=pk)
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


@api_view(["GET"])
@renderer_classes([JSONRenderer, BrowsableAPIRenderer, JSONLRenderer])
def measurement_list(request, format=None):
    """Get measurements attached to events as streamed line-delimited JSON or as standard JSON"""
    qs = Measurement.objects.select_related("type")
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
        Animal.objects.with_dates()
        .annotate(nchildren=Count("children"))
        .filter(Q(alive__gt=0) | Q(nchildren__gt=0))
        .annotate(
            idx=Window(expression=RowNumber(), order_by=["created", "uuid"]),
        )
        .prefetch_related(
            Prefetch("parents", queryset=Animal.objects.with_dates()),
            Prefetch("parents__parents", queryset=Animal.objects.with_dates()),
            Prefetch("parents__children", queryset=Animal.objects.with_dates()),
            Prefetch("children", queryset=Animal.objects.with_dates()),
        )
        .select_related("species", "band_color", "plumage")
        .order_by("idx")
    )
    # convert uuids to indices for inbreeding calculation
    bird_to_idx = {a: a.idx for a in qs}
    bird_to_idx[None] = 0
    sires = [bird_to_idx[a.sire()] for a in qs]
    dams = [bird_to_idx[a.dam()] for a in qs]
    inbreeding = pedigree.inbreeding_coeffs(sires, dams)
    # allow user to filter the results
    f = AnimalFilter(request.GET, qs)

    ctx = {"bird_to_idx": bird_to_idx, "inbreeding": inbreeding}
    if format == "jsonl" or JSONLRenderer.requested_by(request):
        renderer = JSONLRenderer()
        gen = (
            renderer.render(AnimalPedigreeSerializer(obj, context=ctx).data)
            for obj in f.qs
        )
        return StreamingHttpResponse(gen)
    else:
        serializer = AnimalPedigreeSerializer(f.qs, context=ctx, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
