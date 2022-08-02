# -*- coding: utf-8 -*-
# -*- mode: python -*-
import datetime

from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_http_methods
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django_filters import rest_framework as filters
from django_filters.views import FilterView
from drf_link_header_pagination import LinkHeaderPagination

from birds import __version__, api_version
from birds.models import (
    Animal, Event, Sample, SampleType, NestCheck, Pairing, Status
)
from birds.serializers import (
    AnimalSerializer,
    AnimalPedigreeSerializer,
    AnimalDetailSerializer,
    EventSerializer,
)
from birds.forms import (
    ClutchForm,
    NewAnimalForm,
    NewBandForm,
    EventForm,
    ReservationForm,
    SampleForm,
    NewPairingForm,
    EndPairingForm,
    SexForm,
)


class LargeResultsSetPagination(LinkHeaderPagination):
    page_size = 1000
    page_size_query_param = "page_size"
    max_page_size = 10000


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


class AnimalList(FilterView):
    model = Animal
    filterset_class = AnimalFilter
    template_name = "birds/animal_list.html"
    paginate_by = 25
    strict = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.copy()
        try:
            del context["query"]["page"]
        except KeyError:
            pass
        return context


class PairingList(FilterView):
    model = Pairing
    filterset_class = PairingFilter
    template_name = "birds/pairing_list.html"
    strict = False


class PairingListActive(FilterView):
    model = Pairing
    filterset_class = PairingFilter
    template_name = "birds/pairing_list_active.html"
    strict = False

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(ended__isnull=True)


class PairingView(generic.DetailView):
    model = Pairing
    template_name = "birds/pairing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pairing = context["pairing"]
        context["animal_list"] = pairing.eggs().order_by("-alive", "-created")
        context["pairing_list"] = self.model.objects.filter(
            sire=pairing.sire, dam=pairing.dam
        ).exclude(id=pairing.id)
        context["event_list"] = pairing.related_events()
        return context


class PairingEntry(generic.FormView):
    template_name = "birds/pairing_entry.html"
    form_class = NewPairingForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pair"] = getattr(self, "pairing", None)
        return context

    def get_form(self):
        form = super().get_form()
        if "pk" in self.kwargs:
            self.pairing = get_object_or_404(Pairing, pk=self.kwargs["pk"])
            form.fields["sire"].queryset = Animal.objects.filter(
                uuid=self.pairing.sire.uuid
            )
            form.initial["sire"] = self.pairing.sire
            form.fields["dam"].queryset = Animal.objects.filter(
                uuid=self.pairing.dam.uuid
            )
            form.initial["dam"] = self.pairing.dam
        form.initial["entered_by"] = self.request.user
        return form

    def form_valid(self, form, **kwargs):
        from birds.models import Status, MOVED_EVENT_NAME

        data = form.clean()
        if data["location"] is not None and data["entered_by"] is not None:
            try:
                move_status = Status.objects.get(name=MOVED_EVENT_NAME)
            except ObjectDoesNotExist:
                print(
                    f"Unable to create move events - no {MOVED_EVENT_NAME} status type"
                )
            else:
                sire_event = Event(
                    animal=data["sire"],
                    date=data["began"],
                    status=move_status,
                    location=data["location"],
                    entered_by=data["entered_by"],
                    description=f"Paired with {data['dam']}",
                )
                dam_event = Event(
                    animal=data["dam"],
                    date=data["began"],
                    status=move_status,
                    location=data["location"],
                    entered_by=data["entered_by"],
                    description=f"Paired with {data['sire']}",
                )
                sire_event.save()
                dam_event.save()
        pairing = Pairing(
            sire=data["sire"],
            dam=data["dam"],
            began=data["began"],
            purpose=data["purpose"],
            ended=None,
        )
        pairing.save()
        return HttpResponseRedirect(reverse("birds:pairing", args=(pairing.pk,)))


