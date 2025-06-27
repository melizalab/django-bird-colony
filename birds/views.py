# -*- mode: python -*-
import calendar
import datetime
from collections import Counter, defaultdict
from itertools import groupby

from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q, Window
from django.db.models.functions import RowNumber
from django.db.utils import IntegrityError
from django.forms import ValidationError, formset_factory
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import dateparse
from django.utils.timezone import make_aware
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from birds import __version__, pedigree
from birds.filters import (
    AnimalFilter,
    EventFilter,
    MeasurementFilter,
    PairingFilter,
    SampleFilter,
)
from birds.forms import (
    BreedingCheckForm,
    EndPairingForm,
    EventForm,
    MeasurementForm,
    NestCheckUser,
    NewAnimalForm,
    NewBandForm,
    NewEggForm,
    NewPairingForm,
    ReservationForm,
    SampleForm,
    SexForm,
)
from birds.models import (
    ADULT_ANIMAL_NAME,
    Animal,
    Event,
    Location,
    Measure,
    Measurement,
    NestCheck,
    Pairing,
    Sample,
    SampleType,
    Status,
)
from birds.tools import tabulate_pairs


@require_http_methods(["GET"])
def index(request):
    today = datetime.date.today()
    return render(
        request,
        "birds/index.html",
        {
            "today": today,
            "lastmonth": today.replace(day=1) - datetime.timedelta(days=1),
            "version": __version__,
        },
    )


# Animals
@require_http_methods(["GET"])
def animal_list(request, *, parent: str | None = None):
    qs = Animal.objects.with_related().with_child_counts().order_by_life_stage()
    if parent is not None:
        animal = get_object_or_404(Animal, uuid=parent)
        qs = qs.descendents_of(animal)
        header_text = f"Children of {animal}"
    else:
        header_text = "Birds"

    query = request.GET.copy()
    try:
        page_number = query.pop("page")[-1]
    except (KeyError, IndexError):
        page_number = None
    f = AnimalFilter(query, queryset=qs)
    paginator = Paginator(f.qs, 25)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "birds/animal_list.html",
        {
            "header_text": header_text,
            "filter": f,
            "query": query,
            "page_obj": page_obj,
            "animal_list": page_obj.object_list,
        },
    )


@require_http_methods(["GET"])
def animal_view(request, uuid: str):
    qs = Animal.objects.with_related().with_child_counts()
    animal = get_object_or_404(qs, uuid=uuid)
    kids = (
        animal.children.hatched()
        .with_related()
        .with_child_counts()
        .order_by_life_stage()
    )
    events = animal.event_set.with_related().order_by("-date", "-created")
    samples = animal.sample_set.order_by("-date")
    pairings = (
        animal.pairings().with_related().with_progeny_stats().order_by("-began_on")
    )
    return render(
        request,
        "birds/animal.html",
        {
            "animal": animal,
            "animal_measurements": animal.measurements(),
            "history": animal.history,
            "kids": kids,
            "event_list": events,
            "sample_list": samples,
            "pairing_list": pairings,
        },
    )


@require_http_methods(["GET"])
def animal_genealogy(request, uuid: str):
    animal = get_object_or_404(Animal, pk=uuid)
    generations = (1, 2, 3, 4)
    ancestors = [
        Animal.objects.with_child_counts().ancestors_of(animal, generation=gen)
        for gen in generations
    ]
    descendents = [
        Animal.objects.with_child_counts()
        .descendents_of(animal, generation=gen)
        .hatched()
        .order_by("-n_hatched", "-life_history__died_on", "life_history__born_on")
        for gen in generations
    ]
    living = [qs.alive() for qs in descendents]
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


