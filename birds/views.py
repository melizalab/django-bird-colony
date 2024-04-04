# -*- coding: utf-8 -*-
# -*- mode: python -*-
import calendar
import datetime
from itertools import groupby
from typing import Optional
from collections import Counter, defaultdict

from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db.models import F
from django.db.utils import IntegrityError
from django.forms import ValidationError, formset_factory
from django.http import HttpResponseRedirect, HttpResponseBadRequest, Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import dateparse
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.decorators.http import require_http_methods
from drf_link_header_pagination import LinkHeaderPagination
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response

from birds import __version__, api_version
from birds.forms import (
    EndPairingForm,
    EventForm,
    NestCheckForm,
    NestCheckUser,
    NewAnimalForm,
    NewBandForm,
    NewPairingForm,
    ReservationForm,
    SampleForm,
    SexForm,
)
from birds.models import (
    ADULT_ANIMAL_NAME,
    Age,
    Animal,
    Event,
    NestCheck,
    Pairing,
    Sample,
    SampleType,
    Status,
)
from birds.serializers import (
    AnimalDetailSerializer,
    AnimalPedigreeSerializer,
    PedigreeRequestSerializer,
    AnimalSerializer,
    EventSerializer,
)
from birds.filters import (
    AnimalFilter,
    EventFilter,
    SampleFilter,
    PairingFilter,
    DjangoFilterBackend,
)
from birds.tools import tabulate_locations, tabulate_nests


class LargeResultsSetPagination(LinkHeaderPagination):
    page_size = 1000
    page_size_query_param = "page_size"
    max_page_size = 10000


@require_http_methods(["GET"])
def animal_list(request):
    qs = (
        Animal.objects.with_annotations()
        .with_related()
        .order_by("band_color", "band_number")
    )
    f = AnimalFilter(request.GET, queryset=qs)
    paginator = Paginator(f.qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "birds/animal_list.html",
        {"filter": f, "page_obj": page_obj, "animal_list": page_obj.object_list},
    )


@require_http_methods(["GET"])
def pairing_list(request):
    qs = Pairing.objects.with_related().with_progeny_stats().order_by("-began")
    f = PairingFilter(request.GET, queryset=qs)
    paginator = Paginator(f.qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "birds/pairing_list.html",
        {"page_obj": page_obj, "pairing_list": page_obj.object_list},
    )


@require_http_methods(["GET"])
def active_pairing_list(request):
    qs = Pairing.objects.with_related().with_progeny_stats().with_location()
    f = PairingFilter(request.GET, queryset=qs)
    return render(
        request,
        "birds/pairing_list_active.html",
        {"pairing_list": f.qs},
    )


@require_http_methods(["GET"])
def pairing_view(request, pk):
    qs = Pairing.objects.with_related().with_progeny_stats()
    pair = get_object_or_404(qs, pk=pk)
    eggs = pair.eggs().with_annotations().with_related().order_by("-alive", "-created")
    pairings = pair.other_pairings().with_progeny_stats()
    events = pair.related_events().with_related()
    return render(
        request,
        "birds/pairing.html",
        {
            "pairing": pair,
            "animal_list": eggs,
            "pairing_list": pairings,
            "event_list": events,
        },
    )


def new_pairing_entry(request, pk: Optional[int] = None):
    if request.method == "POST":
        form = NewPairingForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if data["location"] is None:
                pair = Pairing.objects.create(
                    sire=data["sire"],
                    dam=data["dam"],
                    began=data["began"],
                    purpose=data["purpose"],
                )
            else:
                pair = Pairing.objects.create_with_events(
                    sire=data["sire"],
                    dam=data["dam"],
                    began=data["began"],
                    purpose=data["purpose"],
                    location=data["location"],
                    entered_by=data["entered_by"],
                )
            return HttpResponseRedirect(reverse("birds:pairing", args=(pair.pk,)))
    else:
        form = NewPairingForm()
        form.initial["entered_by"] = request.user
        if pk is not None:
            old_pairing = get_object_or_404(Pairing, pk=pk)
            form.fields["sire"].queryset = Animal.objects.filter(
                uuid=old_pairing.sire.uuid
            )
            form.initial["sire"] = old_pairing.sire
            form.fields["dam"].queryset = Animal.objects.filter(
                uuid=old_pairing.dam.uuid
            )
            form.initial["dam"] = old_pairing.dam

    return render(request, "birds/pairing_entry.html", {"form": form})


