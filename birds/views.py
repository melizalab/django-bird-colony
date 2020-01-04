# -*- coding: utf-8 -*-
# -*- mode: python -*-
import datetime

from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.db.models import Count, Q
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django_filters import rest_framework as filters
from django_filters.views import FilterView
from drf_link_header_pagination import LinkHeaderPagination

from birds import __version__, api_version
from birds.models import Animal, Event, Sample, SampleType
from birds.serializers import AnimalSerializer, AnimalPedigreeSerializer, AnimalDetailSerializer, EventSerializer
from birds.forms import ClutchForm, NewAnimalForm, NewBandForm, LivingEventForm, EventForm, SampleForm
from birds.tools import sort_and_group, classify_ages, tabulate_animals


class LargeResultsSetPagination(LinkHeaderPagination):
    page_size = 1000
    page_size_query_param = 'page_size'
    max_page_size = 10000


class AnimalFilter(filters.FilterSet):
    uuid = filters.CharFilter(field_name="uuid", lookup_expr="istartswith")
    color = filters.CharFilter(field_name="band_color__name", lookup_expr="iexact")
    band = filters.NumberFilter(field_name="band_number", lookup_expr="exact")
    species = filters.CharFilter(field_name="species__code", lookup_expr="iexact")
    plumage = filters.CharFilter(field_name="plumage__name", lookup_expr="icontains")
    living = filters.BooleanFilter(field_name="alive", method="is_alive")
    available = filters.BooleanFilter(field_name="reserved_by", lookup_expr="isnull")
    reserved_by = filters.CharFilter(field_name="reserved_by__username", lookup_expr="iexact")
    parent = filters.CharFilter(field_name="parents__uuid", lookup_expr="istartswith")
    child = filters.CharFilter(field_name="children__uuid", lookup_expr="istartswith")

    def is_alive(self, queryset, name, value):
        return queryset.filter(alive__gt=0)

    class Meta:
        model = Animal
        fields = ['sex']


class EventFilter(filters.FilterSet):
    animal = filters.CharFilter(field_name="animal__uuid", lookup_expr="istartswith")
    color = filters.CharFilter(field_name="animal__band_color__name", lookup_expr="iexact")
    band = filters.NumberFilter(field_name="animal__band_number", lookup_expr="exact")
    species = filters.CharFilter(field_name="animal__species__code", lookup_expr="iexact")
    status = filters.CharFilter(field_name="status__name", lookup_expr="istartswith")
    location = filters.CharFilter(field_name="location__name", lookup_expr="icontains")
    entered_by = filters.CharFilter(field_name="entered_by__username", lookup_expr="icontains")
    description = filters.CharFilter(field_name="description", lookup_expr="icontains")

    class Meta:
        model = Event
        fields = {
            'date': ['exact', 'year', 'range'],
        }


class EventDate(filters.FilterSet):
    class Meta:
        model = Event
        fields = {
            'date': ['range', 'gt'],
        }


class AnimalList(FilterView):
    model = Animal
    filterset_class = AnimalFilter
    template_name = "birds/animal_list.html"
    paginate_by = 25
    strict = False

    def get_context_data(self, **kwargs):
        context = super(AnimalList, self).get_context_data(**kwargs)
        context['query'] = self.request.GET.copy()
        try:
            del context['query']['page']
        except KeyError:
            pass
        return context


class AnimalLocationList(generic.ListView):
    model = Event
    template_name = "birds/animal_location_list.html"

    def get_queryset(self):
        alive = Animal.living.all()
        return Event.latest.filter(animal__in=alive)

    def sort_and_group(self, qs):
        from operator import attrgetter
        animalgetter = attrgetter("animal")
        loc_data = []
        for location, events in sort_and_group(qs, key=lambda evt: evt.location.name):
            animals = tuple(classify_ages(map(animalgetter, events)))
            males = tuple(animal for animal, age in animals if age == "adult" and animal.sex == Animal.MALE)
            females = tuple(animal for animal, age in animals if age == "adult" and animal.sex == Animal.FEMALE)
            juvs = tuple(animal for animal, age in animals if age != "adult")
            loc_data.append({"location": location, "males": males, "females": females, "juveniles": juvs})
        return loc_data


