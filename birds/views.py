from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.views import generic

from birds.models import Animal, Event, Age
from birds.forms import ClutchForm

class BirdListView(generic.ListView):
    template_name = 'birds/birds.html'
    context_object_name = 'bird_list'
    queryset = Animal.living.order_by("id")


class BirdView(generic.DetailView):
    model = Animal
    template_name = 'birds/bird.html'

    def get_context_data(self, **kwargs):
        context = super(BirdView, self).get_context_data(**kwargs)
        context['bird_list'] = context['animal'].animal_set.all()
        context['event_list'] = context['animal'].event_set.all()
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
  GROUP BY D.name
  ORDER BY D.species_id, D.min_days
"""

class IndexView(generic.base.TemplateView):

    template_name = "birds/index.html"

    def get_context_data(self, **kwargs):
        return {"groups": Age.objects.raw(_age_query)}


# Create your views here.