def close_pairing(request, pk: int):
    pairing = get_object_or_404(Pairing, pk=pk)
    if request.method == "POST":
        form = EndPairingForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # some dirty validation logic to catch errors thrown by the model
            try:
                pairing.close(
                    ended=data["ended"],
                    entered_by=data["entered_by"],
                    location=data["location"],
                    comment=data["comment"],
                )
                return HttpResponseRedirect(reverse("birds:pairing", args=(pk,)))
            except IntegrityError as err:
                form.add_error(
                    None,
                    ValidationError(
                        _("Ending date must be after beginning (%(value)s)"),
                        params={"value": pairing.began},
                    ),
                )
            except ValueError as err:
                form.add_error(None, ValidationError(_(str(err))))
    else:
        form = EndPairingForm()
        form.initial["entered_by"] = request.user

    return render(
        request, "birds/pairing_close.html", {"form": form, "pairing": pairing}
    )


@require_http_methods(["GET"])
def location_summary(request):
    # do this with a single query and then group by location
    qs = (
        Animal.objects.with_annotations()
        .with_related()
        .alive()
        .order_by("last_location")
    )
    loc_data = []
    for location, animals in groupby(qs, key=lambda animal: animal.last_location):
        d = defaultdict(list)
        for animal in animals:
            age_group = animal.age_group()
            if age_group == ADULT_ANIMAL_NAME:
                group_name = "{} {}".format(age_group, Animal.Sex(animal.sex).label)
                d[group_name].append(animal)
            else:
                d[age_group].append(animal)
        loc_data.append((location, sorted(d.items())))
    return render(
        request, "birds/animal_location_summary.html", {"location_list": loc_data}
    )


@require_http_methods(["GET"])
def nest_report(request):
    default_days = 4

    try:
        until = dateparse.parse_date(request.GET["until"])
    except (ValueError, KeyError):
        until = None
    try:
        since = dateparse.parse_date(request.GET["since"])
    except (ValueError, KeyError):
        since = None
    until = until or datetime.datetime.now().date()
    since = since or (until - datetime.timedelta(days=default_days))
    dates, nest_data = tabulate_nests(since, until)
    checks = NestCheck.objects.filter(
        datetime__date__gte=since, datetime__date__lte=until
    ).order_by("datetime")
    return render(
        request,
        "birds/nest_report.html",
        {
            "since": since,
            "until": until,
            "dates": dates,
            "nest_data": nest_data,
            "nest_checks": checks,
        },
    )


@require_http_methods(["GET", "POST"])
def nest_check(request):
    """Nest check view.

    This view is a two-stage form. With GET requests the user is shown a nest
    report for the past 3 days and is able to update egg and chick counts for
    each nest. POST requests do not get immediately committed to the database,
    but instead are used to generate a confirmation form that summarizes
    everything that will change. Submitting this form will then redirect to the
    main nest-report page.

    """

    NestCheckFormSet = formset_factory(NestCheckForm, extra=0)
    until = datetime.datetime.now().date()
    since = until - datetime.timedelta(days=2)
    dates, nest_data = tabulate_nests(since, until)
    initial = []
    previous_checks = NestCheck.objects.filter(
        datetime__date__gte=(until - datetime.timedelta(days=7))
    ).order_by("datetime")
    for nest in nest_data:
        today_counts = nest["days"][-1]["counts"]
        total_count = sum(today_counts.values())
        eggs = today_counts.get("egg", 0)
        initial.append(
            {"location": nest["location"], "eggs": eggs, "chicks": total_count - eggs}
        )

    if request.method == "POST":
        nest_formset = NestCheckFormSet(request.POST, initial=initial, prefix="nests")
        user_form = NestCheckUser(request.POST, prefix="user")
        if nest_formset.is_valid():
            # determine what changes need to be made:
            changes = defaultdict(list)
            for nest_form, nest in zip(nest_formset, nest_data):
                initial = nest_form.initial
                updated = nest_form.cleaned_data
                location = updated["location"]
                if not nest_form.has_changed():
                    changes[location].append({"status": None})
                    continue
                # return user to initial view if there are errors
                if not nest_form.is_valid():
                    return render(
                        request,
                        "birds/nest_check.html",
                        {
                            "dates": dates,
                            "nest_checks": previous_checks,
                            "nest_data": zip(nest_data, nest_formset),
                            "nest_formset": nest_formset,
                        },
                    )
                eggs = nest["days"][-1]["animals"]["egg"]
                for _ in range(updated["delta_chicks"]):
                    hatch = dict(
                        animal=eggs.pop(),
                        status=updated["hatch_status"],
                        location=location,
                    )
                    changes[location].append(hatch)
                if updated["delta_eggs"] < 0:
                    for _ in range(-updated["delta_eggs"]):
                        lost = dict(
                            animal=eggs.pop(),
                            status=updated["lost_status"],
                            location=location,
                        )
                        changes[location].append(lost)
                else:
                    for _ in range(updated["delta_eggs"]):
                        egg = dict(
                            status=updated["laid_status"],
                            sire=updated["sire"],
                            dam=updated["dam"],
                            location=location,
                        )
                        changes[location].append(egg)

            # if the user form is valid, we are coming from the confirmation
            # page; if it's invalid, we're coming from the initial view
            if user_form.is_valid() and user_form.cleaned_data["confirmed"]:
                user = user_form.cleaned_data["entered_by"]
                for items in changes.values():
                    for item in items:
                        if item["status"] in (
                            updated["hatch_status"],
                            updated["lost_status"],
                        ):
                            event = Event.objects.create(
                                date=datetime.date.today(), entered_by=user, **item
                            )
                        elif item["status"] == updated["laid_status"]:
                            animal = Animal.objects.create_from_parents(
                                sire=item["sire"],
                                dam=item["dam"],
                                date=datetime.date.today(),
                                status=item["status"],
                                entered_by=user,
                                location=item["location"],
                            )
                check = NestCheck.objects.create(
                    entered_by=user, comments=user_form.cleaned_data["comments"]
                )
                return HttpResponseRedirect(reverse("birds:nest-summary"))
            else:
                return render(
                    request,
                    "birds/nest_check_confirm.html",
                    {
                        "changes": dict(changes),
                        "nest_formset": nest_formset,
                        "user_form": user_form,
                    },
                )
        else:
            pass
    else:
        nest_formset = NestCheckFormSet(initial=initial, prefix="nests")

    # the initial view is returned by default
    return render(
        request,
        "birds/nest_check.html",
        {
            "dates": dates,
            "nest_checks": previous_checks,
            "nest_data": zip(nest_data, nest_formset),
            "nest_formset": nest_formset,
        },
    )