class LocationSummary(AnimalLocationList):
    template_name = "birds/animal_location_summary.html"

    def get_context_data(self, **kwargs):
        context = super(LocationSummary, self).get_context_data(**kwargs)
        latest = context['object_list']
        context['location_list'] = self.sort_and_group(latest)
        return context


class NestReport(AnimalLocationList):
    n_days = 7
    template_name = "birds/nest_check.html"

    def get_context_data(self, **kwargs):
        context = super(NestReport, self).get_context_data(**kwargs)
        n_days = self.request.GET.get("days", self.n_days)
        today = datetime.date.today()
        data = []
        for i in range(n_days):
            date = today - datetime.timedelta(days=i)
            alive = Animal.living.before(date)
            latest = Event.latest.filter(animal__in=alive)
            data.append({"date": date, "locations": self.sort_and_group(latest)})
        context['location_list'] = data
        print(data)
        return context


class EventList(FilterView, generic.list.MultipleObjectMixin):
    model = Event
    filterset_class = EventFilter
    template_name = "birds/event_list.html"
    paginate_by = 25
    strict = False

    def get_context_data(self, **kwargs):
        context = super(EventList, self).get_context_data(**kwargs)
        context['query'] = self.request.GET.copy()
        try:
            del context['query']['page']
        except KeyError:
            pass
        return context

    def get_queryset(self):
        qs = Event.objects.filter(**self.kwargs)
        return qs.order_by("-date")


class AnimalView(generic.DetailView):
    model = Animal
    template_name = 'birds/animal.html'
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_context_data(self, **kwargs):
        context = super(AnimalView, self).get_context_data(**kwargs)
        animal = context['animal']
        context['animal_list'] = animal.children.order_by("-alive", "-created")
        context['event_list'] = animal.event_set.order_by("-date")
        context['sample_list'] = animal.sample_set.order_by("-date")
        return context


class ClutchEntry(generic.FormView):
    template_name = "birds/clutch_entry.html"
    form_class = ClutchForm

    def get_form(self):
        form = super(ClutchEntry, self).get_form()
        try:
            uuid = self.kwargs["uuid"]
            animal = Animal.objects.get(uuid=uuid)
            if animal.sex == Animal.MALE:
                form.fields['sire'].queryset = Animal.objects.filter(uuid=uuid)
                form.initial['sire'] = animal
            elif animal.sex == Animal.FEMALE:
                form.fields['dam'].queryset = Animal.objects.filter(uuid=uuid)
                print(form.fields)
                form.initial['dam'] = animal
        except (KeyError, ObjectDoesNotExist):
            pass
        return form

    def get_initial(self):
        initial = super(ClutchEntry, self).get_initial()
        initial["user"] = self.request.user
        return initial

    def form_valid(self, form, **kwargs):
        """ For valid entries, render a page with a list of the created events """
        objs = form.create_clutch()
        return render(self.request, 'birds/event_list.html',
                      {'event_list': objs['events'],
                       'header_text': 'Hatch events for new clutch'})


class NewAnimalEntry(generic.FormView):
    template_name = "birds/animal_entry.html"
    form_class = NewAnimalForm

    def get_initial(self):
        initial = super(NewAnimalEntry, self).get_initial()
        initial["user"] = self.request.user
        return initial

    def form_valid(self, form, **kwargs):
        chick = form.create_chick()
        return HttpResponseRedirect(reverse('birds:animal', args=(chick.pk,)))


class NewBandEntry(generic.FormView):
    template_name = "birds/band_entry.html"
    form_class = NewBandForm

    def get_form(self):
        form = super(NewBandEntry, self).get_form()
        try:
            uuid = self.kwargs["uuid"]
            form.fields['animal'].queryset = Animal.objects.filter(uuid=uuid)
            animal = Animal.objects.get(uuid=uuid)
            form.initial['animal'] = animal
            form.initial['sex'] = animal.sex
        except (KeyError, ObjectDoesNotExist):
            pass
        return form

    def get_initial(self):
        initial = super(NewBandEntry, self).get_initial()
        initial["user"] = self.request.user
        return initial

    def form_valid(self, form, **kwargs):
        animal = form.add_band()
        return HttpResponseRedirect(reverse('birds:animal', args=(animal.pk,)))