class PairingClose(generic.FormView):
    template_name = "birds/pairing_close.html"
    form_class = EndPairingForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pair"] = self.pairing
        return context

    def get_form(self):
        form = super().get_form()
        self.pairing = get_object_or_404(Pairing, pk=self.kwargs["pk"])
        form.initial["began"] = self.pairing.began
        form.initial["entered_by"] = self.request.user
        # users should not be accessing this form for inactive pairings, but
        # make sure the fields are populated if it is
        form.initial["ended"] = self.pairing.ended
        form.initial["comment"] = self.pairing.comment
        return form

    def form_valid(self, form, **kwargs):
        from birds.models import Status, MOVED_EVENT_NAME

        data = form.clean()
        if (
            self.pairing.ended is None
            and data["location"] is not None
            and data["entered_by"] is not None
        ):
            try:
                move_status = Status.objects.get(name=MOVED_EVENT_NAME)
            except ObjectDoesNotExist:
                print(
                    f"Unable to create move events - no {MOVED_EVENT_NAME} status type"
                )
            else:
                sire_event = Event(
                    animal=self.pairing.sire,
                    date=data["ended"],
                    status=move_status,
                    location=data["location"],
                    entered_by=data["entered_by"],
                    description=f"Ended pairing with {self.pairing.dam}",
                )
                dam_event = Event(
                    animal=self.pairing.dam,
                    date=data["ended"],
                    status=move_status,
                    location=data["location"],
                    entered_by=data["entered_by"],
                    description=f"Ended pairing with {self.pairing.sire}",
                )
                sire_event.save()
                dam_event.save()
        self.pairing.ended = data["ended"]
        self.pairing.comment = data["comment"]
        self.pairing.save()
        return HttpResponseRedirect(reverse("birds:pairing", args=(self.pairing.pk,)))


class LocationSummary(generic.ListView):
    model = Event
    template_name = "birds/animal_location_summary.html"

    def get_queryset(self):
        alive = Animal.living.all()
        return Event.latest.filter(animal__in=alive)

    def sort_and_group(self, qs):
        from collections import defaultdict
        from birds.tools import sort_and_group
        from birds.models import ADULT_ANIMAL_NAME

        sex_choices = dict(Animal.SEX_CHOICES)
        loc_data = []
        for location, events in sort_and_group(qs, key=lambda evt: evt.location.name):
            d = defaultdict(list)
            for event in events:
                animal = event.animal
                age_group = animal.age_group()
                if age_group == ADULT_ANIMAL_NAME:
                    group_name = "{} {}".format(age_group, sex_choices[animal.sex])
                    d[group_name].append(animal)
                else:
                    d[age_group].append(animal)
            loc_data.append((location, sorted(d.items())))
        return loc_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        latest = context["object_list"]
        context["location_list"] = self.sort_and_group(latest)
        return context