@require_http_methods(["GET"])
def event_list(request, animal: Optional[str] = None):
    qs = Event.objects.with_related().order_by("-date", "-created")
    if animal is not None:
        animal = get_object_or_404(Animal, uuid=animal)
        qs = qs.filter(animal=animal)
    f = EventFilter(request.GET, queryset=qs)
    paginator = Paginator(f.qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "birds/event_list.html",
        {"filter": f, "page_obj": page_obj, "event_list": page_obj.object_list},
    )


@require_http_methods(["GET"])
def animal_view(request, uuid: str):
    qs = Animal.objects.with_annotations()
    animal = get_object_or_404(qs, uuid=uuid)
    kids = (
        animal.children.with_annotations()
        .with_related()
        .order_by("-alive", F("age").desc(nulls_last=True))
    )
    events = animal.event_set.with_related().order_by("-date", "-created")
    samples = animal.sample_set.order_by("-date")
    pairings = animal.pairings().with_related().with_progeny_stats().order_by("-began")
    return render(
        request,
        "birds/animal.html",
        {
            "animal": animal,
            "animal_list": kids,
            "event_list": events,
            "sample_list": samples,
            "pairing_list": pairings,
        },
    )


@require_http_methods(["GET"])
def animal_genealogy(request, uuid: str):
    animal = get_object_or_404(Animal.objects.with_dates(), pk=uuid)
    generations = (1, 2, 3, 4)
    ancestors = [
        Animal.objects.ancestors_of(animal, generation=gen).with_annotations()
        for gen in generations
    ]
    descendents = [
        Animal.objects.descendents_of(animal, generation=gen)
        .with_annotations()
        .hatched()
        .order_by("-alive", "-age")
        for gen in generations
    ]
    # have to manually filter here because alive() will call with_status()
    living = [qs.filter(alive__gt=0) for qs in descendents]
    return render(
        request,
        "birds/genealogy.html",
        {
            "animal": animal,
            "ancestors": ancestors,
            "descendents": descendents,
            "living": living,
        },
    )


class GenealogyView(generic.DetailView):
    model = Animal
    template_name = "birds/genealogy.html"
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        animal = context["animal"]
        # could probably speed these up by prefetching related
        context["ancestors"] = [
            animal.parents.all(),
            Animal.objects.filter(children__children=animal),
            Animal.objects.filter(children__children__children=animal),
            Animal.objects.filter(children__children__children__children=animal),
        ]
        context["descendents"] = [
            animal.children.filter(event__status__adds=True).order_by("-alive"),
            Animal.objects.filter(
                parents__parents=animal, event__status__adds=True
            ).order_by("-alive"),
            Animal.objects.filter(
                parents__parents__parents=animal, event__status__adds=True
            ).order_by("-alive"),
            Animal.objects.filter(
                parents__parents__parents__parents=animal, event__status__adds=True
            ).order_by("-alive"),
        ]
        context["living"] = [qs.filter(alive=True) for qs in context["descendents"]]
        return context