class EventEntry(generic.FormView):
    template_name = "birds/event_entry.html"
    form_class = EventForm

    def get_context_data(self, **kwargs):
        context = super(EventEntry, self).get_context_data(**kwargs)
        self.animal = get_object_or_404(Animal, uuid=self.kwargs["uuid"])
        context["animal"] = self.animal
        return context

    def get_initial(self):
        initial = super(EventEntry, self).get_initial()
        initial['entered_by'] = self.request.user
        return initial

    def form_valid(self, form, **kwargs):
        event = form.save(commit=False)
        event.animal = get_object_or_404(Animal, uuid=self.kwargs["uuid"])
        event = form.save()
        return HttpResponseRedirect(reverse('birds:animal', args=(event.animal.pk,)))


class LivingEventEntry(EventEntry):
    form_class = LivingEventForm


class IndexView(generic.base.TemplateView):
    template_name = "birds/index.html"

    def get_context_data(self, **kwargs):
        today = datetime.date.today()
        return {
            "today": today,
            "lastmonth": today.replace(day=1) - datetime.timedelta(days=1)
        }


class EventSummary(generic.base.TemplateView):
    template_name = "birds/summary.html"

    def get_context_data(self, **kwargs):
        from collections import Counter
        tots = Counter()
        year, month = map(int, self.args[:2])
        # aggregation by month does not appear to work properly with postgres
        # backend. Event counts per month will be relatively small, so this
        # shouldn't be too slow
        for event in Event.objects.filter(date__year=year, date__month=month):
            tots[event.status.name] += 1
        return {
            "year": year,
            "month": month,
            "next": datetime.date(year, month, 1) + datetime.timedelta(days=32),
            "prev": datetime.date(year, month, 1) - datetime.timedelta(days=1),
            "event_totals": dict(tots)
        }


class SampleFilter(filters.FilterSet):
    uuid = filters.CharFilter(field_name="uuid", lookup_expr="istartswith")
    type = filters.CharFilter(field_name="type__name", lookup_expr="istartswith")
    location = filters.CharFilter(field_name="location__name", lookup_expr="istartswith")
    available = filters.BooleanFilter(field_name="location", method="is_available")
    color = filters.CharFilter(field_name="animal__band_color__name", lookup_expr="iexact")
    band = filters.NumberFilter(field_name="animal__band_number", lookup_expr="exact")
    species = filters.CharFilter(field_name="animal__species__code", lookup_expr="iexact")
    collected_by = filters.CharFilter(field_name="collected_by__username", lookup_expr="iexact")

    def is_available(self, queryset, name, value):
        return queryset.exclude(location__isnull=True)

    class Meta:
        model = Sample
        fields = {
            'date': ['exact', 'year', 'range'],
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
        context = super(SampleList, self).get_context_data(**kwargs)
        context['query'] = self.request.GET.copy()
        try:
            del context['query']['page']
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
        context = super(SampleEntry, self).get_context_data(**kwargs)
        context["animal"] = self.animal
        return context

    def get_form(self):
        form = super(SampleEntry, self).get_form()
        self.animal = get_object_or_404(Animal, uuid=self.kwargs["uuid"])
        form.fields["source"].queryset = Sample.objects.filter(animal=self.animal)
        return form

    def get_initial(self):
        initial = super(SampleEntry, self).get_initial()
        initial['collected_by'] = self.request.user
        return initial

    def form_valid(self, form, **kwargs):
        sample = form.save(commit=False)
        sample.animal = self.animal
        sample.save()
        return HttpResponseRedirect(reverse('birds:animal', args=(sample.animal.pk,)))


### API
@api_view(['GET'])
def api_info(request, format=None):
    return Response({
        'name': 'django-bird-colony',
        'version': __version__,
        'api_version': api_version
    })


class APIAnimalsList(generics.ListAPIView):
    queryset = Animal.objects.all()
    serializer_class = AnimalSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AnimalFilter


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
        if self.request.GET.get("restrict", True):
            qs = Animal.objects.annotate(
                nchildren=Count('children')).filter(Q(alive__gt=0) | Q(nchildren__gt=0))
        else:
            qs = Animal.objects.all()
        return qs


# Create your views here.
