# -*- coding: utf-8 -*-
# -*- mode: python -*-
from django.contrib.auth.decorators import login_required
from django.conf.urls import re_path

from birds import views

app_name = "birds"
urlpatterns = [
    # browser ui
    re_path(r'^$', views.IndexView.as_view(), name='index'),
    re_path(r'^animals/$', views.AnimalList.as_view(), name='animals'),
    re_path(r'^animals/new/$', login_required(views.NewAnimalEntry.as_view()), name='new_animal'),
    re_path(r'^animals/(?P<uuid>[a-f0-9\-]{36})/$', views.AnimalView.as_view(), name='animal'),
    re_path(r'^animals/(?P<animal>[a-f0-9\-]{36})/events/$', views.EventList.as_view(), name='animal_events'),
    re_path(r'^animals/(?P<uuid>[a-f0-9\-]{36})/events/new/$', login_required(views.EventEntry.as_view()), name='new_event'),
    re_path(r'^animals/(?P<animal>[a-f0-9\-]{36})/samples/$', views.SampleList.as_view(), name='animal_samples'),
    re_path(r'^animals/(?P<uuid>[a-f0-9\-]{36})/samples/new/$', login_required(views.SampleEntry.as_view()), name='new_sample'),
    re_path(r'^animals/(?P<uuid>[a-f0-9\-]{36})/new-band/$', login_required(views.NewBandEntry.as_view()), name='new_band'),
    re_path(r'^animals/(?P<uuid>[a-f0-9\-]{36})/new-clutch/$', login_required(views.ClutchEntry.as_view()), name='clutch'),
    re_path(r'^events/$', views.EventList.as_view(), name='events'),
    re_path(r'^sampletypes/$', views.SampleTypeList.as_view(), name='sampletypes'),
    re_path(r'^samples/$', views.SampleList.as_view(), name='samples'),
    re_path(r'^samples/(?P<uuid>[a-f0-9\-]{36})/$', views.SampleView.as_view(), name='sample'),
    # summary views
    re_path(r'^summary/locations/$', views.LocationSummary.as_view(), name="location-summary"),
    re_path(r'^summary/nests/$', views.NestReport.as_view(), name='nest-summary'),
    re_path(r'^summary/events/([0-9]{4})/([0-9]{1,2})/$', views.EventSummary.as_view(),
        name="event_summary"),
    # forms
    #re_path(r'^nest-check/$', login_required(views.NestCheck.as_view()), name='nest-check'),
    re_path(r'^nest-check/$', login_required(views.nest_check), name='nest-check'),
    re_path(r'^new-clutch/$', login_required(views.ClutchEntry.as_view()), name='clutch'),
    re_path(r'^new-band/$', login_required(views.NewBandEntry.as_view()), name='new_band'),
    # api
    re_path(r'^api/info/$', views.api_info, name='api_info'),
    re_path(r'^api/animals/$', views.APIAnimalsList.as_view(), name="animals_api"),
    re_path(r'^api/animals/(?P<pk>[a-f0-9\-]{36})/$', views.APIAnimalDetail.as_view()),
    re_path(r'^api/animals/(?P<pk>[a-f0-9\-]{36})/children/$', views.APIAnimalChildList.as_view()),
    re_path(r'^api/events/$', views.APIEventsList.as_view(), name="events_api"),
    re_path(r'^api/pedigree/$', views.APIAnimalPedigree.as_view(), name="pedigree_api"),
]