@require_http_methods(["GET", "POST"])
def new_animal_entry(request):
    if request.method == "POST":
        form = NewAnimalForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if data["sire"] is not None and data["dam"] is not None:
                animal = Animal.objects.create_from_parents(
                    sire=data["sire"],
                    dam=data["dam"],
                    date=data["acq_date"],
                    status=data["acq_status"],
                    description=data["comments"],
                    location=data["location"],
                    entered_by=data["user"],
                )
            else:
                animal = Animal.objects.create_with_event(
                    species=data["species"],
                    date=data["acq_date"],
                    status=data["acq_status"],
                    description=data["comments"],
                    location=data["location"],
                    entered_by=data["user"],
                )
            animal.update_band(
                band_number=data["band_number"],
                band_color=data["band_color"],
                date=data["banding_date"],
                location=data["location"],
                entered_by=data["user"],
                sex=data["sex"],
                plumage=data["plumage"],
            )
            return HttpResponseRedirect(reverse("birds:animal", args=(animal.pk,)))
    else:
        form = NewAnimalForm()
        form.initial["user"] = request.user

    return render(request, "birds/animal_entry.html", {"form": form})


@require_http_methods(["GET", "POST"])
def new_band_entry(request, uuid: str):
    animal = get_object_or_404(Animal, pk=uuid)
    if request.method == "POST":
        form = NewBandForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            animal.update_band(
                band_number=data["band_number"],
                date=data["banding_date"],
                entered_by=data["user"],
                band_color=data["band_color"],
                sex=data["sex"],
                plumage=data["plumage"],
                location=data["location"],
            )
            return HttpResponseRedirect(reverse("birds:animal", args=(animal.pk,)))
    else:
        form = NewBandForm()
        form.initial["user"] = request.user
        form.initial["sex"] = animal.sex

    return render(request, "birds/band_entry.html", {"animal": animal, "form": form})


@require_http_methods(["GET", "POST"])
def new_event_entry(request, uuid: str):
    animal = get_object_or_404(Animal, pk=uuid)
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            event = Event.objects.create(
                animal=animal,
                date=data["date"],
                status=data["status"],
                entered_by=data["entered_by"],
                location=data["location"],
                description=data["description"],
            )
            return HttpResponseRedirect(reverse("birds:animal", args=(animal.pk,)))
    else:
        form = EventForm()
        form.initial["entered_by"] = request.user

    return render(request, "birds/event_entry.html", {"form": form, "animal": animal})


@require_http_methods(["GET", "POST"])
def reservation_entry(request, uuid: str):
    animal = get_object_or_404(Animal, pk=uuid)
    if request.method == "POST":
        form = ReservationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if data["entered_by"] is None:
                user = request.user
                animal.reserved_by = None
                descr = f"reservation released: {data['description']}"
            else:
                user = animal.reserved_by = data["entered_by"]
                descr = f"reservation created: {data['description']}"
            animal.save()
            evt = Event.objects.create(
                animal=animal,
                date=data["date"],
                status=data["status"],
                entered_by=user,
                description=descr,
            )
            return HttpResponseRedirect(reverse("birds:animal", args=(animal.pk,)))
    else:
        form = ReservationForm()
        if animal.reserved_by is None:
            form.initial["entered_by"] = request.user
    return render(
        request, "birds/reservation_entry.html", {"animal": animal, "form": form}
    )


@require_http_methods(["GET", "POST"])
def update_sex(request, uuid: str):
    animal = get_object_or_404(Animal, pk=uuid)
    if request.method == "POST":
        form = SexForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            animal.update_sex(
                date=data["date"],
                entered_by=data["entered_by"],
                sex=data["sex"],
                description=data["description"],
            )
            return HttpResponseRedirect(reverse("birds:animal", args=(animal.pk,)))
    else:
        form = SexForm()
        form.initial["entered_by"] = request.user
        form.initial["sex"] = animal.sex

    return render(request, "birds/sex_entry.html", {"animal": animal, "form": form})


@require_http_methods(["GET"])
def index(request):
    today = datetime.date.today()
    return render(
        request,
        "birds/index.html",
        {
            "today": today,
            "lastmonth": today.replace(day=1) - datetime.timedelta(days=1),
        },
    )


