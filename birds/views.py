# -*- coding: utf-8 -*-
# -*- mode: python -*-
import datetime

from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.views import generic
from django.db.models import Min
from rest_framework import generics
from rest_framework.response import Response
from django_filters import rest_framework as filters
from django_filters.views import FilterView

from birds.models import Animal, Event
from birds.serializers import AnimalSerializer, AnimalDetailSerializer, EventSerializer
from birds.forms import ClutchForm, BandingForm, EventForm


class AnimalFilter(filters.FilterSet):
    uuid = filters.CharFilter(name="uuid", lookup_expr="istartswith")
    color = filters.CharFilter(name="band_color__name", lookup_expr="iexact")
    band = filters.NumberFilter(name="band_number", lookup_expr="exact")
    species = filters.CharFilter(name="species__code", lookup_expr="iexact")
    sex = filters.CharFilter(name="sex", lookup_expr="iexact")
    available = filters.BooleanFilter(name="reserved_by", lookup_expr="isnull")
    reserved_by = filters.CharFilter(name="reserved_by__username", lookup_expr="iexact")
    parent = filters.CharFilter(name="parents__uuid", lookup_expr="istartswith")
    child = filters.CharFilter(name="children__uuid", lookup_expr="istartswith")

    class Meta:
        model = Animal
        fields = []


class EventFilter(filters.FilterSet):
    animal = filters.CharFilter(name="animal__uuid", lookup_expr="istartswith")
    color = filters.CharFilter(name="animal__band_color__name", lookup_expr="iexact")
    band = filters.NumberFilter(name="animal__band_number", lookup_expr="exact")
    species = filters.CharFilter(name="animal__species__code", lookup_expr="iexact")
    location = filters.CharFilter(name="location__name", lookup_expr="icontains")
    entered_by = filters.CharFilter(name="entered_by__username", lookup_expr="icontains")
    description = filters.CharFilter(name="description", lookup_expr="icontains")

    class Meta:
        model = Event
        fields = {
            'date': ['exact', 'year', 'range'],
        }


class AnimalList(FilterView):
    model = Animal
    filterset_class = AnimalFilter
    template_name = "birds/animal_list.html"

    def get_queryset(self):
        if self.request.GET.get("living", False):
            qs = Animal.living.annotate(acq_date=Min("event__date")).order_by("acq_date")
        else:
            qs = Animal.objects.all()
        return qs


class EventList(FilterView, generic.list.MultipleObjectMixin):
    model = Event
    filterset_class = EventFilter
    template_name = "birds/event_list.html"
    paginate_by = 25

    def get_queryset(self):
        qs = Event.objects.filter(**self.kwargs)
        return qs


class AnimalView(generic.DetailView):
    model = Animal
    template_name = 'birds/animal.html'
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_context_data(self, **kwargs):
        context = super(AnimalView, self).get_context_data(**kwargs)
        animal = context['animal']
        context['animal_list'] = animal.children.all()
        context['event_list'] = animal.event_set.all()
        return context


class ClutchEntry(generic.FormView):
    template_name = "birds/clutch_entry.html"
    form_class = ClutchForm

    def get_initial(self):
        initial = super(ClutchEntry, self).get_initial()
        initial["user"] = self.request.user
        return initial

    def form_valid(self, form, **kwargs):
        """ For valid entries, render a page with a list of the created events """
        objs = form.create_clutch()
        return render(self.request, 'birds/events.html',
                      { 'event_list': objs['events'],
                        'header_text': 'Hatch events for new clutch'})


class BandingEntry(generic.FormView):
    template_name = "birds/banding_entry.html"
    form_class = BandingForm

    def get_initial(self):
        initial = super(BandingEntry, self).get_initial()
        initial["user"] = self.request.user
        return initial

    def form_valid(self, form, **kwargs):
        chick = form.create_chick()
        return HttpResponseRedirect(reverse('birds:animal', args=(chick.pk,)))


class EventEntry(generic.FormView):
    template_name = "birds/event_entry.html"
    form_class = EventForm

    def get_initial(self):
        initial = super(EventEntry, self).get_initial()
        try:
            uuid = self.kwargs["uuid"]
            animal = Animal.objects.get(uuid=uuid)
            initial['animal'] = animal
        except:
            pass
        initial['entered_by'] = self.request.user
        return initial

    def form_valid(self, form, **kwargs):
        event = form.save()
        return HttpResponseRedirect(reverse('birds:animal', args=(event.animal.pk,)))


class IndexView(generic.base.TemplateView):
    template_name = "birds/index.html"

    def get_context_data(self, **kwargs):
        today = datetime.date.today()
        return {"today": today,
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
        return { "year": year,
                 "month": month,
                 "next": datetime.date(year, month, 1) + datetime.timedelta(days=32),
                 "prev": datetime.date(year, month, 1) - datetime.timedelta(days=1),
                 "event_totals": dict(tots) }

### API

class APIAnimalsList(generics.ListAPIView):
    queryset = Animal.objects.all()
    serializer_class = AnimalSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = AnimalFilter

    def get_queryset(self):
        if self.request.GET.get("living", False):
            qs = Animal.living.annotate(acq_date=Min("event__date")).order_by("acq_date")
        else:
            qs = Animal.objects.all()
        return qs


class APIAnimalDetail(generics.RetrieveAPIView):
    queryset = Animal.objects.all()
    serializer_class = AnimalDetailSerializer


class APIEventsList(generics.ListAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = EventFilter


# Create your views here.
