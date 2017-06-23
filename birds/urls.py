# -*- coding: utf-8 -*-
# -*- mode: python -*-
from django.contrib.auth.decorators import login_required
from django.conf.urls import url

from birds import views

urlpatterns = [
    # browser ui
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^animals/$', views.AnimalList.as_view(), name='animals'),
    url(r'^animals/new/$', login_required(views.BandingEntry.as_view()), name='new_animal'),
    url(r'^animals/(?P<uuid>[a-f0-9\-]{36})/$', views.AnimalView.as_view(), name='animal'),
    url(r'^animals/(?P<animal>[a-f0-9\-]{36})/events/$',
        views.EventList.as_view(), name='animal_events'),
    url(r'^animals/(?P<uuid>[a-f0-9\-]{36})/events/new/$',
        login_required(views.EventEntry.as_view()), name='new_event'),
    url(r'^events/$', views.EventList.as_view(), name='events'),
    url(r'^events/new/$', login_required(views.EventEntry.as_view()), name='new_event'),
    # summary views
    url(r'^summary/events/([0-9]{4})/([0-9]{1,2})/$', views.EventSummary.as_view(),
        name="event_summary"),
    # forms
    url(r'^clutch$', login_required(views.ClutchEntry.as_view()), name='clutch'),
    # api
    url(r'^api/animals/$', views.APIAnimalsList.as_view(), name="animals_api"),
    url(r'^api/animals/(?P<pk>[a-f0-9\-]{36})/$', views.APIAnimalDetail.as_view()),
    #url(r'^api/animals/(?P<uuid>[a-f0-9\-]{36})/events$', views.APIEventsList.as_view()),
    url(r'^api/events/$', views.APIEventsList.as_view(), name="events_api"),
]