@require_http_methods(["GET"])
def event_summary(request, year: int, month: int):
    try:
        date = datetime.date(year=year, month=month, day=1)
    except ValueError as err:
        raise Http404("No such year/ month") from err
    event_counts = Event.objects.in_month(date).count_by_status()
    today = datetime.date.today()
    if date.year == today.year and date.month == today.month:
        refdate = today
    else:
        refdate = datetime.date(
            year=year, month=month, day=calendar.monthrange(year, month)[1]
        )
    birds = (
        Animal.objects.with_dates(refdate)
        .prefetch_related("species__age_set")
        .alive_on(refdate)
        .order_by("species", "born_on")
    )
    counter = defaultdict(lambda: defaultdict(Counter))
    for bird in birds:
        age_group = bird.age_group()
        counter[bird.species.common_name][age_group][bird.sex] += 1
    # template engine really wants plain dicts
    counts = [
        (species, [(age, counts) for age, counts in ages.items()])
        for species, ages in counter.items()
    ]

    return render(
        request,
        "birds/summary.html",
        {
            "year": year,
            "month": month,
            "next": date + datetime.timedelta(days=32),
            "prev": date - datetime.timedelta(days=1),
            "event_totals": event_counts.order_by(),
            "bird_counts": counts,
        },
    )


@require_http_methods(["GET"])
def sample_type_list(request):
    qs = SampleType.objects.all()
    return render(request, "birds/sample_type_list.html", {"sampletype_list": qs})


@require_http_methods(["GET"])
def sample_list(request, animal: Optional[str] = None):
    qs = Sample.objects.select_related(
        "type",
        "location",
        "collected_by",
        "animal",
        "animal__species",
        "animal__band_color",
    ).order_by("-date")
    if animal is not None:
        animal = get_object_or_404(Animal, uuid=animal)
        qs = qs.filter(animal=animal)
    f = SampleFilter(request.GET, queryset=qs)
    paginator = Paginator(f.qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "birds/sample_list.html",
        {"filter": f, "page_obj": page_obj, "sample_list": page_obj.object_list},
    )


@require_http_methods(["GET"])
def sample_view(request, uuid: str):
    sample = get_object_or_404(Sample, uuid=uuid)
    return render(
        request,
        "birds/sample.html",
        {"sample": sample},
    )


@require_http_methods(["GET", "POST"])
def new_sample_entry(request, uuid: str):
    animal = get_object_or_404(Animal, pk=uuid)
    if request.method == "POST":
        form = SampleForm(request.POST)
        if form.is_valid():
            sample = form.save(commit=False)
            sample.animal = animal
            sample.save()
            return HttpResponseRedirect(reverse("birds:animal", args=(animal.pk,)))
    else:
        form = SampleForm()
        form.fields["source"].queryset = Sample.objects.filter(animal=animal)
        form.initial["collected_by"] = request.user

    return render(request, "birds/sample_entry.html", {"form": form, "animal": animal})


### API
@api_view(["GET"])
def api_info(request, format=None):
    return Response(
        {
            "name": "django-bird-colony",
            "version": __version__,
            "api_version": api_version,
        }
    )


class APIAnimalsList(generics.ListAPIView):
    queryset = (
        Animal.objects.with_status()
        .select_related("reserved_by", "species", "band_color")
        .prefetch_related("parents")
        .order_by("band_color", "band_number")
    )
    serializer_class = AnimalSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = AnimalFilter


class APIAnimalChildList(APIAnimalsList):
    """List all the children of an animal"""

    def get_queryset(self):
        animal = get_object_or_404(Animal, uuid=self.kwargs["pk"])
        return (
            animal.children.with_status()
            .select_related("reserved_by", "species", "band_color")
            .prefetch_related("parents")
            .order_by("band_color", "band_number")
        )


@api_view(["GET"])
def api_animal_detail(request, pk: str, format=None):
    animal = get_object_or_404(Animal, pk=pk)
    serializer = AnimalDetailSerializer(animal)
    return Response(serializer.data)


class APIEventsList(generics.ListAPIView):
    queryset = Event.objects.with_related()
    serializer_class = EventSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = EventFilter


class APIAnimalPedigree(generics.ListAPIView):
    """A list of animals and their parents.

    If query param restrict is False, includes all animals, not just
    the ones useful for constructing a pedigree.
    """

    serializer_class = AnimalPedigreeSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = AnimalFilter
    pagination_class = LargeResultsSetPagination

    def get_queryset(self):
        from django.db.models import Count, Q

        queryset = (
            Animal.objects.with_status()
            .with_dates()
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
