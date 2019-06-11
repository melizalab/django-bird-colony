# -*- coding: utf-8 -*-
# -*- mode: python -*-
from django.contrib.auth.decorators import login_required
from django.conf.urls import url

from birds import views

app_name = "birds"
urlpatterns = [
    # browser ui
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^animals/$', views.AnimalList.as_view(), name='animals'),
    url(r'^animals/new/$', login_required(views.NewAnimalEntry.as_view()), name='new_animal'),
    url(r'^animals/(?P<uuid>[a-f0-9\-]{36})/$', views.AnimalView.as_view(), name='animal'),
    url(r'^animals/(?P<animal>[a-f0-9\-]{36})/events/$', views.EventList.as_view(), name='animal_events'),
    url(r'^animals/(?P<uuid>[a-f0-9\-]{36})/events/new/$', login_required(views.EventEntry.as_view()), name='new_event'),
    url(r'^animals/(?P<animal>[a-f0-9\-]{36})/samples/$', views.SampleList.as_view(), name='animal_samples'),
    url(r'^animals/(?P<uuid>[a-f0-9\-]{36})/samples/new/$', login_required(views.SampleEntry.as_view()), name='new_sample'),
    url(r'^animals/(?P<uuid>[a-f0-9\-]{36})/new-band/$', login_required(views.NewBandEntry.as_view()), name='new_band'),
    url(r'^events/$', views.EventList.as_view(), name='events'),
    url(r'^sampletypes/$', views.SampleTypeList.as_view(), name='sampletypes'),
    url(r'^samples/$', views.SampleList.as_view(), name='samples'),
    url(r'^samples/(?P<uuid>[a-f0-9\-]{36})/$', views.SampleView.as_view(), name='sample'),
    # summary views
    url(r'^summary/events/([0-9]{4})/([0-9]{1,2})/$', views.EventSummary.as_view(),
        name="event_summary"),
    # forms
    url(r'^new-clutch/$', login_required(views.ClutchEntry.as_view()), name='clutch'),
    url(r'^new-band/$', login_required(views.NewBandEntry.as_view()), name='new_band'),
    # api
    url(r'^api/animals/$', views.APIAnimalsList.as_view(), name="animals_api"),
    url(r'^api/animals/(?P<pk>[a-f0-9\-]{36})/$', views.APIAnimalDetail.as_view()),
    url(r'^api/events/$', views.APIEventsList.as_view(), name="events_api"),
    url(r'^api/pedigree/$', views.APIAnimalPedigree.as_view(), name="pedigree_api"),
]