@require_http_methods(["GET", "POST"])
def reservation_entry(request, uuid: str):
    # TODO write tests
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
            Event.objects.create(
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


# Events
@require_http_methods(["GET"])
def event_list(request, *, animal: str | None = None, location: int | None = None):
    qs = Event.objects.with_related().order_by("-date", "-created")
    if animal is not None:
        animal = get_object_or_404(Animal, uuid=animal)
        qs = qs.filter(animal=animal)
        header_text = f"Events for {animal}"
    elif location is not None:
        location = get_object_or_404(Location, pk=location)
        qs = qs.filter(location=location)
        header_text = f"Events for {location}"
    else:
        header_text = "Events"
    query = request.GET.copy()
    try:
        page_number = query.pop("page")[-1]
    except (KeyError, IndexError):
        page_number = None
    f = EventFilter(query, queryset=qs)
    paginator = Paginator(f.qs, 25)
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "birds/event_list.html",
        {
            "filter": f,
            "query": query,
            "page_obj": page_obj,
            "event_list": page_obj.object_list,
            "header_text": header_text,
        },
    )


@require_http_methods(["GET", "POST"])
def event_entry(request, event: int | None = None, animal: str | None = None):
    if event:
        # editing an existing event
        event = get_object_or_404(Event, pk=event)
        animal = event.animal
        form = EventForm(request.POST or None, instance=event)
        action = reverse("birds:event_entry", kwargs={"event": event.pk})
    elif animal:
        # adding a new event
        animal = get_object_or_404(Animal, pk=animal)
        form = EventForm(request.POST or None)
        action = reverse("birds:event_entry", kwargs={"animal": animal.uuid})

    MeasurementFormSet = formset_factory(MeasurementForm, extra=0, can_delete=False)

    if request.method == "POST":
        if form.is_valid():
            if event:
                form.save()
            else:
                event = form.save(commit=False)
                event.animal = animal
                event.save()
            formset = MeasurementFormSet(request.POST, prefix="measurements")
            if formset.is_valid():
                for measurement_form in formset:
                    value = measurement_form.cleaned_data["value"]
                    measure = measurement_form.cleaned_data["type"]
                    if value is None:
                        Measurement.objects.filter(event=event, type=measure).delete()
                    else:
                        Measurement.objects.update_or_create(
                            event=event, type=measure, defaults={"value": value}
                        )

            return HttpResponseRedirect(reverse("birds:animal", args=(animal.pk,)))
    else:
        if event:
            form.initial["entered_by"] = event.entered_by
            initial_data = [
                {"type": measure, "value": measure.measurement_value}
                for measure in event.measures()
            ]
        else:
            form.initial["entered_by"] = request.user
            initial_data = [
                {"type": measure, "value": None} for measure in Measure.objects.all()
            ]
        formset = MeasurementFormSet(initial=initial_data, prefix="measurements")
        event_types = Status.objects.all().order_by("-removes", "-adds", "name")

    return render(
        request,
        "birds/event_entry.html",
        {
            "form": form,
            "measurements": formset,
            "form_action": action,
            "animal": animal,
            "event": event,
            "event_types": event_types,
        },
    )


# Measurements
@require_http_methods(["GET"])
def measurement_list(
    request,
    *,
    animal: str | None = None,
):
    qs = Measurement.objects.select_related(
        "type",
        "event",
        "event__animal",
        "event__animal__species",
        "event__animal__band_color",
        "event__entered_by",
    ).order_by("-event__date", "-created")
    if animal is not None:
        animal = get_object_or_404(Animal, uuid=animal)
        qs = qs.filter(event__animal=animal)
        header_text = f"Measurements for {animal}"
    else:
        header_text = "Measurements"
    query = request.GET.copy()
    try:
        page_number = query.pop("page")[-1]
    except (KeyError, IndexError):
        page_number = None
    f = MeasurementFilter(query, queryset=qs)
    paginator = Paginator(f.qs, 25)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "birds/measurement_list.html",
        {
            "filter": f,
            "query": query,
            "page_obj": page_obj,
            "measurement_list": page_obj.object_list,
            "header_text": header_text,
        },
    )


