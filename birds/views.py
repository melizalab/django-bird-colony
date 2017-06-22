# -*- coding: utf-8 -*-
# -*- mode: python -*-
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.views import generic
from django.db.models import Min
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
import django_filters
import datetime

from birds.models import Animal, Event
from birds.serializers import AnimalSerializer, EventSerializer
from birds.forms import ClutchForm, BandingForm

class BirdFilter(django_filters.FilterSet):
    class Meta:
        model = Animal
        fields = {
            'sex': ['exact'],
            'band_color': ['exact'],
            'species__code': ['exact'],
        }


class EventFilter(django_filters.FilterSet):
    class Meta:
        model = Event
        fields = {
            'animal__uuid': ['exact','contains'],
            'location__name': ['exact', 'contains'],
            'date': ['exact', 'year', 'range'],
            'entered_by': ['exact'],
        }


def bird_list(request, living=None):
    if living:
        qs = Animal.living.annotate(acq_date=Min("event__date")).order_by("acq_date")
    else:
        qs = Animal.objects.all()
    f = BirdFilter(request.GET, queryset=qs)
    return render(request, 'birds/birds.html', {'bird_list': f.qs})


def event_list(request):
    f = EventFilter(request.GET, Event.objects.all())
    paginator = Paginator(f.qs, 25)
    page = request.GET.get('page')
    try:
        events = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        events = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        events = paginator.page(paginator.num_pages)
    return render(request, 'birds/events.html', {'event_list': events})


class BirdView(generic.DetailView):
    model = Animal
    template_name = 'birds/bird.html'
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_context_data(self, **kwargs):
        context = super(BirdView, self).get_context_data(**kwargs)
        animal = context['animal']
        context['bird_list'] = animal.children.all()
        context['event_list'] = animal.event_set.all()
        return context


class ClutchEntry(generic.FormView):
    template_name = "birds/clutch_entry.html"
    form_class = ClutchForm

    def form_valid(self, form, **kwargs):
        """ For valid entries, render a page with a list of the created events """
        objs = form.create_clutch()
        return render(self.request, 'birds/events.html',
                      { 'event_list': objs['events'],
                        'header_text': 'Hatch events for new clutch'})


class BandingEntry(generic.FormView):
    template_name = "birds/banding_entry.html"
    form_class = BandingForm

    def form_valid(self, form, **kwargs):
        chick = form.create_chick()
        return HttpResponseRedirect(reverse('birds:bird', args=(chick.pk,)))


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

@api_view(['GET', 'POST'])
def all_birds_json(request):
    if request.method == 'GET':
        birds = Animal.objects.all()
        serializer = AnimalSerializer(birds, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = AnimalSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def all_events_json(request):
    if request.method == 'GET':
        events = Event.objects.all()
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = EventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Create your views here.