class NestReport(generic.TemplateView):
    default_days = 4
    template_name = "birds/nest_report.html"

    def get_context_data(self, **kwargs):
        from django.utils import dateparse
        from datetime import datetime, timedelta
        from birds.tools import tabulate_locations

        context = super().get_context_data(**kwargs)
        try:
            until = dateparse.parse_date(self.request.GET["until"])
        except (ValueError, KeyError):
            until = None
        try:
            since = dateparse.parse_date(self.request.GET["since"])
        except (ValueError, KeyError):
            since = None
        until = until or datetime.now().date()
        since = since or (until - timedelta(days=self.default_days))
        dates, nest_data = tabulate_locations(since, until)
        checks = NestCheck.objects.filter(
            datetime__date__gte=since, datetime__date__lte=until
        ).order_by("datetime")
        context.update(
            since=since,
            until=until,
            dates=dates,
            nest_data=nest_data,
            nest_checks=checks,
        )
        return context


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
    from datetime import datetime, timedelta
    from collections import defaultdict
    from django.forms import formset_factory, ValidationError
    from birds.forms import NestCheckForm, NestCheckUser
    from birds.tools import tabulate_locations

    NestCheckFormSet = formset_factory(NestCheckForm, extra=0)
    until = datetime.now().date()
    since = until - timedelta(days=2)
    dates, nest_data = tabulate_locations(since, until)
    initial = []
    previous_checks = NestCheck.objects.filter(
        datetime__date__gte=(until - timedelta(days=7))
    ).order_by("datetime")
    for nest in nest_data:
        today_counts = nest["days"][-1]["counts"]
        total_count = sum(today_counts.values())
        eggs = today_counts["egg"]
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
                # most of the validation logic to keep users from removing any
                # animals is in the form; but we do checks against current
                # occupants here
                delta_chicks = updated["chicks"] - initial["chicks"]
                delta_eggs = updated["eggs"] - initial["eggs"] + delta_chicks
                if delta_eggs > 0:
                    adults = nest["days"][-1]["animals"]["adult"]
                    if len(adults) > 2:
                        nest_form.add_error(
                            None, ValidationError("unable to add egg - too many adults")
                        )
                    else:
                        try:
                            sire = next(
                                (
                                    animal
                                    for animal in adults
                                    if animal.sex == Animal.MALE
                                )
                            )
                        except StopIteration:
                            nest_form.add_error(
                                None, ValidationError("unable to add egg - no sire")
                            )
                        try:
                            dam = next(
                                (
                                    animal
                                    for animal in adults
                                    if animal.sex == Animal.FEMALE
                                )
                            )
                        except StopIteration:
                            nest_form.add_error(
                                None, ValidationError("unable to add egg - no dam")
                            )
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
                for i in range(delta_chicks):
                    hatch = dict(
                        animal=eggs.pop(),
                        status=updated["hatch_status"],
                        location=location,
                    )
                    changes[location].append(hatch)
                if delta_eggs < 0:
                    for i in range(-delta_eggs):
                        lost = dict(
                            animal=eggs.pop(),
                            status=updated["lost_status"],
                            location=location,
                        )
                        changes[location].append(lost)
                else:
                    for i in range(delta_eggs):
                        egg = dict(
                            status=updated["laid_status"],
                            sire=sire,
                            dam=dam,
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
                            event = Event(
                                date=datetime.now().date(), entered_by=user, **item
                            )
                            event.save()
                        elif item["status"] == updated["laid_status"]:
                            animal = Animal(
                                species=item["sire"].species, sex=Animal.UNKNOWN_SEX
                            )
                            animal.save()
                            animal.parents.set([item["sire"], item["dam"]])
                            animal.save()
                            event = Event(
                                animal=animal,
                                date=datetime.now().date(),
                                entered_by=user,
                                status=item["status"],
                                location=item["location"],
                            )
                            event.save()
                check = NestCheck(
                    entered_by=user, comments=user_form.cleaned_data["comments"]
                )
                check.save()
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


class EventList(FilterView, generic.list.MultipleObjectMixin):
    model = Event
    filterset_class = EventFilter
    template_name = "birds/event_list.html"
    paginate_by = 25
    strict = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.copy()
        try:
            del context["query"]["page"]
        except KeyError:
            pass
        return context

    def get_queryset(self):
        qs = Event.objects.filter(**self.kwargs)
        return qs.order_by("-date", "-created")


class AnimalView(generic.DetailView):
    model = Animal
    template_name = "birds/animal.html"
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        animal = context["animal"]
        context["animal_list"] = animal.children.order_by("-alive", "-created")
        context["event_list"] = animal.event_set.order_by("-date", "-created")
        context["sample_list"] = animal.sample_set.order_by("-date")
        context["pairing_list"] = animal.pairings().order_by("-began")
        return context


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
            Animal.objects.filter(parents__parents=animal, event__status__adds=True).order_by("-alive"),
            Animal.objects.filter(parents__parents__parents=animal, event__status__adds=True).order_by("-alive"),
            Animal.objects.filter(parents__parents__parents__parents=animal, event__status__adds=True).order_by("-alive"),
        ]
        context["living"] = [qs.filter(alive=True) for qs in context["descendents"]]
        return context


