from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.views import generic

from birds.models import Animal, Event
from birds.forms import ClutchForm

def index(request):
    return render(request, 'birds/index.html')

class BirdListView(generic.ListView):
    template_name = 'birds/birds.html'
    context_object_name = 'bird_list'

    def get_queryset(self):
        return Animal.objects.order_by("id")


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

    def get_queryset(self):
        """ Returns last 100 events """
        return Event.objects.order_by('-date')[:100]


class ClutchEntry(generic.FormView):
    template_name = "birds/clutch_entry.html"
    form_class = ClutchForm

    def form_valid(self, form, **kwargs):
        """ For valid entries, render a page with a list of the created events """
        objs = form.create_clutch()
        return render(self.request, 'birds/events.html',
                      { 'event_list': objs['events'],
                        'header_text': 'Hatch events for new clutch'})


# Create your views here.
