# -*- coding: utf-8 -*-
# -*- mode: python -*-
from django.contrib.auth.decorators import login_required
from django.conf.urls import url

from birds import views

urlpatterns = [
    # browser ui
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^animals/$', views.AnimalList.as_view(), name='animals'),
    # url(r'^animals/living/$', views.animal_list, {'living': True}, name='animals_living'),
    url(r'^animals/(?P<uuid>[a-f0-9\-]{36})/$', views.AnimalView.as_view(), name='animal'),
    url(r'^events/$', views.EventList.as_view(), name='events'),
    # summary views
    url(r'^summary/events/([0-9]{4})/([0-9]{1,2})/$', views.EventSummary.as_view(),
        name="event_summary"),
    # forms
    url(r'^clutch$', login_required(views.ClutchEntry.as_view()), name='clutch'),
    url(r'^animals/new$', login_required(views.BandingEntry.as_view()), name='new_animal'),
    # api
    # url(r'^api/animals/$', views.all_animals_json),
    # url(r'^api/events/$', views.all_events_json),
]
