from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.views import generic
from django.db.models import Min, Count

import datetime

from birds.models import Animal, Event, Age, Status
from birds.forms import ClutchForm, BandingForm

class BirdListView(generic.ListView):
    template_name = 'birds/birds.html'
    context_object_name = 'bird_list'
    queryset = Animal.living.annotate(acq_date=Min("event__date")).order_by("acq_date")


class BirdView(generic.DetailView):
    model = Animal
    template_name = 'birds/bird.html'

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


# after excluding birds that have died/left, calculate days since
# hatch/acquisition and bin according to age table
_age_query = """
SELECT D.*, COUNT(*) as count FROM birds_animal AS A
  INNER JOIN (birds_event AS E, birds_status AS S, birds_age AS D)
    ON (E.animal_id=A.id AND
        E.status_id=S.id AND
        A.species_id=D.species_id AND
        timestampdiff(DAY,E.date,CURDATE()) BETWEEN D.min_days AND D.max_days)
  WHERE NOT (A.id IN (SELECT U1.animal_id FROM birds_event U1
                       INNER JOIN birds_status U2 ON ( U1.status_id = U2.id )
                       WHERE U2.count=-1 ))
    AND S.count=1
  GROUP BY D.name, D.species_id
  ORDER BY D.species_id, D.min_days
"""

class IndexView(generic.base.TemplateView):

    template_name = "birds/index.html"

    def get_context_data(self, **kwargs):
        today = datetime.date.today()
        return {"groups": Age.objects.raw(_age_query),
                "today": today,
                "lastmonth": today.replace(day=1) - datetime.timedelta(days=1)
        }


class EventSummary(generic.base.TemplateView):

    template_name = "birds/summary.html"

    def get_context_data(self, **kwargs):
        year, month = map(int, self.args[:2])
        qs = Event.objects.filter(date__year=year, date__month=month)
        totls = [ dict(name=x['status__name'], total=x['total']) for x in
                  qs.values("status__name").annotate(total=Count("id")) ]
        return { "year": year,
                 "month": month,
                 "next": datetime.date(year, month, 1) + datetime.timedelta(days=32),
                 "prev": datetime.date(year, month, 1) - datetime.timedelta(days=1),
                 "event_totals": totls }

# Create your views here.