# Locations
@require_http_methods(["GET"])
def location_list(request):
    qs = (
        Location.objects.filter(active=True)
        .select_related("room")
        .order_by("room__name", "name")
    )
    # paginator = Paginator(qs, 25)
    # page_number = request.GET.get("page")
    # page_obj = paginator.get_page(page_number)
    return render(
        request,
        "birds/location_list.html",
        {"location_list": qs},
        # {"page_obj": page_obj, "location_list": page_obj.object_list},
    )


@require_http_methods(["GET"])
def location_view(request, pk):
    location = get_object_or_404(Location, pk=pk)
    birds = location.birds().with_related().existing().order_by("-created")
    events = location.event_set.with_related()

    return render(
        request,
        "birds/location.html",
        {
            "location": location,
            "animal_list": birds.alive(),
            "egg_list": birds.eggs(),
            "event_list": events,
        },
    )


# Users
@require_http_methods(["GET"])
def user_list(request):
    queryset = (
        User.objects.filter(is_active=True)
        .annotate(
            n_reserved=Count("animal"),
            n_reserved_alive=Count(
                "animal",
                filter=Q(animal__life_history__acquired_on__isnull=False)
                & Q(animal__life_history__died_on__isnull=True),
            ),
        )
        .order_by("-n_reserved")
    )
    return render(
        request,
        "birds/user_list.html",
        {"user_list": queryset},
    )


@require_http_methods(["GET"])
def user_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    reserved = user.animal_set.with_related().order_by_life_stage()
    query = request.GET.copy()
    try:
        page_number = query.pop("page")[-1]
    except (KeyError, IndexError):
        page_number = None
    f = AnimalFilter(query, queryset=reserved)
    paginator = Paginator(f.qs, 25)
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "birds/user.html",
        {
            "reserver": user,
            "filter": f,
            "query": query,
            "page_obj": page_obj,
            "animal_list": page_obj.object_list,
        },
    )


# Pairings
@require_http_methods(["GET"])
def pairing_list(request):
    qs_ped = Animal.objects.for_pedigree().values_list("uuid", "sire", "dam")
    ped = pedigree.Pedigree.from_animals(qs_ped)
    kinship = ped.get_kinship()

    qs = Pairing.objects.with_related().with_progeny_stats().order_by("-began_on")
    query = request.GET.copy()
    try:
        page_number = query.pop("page")[-1]
    except (KeyError, IndexError):
        page_number = None
    f = PairingFilter(query, queryset=qs)
    paginator = Paginator(f.qs, 25)
    page_obj = paginator.get_page(page_number)
    kinships = {
        pairing: kinship[ped.index(pairing.sire.uuid), ped.index(pairing.dam.uuid)]
        for pairing in page_obj.object_list
    }
    return render(
        request,
        "birds/pairing_list.html",
        {
            "query": query,
            "page_obj": page_obj,
            "pairing_list": page_obj.object_list,
            "kinships": kinships,
        },
    )


@require_http_methods(["GET"])
def active_pairing_list(request):
    qs_ped = Animal.objects.for_pedigree().values_list("uuid", "sire", "dam")
    ped = pedigree.Pedigree.from_animals(qs_ped)
    kinship = ped.get_kinship()
    qs = (
        Pairing.objects.with_related()
        .with_progeny_stats()
        .with_location()
        .order_by("-began_on")
    )
    f = PairingFilter(request.GET, queryset=qs)
    kinships = {
        pairing: kinship[ped.index(pairing.sire.uuid), ped.index(pairing.dam.uuid)]
        for pairing in f.qs
    }
    return render(
        request,
        "birds/pairing_list_active.html",
        {"pairing_list": f.qs, "kinships": kinships},
    )


