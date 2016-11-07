from django.shortcuts import render, render_to_response
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.core import serializers
from django.views import generic
from django.db.models import Min
import django_filters
import datetime

from birds.models import Animal, Event
from birds.forms import ClutchForm, BandingForm


class BirdFilter(django_filters.FilterSet):
    class Meta:
        model = Animal
        fields = ['sex', 'band_color', 'species__code']


def json_response(queryset):
    return HttpResponse(serializers.serialize("json", queryset),
                        content_type="application/json")


def bird_list(request):
    qs = BirdFilter(request.GET, queryset=Animal.objects.all())
    return render_to_response('birds/birds.html', {'bird_list': qs})


def bird_living_list(request):
    qs = Animal.living.annotate(acq_date=Min("event__date")).order_by("acq_date")
    qs = BirdFilter(request.GET, queryset=qs)
    return render_to_response('birds/birds.html', {'bird_list': qs})


class BirdView(generic.DetailView):
    model = Animal
    template_name = 'birds/bird.html'
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_context_data(self, **kwargs):
        context = super(BirdView, self).get_context_data(**kwargs)
        animal = context['animal']
        context['bird_list'] = animal.animal_set.all()
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