class ClutchEntry(generic.FormView):
    template_name = "birds/clutch_entry.html"
    form_class = ClutchForm

    def get_form(self):
        form = super().get_form()
        try:
            uuid = self.kwargs["uuid"]
            animal = Animal.objects.get(uuid=uuid)
            if animal.sex == Animal.MALE:
                form.fields["sire"].queryset = Animal.objects.filter(uuid=uuid)
                form.initial["sire"] = animal
            elif animal.sex == Animal.FEMALE:
                form.fields["dam"].queryset = Animal.objects.filter(uuid=uuid)
                form.initial["dam"] = animal
        except (KeyError, ObjectDoesNotExist):
            pass
        return form

    def get_initial(self):
        initial = super().get_initial()
        initial["user"] = self.request.user
        return initial

    def form_valid(self, form, **kwargs):
        """For valid entries, render a page with a list of the created events"""
        objs = form.create_clutch()
        return render(
            self.request,
            "birds/event_list.html",
            {
                "event_list": objs["events"],
                "header_text": "Hatch events for new clutch",
            },
        )


class NewAnimalEntry(generic.FormView):
    template_name = "birds/animal_entry.html"
    form_class = NewAnimalForm

    def get_initial(self):
        initial = super().get_initial()
        initial["user"] = self.request.user
        return initial

    def form_valid(self, form, **kwargs):
        chick = form.create_chick()
        return HttpResponseRedirect(reverse("birds:animal", args=(chick.pk,)))


class NewBandEntry(generic.FormView):
    template_name = "birds/band_entry.html"
    form_class = NewBandForm

    def get_form(self):
        form = super().get_form()
        form.initial["user"] = self.request.user
        try:
            uuid = self.kwargs["uuid"]
            form.fields["animal"].queryset = Animal.objects.filter(uuid=uuid)
            animal = Animal.objects.get(uuid=uuid)
            form.initial["animal"] = animal
            form.initial["sex"] = animal.sex
        except (KeyError, ObjectDoesNotExist):
            pass
        return form

    def form_valid(self, form, **kwargs):
        animal = form.add_band()
        return HttpResponseRedirect(reverse("birds:animal", args=(animal.pk,)))


class EventEntry(generic.FormView):
    template_name = "birds/event_entry.html"
    form_class = EventForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.animal = get_object_or_404(Animal, uuid=self.kwargs["uuid"])
        context["animal"] = self.animal
        return context

    def get_initial(self):
        initial = super().get_initial()
        initial["entered_by"] = self.request.user
        return initial

    def form_valid(self, form, **kwargs):
        event = form.save(commit=False)
        event.animal = get_object_or_404(Animal, uuid=self.kwargs["uuid"])
        event = form.save()
        return HttpResponseRedirect(reverse("birds:animal", args=(event.animal.pk,)))


class ReservationEntry(generic.FormView):
    template_name = "birds/reservation_entry.html"
    form_class = ReservationForm

    def get_form(self):
        form = super().get_form()
        try:
            uuid = self.kwargs["uuid"]
            form.fields["animal"].queryset = Animal.objects.filter(uuid=uuid)
            animal = Animal.objects.get(uuid=uuid)
            form.initial["animal"] = animal
            if animal.reserved_by is None:
                form.initial["entered_by"] = self.request.user
        except (KeyError, ObjectDoesNotExist):
            pass
        return form

    def form_valid(self, form, **kwargs):
        data = form.cleaned_data
        animal = data["animal"]
        animal.reserved_by = data["entered_by"]
        if animal.reserved_by is None:
            user = self.request.user
            descr = f"reservation released: {data['description']}"
        else:
            user = animal.reserved_by
            descr = f"reservation created: {data['description']}"
        evt = Event(
            animal=animal,
            date=data["date"],
            status=data["status"],
            entered_by=user,
            description=descr,
        )
        animal.save()
        evt.save()
        return HttpResponseRedirect(reverse("birds:animal", args=(animal.pk,)))