@require_http_methods(["GET"])
def pairing_view(request, pk):
    qs = Pairing.objects.with_related().with_progeny_stats()
    pair = get_object_or_404(qs, pk=pk)
    progeny = pair.eggs().with_related().hatched().order_by_life_stage()
    eggs = pair.eggs().with_related().unhatched().order_by("created")
    pairings = pair.other_pairings().with_progeny_stats()
    events = pair.events().with_related()
    # kinship should eventually be cached to avoid all this work
    qs_ped = Animal.objects.for_pedigree().values_list("uuid", "sire", "dam")
    ped = pedigree.Pedigree.from_animals(qs_ped)
    kinship = ped.get_kinship()
    return render(
        request,
        "birds/pairing.html",
        {
            "pairing": pair,
            "animal_list": progeny,
            "egg_list": eggs,
            "pairing_list": pairings,
            "event_list": events,
            "pairing_kinship": kinship[
                ped.index(pair.sire.uuid), ped.index(pair.dam.uuid)
            ],
        },
    )


def new_pairing_entry(request, pk: int | None = None):
    if request.method == "POST":
        form = NewPairingForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if data["location"] is None:
                pair = Pairing.objects.create(
                    sire=data["sire"],
                    dam=data["dam"],
                    began_on=data["began_on"],
                    purpose=data["purpose"],
                )
            else:
                pair = Pairing.objects.create_with_events(
                    sire=data["sire"],
                    dam=data["dam"],
                    began_on=data["began_on"],
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


@require_http_methods(["GET", "POST"])
def new_pairing_egg(request, pk: int):
    pairing = get_object_or_404(Pairing, pk=pk)
    if request.method == "POST":
        form = NewEggForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            date = data["date"]
            try:
                pairing.create_egg(
                    date=date,
                    entered_by=data["user"],
                    location=pairing.last_location(on_date=date),
                    description=data.get("comments")
                    or f"manually added egg to {pairing.short_name}",
                )
            except ValueError as e:
                form.add_error(None, ValidationError(_(str(e))))
            else:
                return HttpResponseRedirect(
                    reverse("birds:pairing", args=(pairing.pk,))
                )
    else:
        form = NewEggForm()
        form.initial["user"] = request.user

    return render(
        request, "birds/pairing_egg_entry.html", {"form": form, "pairing": pairing}
    )


@require_http_methods(["GET", "POST"])
def new_pairing_event(request, pk: int):
    pairing = get_object_or_404(Pairing, pk=pk)
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if not pairing.active(data["date"]):
                form.add_error(
                    None,
                    ValidationError(
                        _("Date must be when the pairing is or was active")
                    ),
                )
            else:
                if pairing.sire.history.is_alive(on_date=data["date"]):
                    _evt = Event.objects.create(animal=pairing.sire, **data)
                if pairing.dam.history.is_alive(on_date=data["date"]):
                    _evt = Event.objects.create(animal=pairing.dam, **data)
                for bird in pairing.eggs().alive(on_date=data["date"]):
                    _evt = Event.objects.create(animal=bird, **data)
                return HttpResponseRedirect(
                    reverse("birds:pairing", args=(pairing.pk,))
                )
    else:
        form = EventForm()
        form.initial["entered_by"] = request.user

    return render(
        request, "birds/pairing_event_entry.html", {"form": form, "pairing": pairing}
    )


def close_pairing(request, pk: int):
    pairing = get_object_or_404(Pairing, pk=pk)
    if request.method == "POST":
        form = EndPairingForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # some dirty validation logic to catch errors thrown by the model
            try:
                pairing.close(
                    ended_on=data["ended_on"],
                    entered_by=data["entered_by"],
                    location=data["location"],
                    comment=data["comment"],
                    remove_unhatched=data["remove_unhatched"],
                )
                return HttpResponseRedirect(reverse("birds:pairing", args=(pk,)))
            except IntegrityError:
                form.add_error(
                    None,
                    ValidationError(
                        _("Ending date must be after beginning (%(value)s)"),
                        params={"value": pairing.began_on},
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


# Samples
@require_http_methods(["GET"])
def sample_type_list(request):
    qs = SampleType.objects.all()
    return render(request, "birds/sample_type_list.html", {"sampletype_list": qs})


@require_http_methods(["GET"])
def sample_list(request, animal: str | None = None):
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
    query = request.GET.copy()
    try:
        page_number = query.pop("page")[-1]
    except (KeyError, IndexError):
        page_number = None
    f = SampleFilter(query, queryset=qs)
    paginator = Paginator(f.qs, 25)
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "birds/sample_list.html",
        {
            "filter": f,
            "query": query,
            "page_obj": page_obj,
            "sample_list": page_obj.object_list,
        },
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
        # this needs to be formatted in a way that's compatible with the
        # datetime widget
        # form.initial["date"] = datetime.date.today()
        form.initial["collected_by"] = request.user

    return render(request, "birds/sample_entry.html", {"form": form, "animal": animal})


# Summary views
@require_http_methods(["GET"])
def location_summary(request):
    # do this with a single query and then group by location
    qs = Animal.objects.with_related().alive().order_by("life_history__last_location")
    loc_data = []
    for location, animals in groupby(
        qs, key=lambda animal: animal.history.last_location
    ):
        d = defaultdict(list)
        for animal in animals:
            age_group = animal.history.age_group()
            if age_group == ADULT_ANIMAL_NAME:
                group_name = f"{age_group} {Animal.Sex(animal.sex).label}"
                d[group_name].append(animal)
            else:
                d[age_group].append(animal)
        loc_data.append((location, sorted(d.items())))
    return render(
        request, "birds/animal_location_summary.html", {"location_list": loc_data}
    )


@require_http_methods(["GET"])
def breeding_report(request):
    default_days = 4
    try:
        until = dateparse.parse_date(request.GET["until"])
    except (ValueError, KeyError):
        until = None
    try:
        since = dateparse.parse_date(request.GET["since"])
    except (ValueError, KeyError):
        since = None
    until = until or datetime.date.today()
    since = since or (until - datetime.timedelta(days=default_days))
    if until - since > datetime.timedelta(days=9):
        raise ValueError("report cannot span more than 10 days")
    dates, pairs = tabulate_pairs(since, until)
    checks = NestCheck.objects.filter(
        datetime__date__gte=since, datetime__date__lte=until
    ).order_by("-datetime")
    return render(
        request,
        "birds/breeding_report.html",
        {
            "dates": dates,
            "pairs": pairs,
            "checks": checks,
        },
    )


@require_http_methods(["GET", "POST"])
def breeding_check(request):
    """Nest check view.

    This view is a two-stage form. With GET requests the user is shown a nest
    report for the past 3 days and is able to update egg and chick counts for
    each nest. POST requests do not get immediately committed to the database,
    but instead are used to generate a confirmation form that summarizes
    everything that will change. Submitting this form will then redirect to the
    main breeding-report page.

    """
    BreedingCheckFormSet = formset_factory(BreedingCheckForm, extra=0)
    until = datetime.date.today()

    if request.method == "POST":
        # post only needs to tabulate for today unless there's an error
        _, pairs = tabulate_pairs(until, until)
        initial = [
            {
                "pairing": p["pair"],
                "location": p["location"],
                "eggs": (n_eggs := p["counts"][0]["egg"]),
                "chicks": p["counts"][0].total() - n_eggs,
            }
            for p in pairs
        ]
        nest_formset = BreedingCheckFormSet(
            request.POST, initial=initial, prefix="nests"
        )
        user_form = NestCheckUser(request.POST, prefix="user")

        if nest_formset.is_valid():
            if not user_form.is_valid() or not user_form.cleaned_data["confirmed"]:
                # coming from the original view, show the confirmation page
                return render(
                    request,
                    "birds/breeding_check_confirm.html",
                    {
                        "nest_formset": nest_formset,
                        "user_form": user_form,
                    },
                )
            else:
                # coming from the confirmation page
                user = user_form.cleaned_data["entered_by"]
                for form in nest_formset:
                    data = form.cleaned_data
                    for hatched_egg in data["hatched_eggs"]:
                        _ = Event.objects.create(
                            animal=hatched_egg,
                            date=datetime.date.today(),
                            status=data["hatch_status"],
                            location=data["location"],
                            entered_by=user,
                        )
                    for lost_egg in data["lost_eggs"]:
                        _ = Event.objects.create(
                            animal=lost_egg,
                            date=datetime.date.today(),
                            status=data["lost_status"],
                            location=data["location"],
                            entered_by=user,
                        )
                    for _ in range(data["added_eggs"]):
                        data["pairing"].create_egg(
                            date=datetime.date.today(),
                            location=data["location"],
                            entered_by=user,
                        )
                NestCheck.objects.create(
                    entered_by=user,
                    comments=user_form.cleaned_data["comments"],
                    datetime=make_aware(datetime.datetime.now()),
                )
                return HttpResponseRedirect(reverse("birds:breeding-summary"))

    # initial view on get or errors
    since = until - datetime.timedelta(days=2)
    dates, pairs = tabulate_pairs(since, until, only_active=True)
    initial = []
    for pairing in pairs:
        today_counts = pairing["counts"][-1]
        total_count = sum(today_counts.values())
        eggs = today_counts.get("egg", 0)
        initial.append(
            {
                "pairing": pairing["pair"],
                "location": pairing["location"],
                "eggs": eggs,
                "chicks": total_count - eggs,
            }
        )
    # only create a new formset for GET requests - otherwise use the one from
    # the POST
    if request.method == "GET":
        nest_formset = BreedingCheckFormSet(initial=initial, prefix="nests")
    previous_checks = NestCheck.objects.filter(
        datetime__date__gte=(until - datetime.timedelta(days=7))
    ).order_by("-datetime")

    return render(
        request,
        "birds/breeding_check.html",
        {
            "dates": dates,
            "nest_checks": previous_checks,
            "nest_data": zip(pairs, nest_formset, strict=True),
            "nest_formset": nest_formset,
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
        .alive(refdate)
        .order_by("species", "born_on")
    )
    counter = defaultdict(lambda: defaultdict(Counter))
    for bird in birds:
        age_group = bird.history.age_group()
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
def breeding_stats_list(request):
    """A table of animals with statistics relevant to breeding strength"""
    # monster query to pull in everything we need. Only look at birds that are
    # alive or that have descendents. Latter are needed to calculate inbreeding.
    # Each bird gets a 1-based index based on creation timestamp to use in
    # calculating inbreeding. If parents are ever entered after children (which
    # can happen if placeholder parents are created when importing animals),
    # this will really mess up the inbreeding calculation, but I think it's
    # worth avoiding the topological sort.
    qs = (
        Animal.objects.with_dates()
        .annotate(nchildren=Count("children"))
        .filter(Q(alive__gt=0) | Q(nchildren__gt=0))
        .annotate(idx=Window(expression=RowNumber(), order_by=["created", "uuid"]))
        .select_related("species", "band_color")
        .prefetch_related(
            Prefetch("parents", queryset=Animal.objects.with_dates()),
            Prefetch("parents__parents", queryset=Animal.objects.with_dates()),
            Prefetch("children", queryset=Animal.objects.with_dates()),
        )
        .order_by("idx")
    )
    # lookup dict from uuids to indices for inbreeding calculation
    bird_to_idx = {a: a.idx for a in qs}
    bird_to_idx[None] = 0
    sires = [bird_to_idx[a.sire()] for a in qs]
    dams = [bird_to_idx[a.dam()] for a in qs]
    inbreeding = pedigree.inbreeding_coeffs(sires, dams)

    # filtering and pagination
    query = request.GET.copy()
    try:
        page_number = query.pop("page")[-1]
    except (KeyError, IndexError):
        page_number = None
    f = AnimalFilter(query, queryset=qs.alive())  # only living birds
    paginator = Paginator(f.qs, 25)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "birds/breeding_stats.html",
        {
            "filter": f,
            "query": query,
            "page_obj": page_obj,
            "animal_list": page_obj.object_list,
            "inbreeding": inbreeding,
        },
    )
