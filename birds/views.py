from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.core.serializers.python import Serializer
from django.core.serializers.json import DjangoJSONEncoder
from django.views import generic
from django.db.models import Min
import django_filters
import datetime
import json

from birds.models import Animal, Event, Recording
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


class RecordingFilter(django_filters.FilterSet):
    class Meta:
        model = Recording
        fields = {
            'animal__uuid': ['exact', 'contains'],
            'collection__name' : ['exact', 'contains'],
            'datatype__name' : ['exact'],
            'timestamp' : ['exact', 'year', 'range'],
        }


class FlatJsonSerializer(Serializer):
    def get_dump_object(self, obj):
        data = self._current
        if not self.selected_fields or 'id' in self.selected_fields:
            data['id'] = obj.id
        return data

    def end_object(self, obj):
        if not self.first:
            self.stream.write(', ')
        json.dump(self.get_dump_object(obj), self.stream,
                  cls=DjangoJSONEncoder)
        self._current = None

    def start_serialization(self):
        self.stream.write("[")

    def end_serialization(self):
        self.stream.write("]")

    def getvalue(self):
        return super(Serializer, self).getvalue()


def json_response(queryset):
    s = FlatJsonSerializer()
    return HttpResponse(s.serialize(queryset),
                        content_type="application/json")


def bird_list(request, living=None):
    if living:
        qs = Animal.living.annotate(acq_date=Min("event__date")).order_by("acq_date")
    else:
        qs = Animal.objects.all()
    qs = BirdFilter(request.GET, queryset=qs)
    if 'application/json' in request.META.get('HTTP_ACCEPT'):
        return json_response(qs)
    else:
        return render(request, 'birds/birds.html', {'bird_list': qs})


def event_list(request):
    event_list = EventFilter(request.GET, Event.objects.all())
    if 'application/json' in request.META.get('HTTP_ACCEPT'):
        return json_response(event_list)
    else:
        paginator = Paginator(event_list, 25)
        page = request.GET.get('page')
        try:
            qs = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            qs = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            qs = paginator.page(paginator.num_pages)
        return render(request, 'birds/events.html', {'event_list': qs})


class BirdView(generic.DetailView):
    model = Animal
    template_name = 'birds/bird.html'
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_context_data(self, **kwargs):
        context = super(BirdView, self).get_context_data(**kwargs)
        animal = context['animal']
        context['bird_list'] = animal.animal_set.all()
        print(context['bird_list'])
        context['event_list'] = animal.event_set.all()
        return context


class EventListView(generic.ListView):
    template_name = 'birds/events.html'
    context_object_name = 'event_list'
    queryset = Event.objects.order_by('-date')[:100]


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

# Create your views here.