class SexEntry(generic.FormView):
    template_name = "birds/sex_entry.html"
    form_class = SexForm

    def get_form(self):
        form = super().get_form()
        try:
            uuid = self.kwargs["uuid"]
            form.fields["animal"].queryset = Animal.objects.filter(uuid=uuid)
            animal = Animal.objects.get(uuid=uuid)
            form.initial["animal"] = animal
            form.initial["sex"] = animal.sex
        except (KeyError, ObjectDoesNotExist):
            pass
        form.initial["entered_by"] = self.request.user
        return form

    def form_valid(self, form, **kwargs):
        animal = form.update_sex()
        return HttpResponseRedirect(reverse("birds:animal", args=(animal.pk,)))


class IndexView(generic.base.TemplateView):
    template_name = "birds/index.html"

    def get_context_data(self, **kwargs):
        today = datetime.date.today()
        return {
            "today": today,
            "lastmonth": today.replace(day=1) - datetime.timedelta(days=1),
        }


class EventSummary(generic.base.TemplateView):
    template_name = "birds/summary.html"

    def get_context_data(self, **kwargs):
        from collections import Counter

        tots = Counter()
        year, month = map(int, self.args[:2])
        # aggregation by month does not appear to work properly with postgres
        # backend, so we have to do it in python. Event counts per month will be
        # relatively small, though, so shouldn't be too slow.
        for event in Event.objects.filter(date__year=year, date__month=month):
            tots[event.status.name] += 1
        return {
            "year": year,
            "month": month,
            "next": datetime.date(year, month, 1) + datetime.timedelta(days=32),
            "prev": datetime.date(year, month, 1) - datetime.timedelta(days=1),
            "event_totals": dict(tots),
        }


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


class SampleTypeList(generic.ListView):
    model = SampleType
    template_name = "birds/sample_type_list.html"


class SampleList(FilterView):
    model = Sample
    filterset_class = SampleFilter
    template_name = "birds/sample_list.html"
    paginate_by = 25
    strict = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.copy()
        try:
            del context["query"]["page"]
        except KeyError:
            pass
        return context

    def get_queryset(self):
        qs = Sample.objects.filter(**self.kwargs)
        return qs.order_by("-date")


class SampleView(generic.DetailView):
    model = Sample
    template_name = "birds/sample.html"
    slug_field = "uuid"
    slug_url_kwarg = "uuid"


class SampleEntry(generic.FormView):
    template_name = "birds/sample_entry.html"
    form_class = SampleForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["animal"] = self.animal
        return context

    def get_form(self):
        form = super().get_form()
        self.animal = get_object_or_404(Animal, uuid=self.kwargs["uuid"])
        form.fields["source"].queryset = Sample.objects.filter(animal=self.animal)
        return form

    def get_initial(self):
        initial = super().get_initial()
        initial["collected_by"] = self.request.user
        return initial

    def form_valid(self, form, **kwargs):
        sample = form.save(commit=False)
        sample.animal = self.animal
        sample.save()
        return HttpResponseRedirect(reverse("birds:animal", args=(sample.animal.pk,)))


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
    queryset = Animal.objects.all()
    serializer_class = AnimalSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AnimalFilter


class APIAnimalChildList(APIAnimalsList):
    """List all the children of an animal"""

    def get_object(self):
        return get_object_or_404(Animal, uuid=self.kwargs["pk"])

    def get_queryset(self):
        animal = self.get_object()
        return animal.children.all()


class APIAnimalDetail(generics.RetrieveAPIView):
    queryset = Animal.objects.all()
    serializer_class = AnimalDetailSerializer


class APIEventsList(generics.ListAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = EventFilter


class APIAnimalPedigree(generics.ListAPIView):
    """A list of animals and their parents.

    If query param restrict is False, includes all animals, not just those useful in constructing a pedigree."""

    serializer_class = AnimalPedigreeSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AnimalFilter
    pagination_class = LargeResultsSetPagination

    def get_queryset(self):
        from django.db.models import Count, Q

        if self.request.GET.get("restrict", True):
            qs = Animal.objects.annotate(nchildren=Count("children")).filter(
                Q(alive__gt=0) | Q(nchildren__gt=0)
            )
        else:
            qs = Animal.objects.all()
        return qs


# Create your views here.
