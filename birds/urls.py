# -*- coding: utf-8 -*-
# -*- mode: python -*-
from django.contrib.auth.decorators import login_required
from django.conf.urls import url

from birds import views

urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^api/birds/$', views.all_birds_json),
    url(r'^api/events/$', views.all_events_json),
    url(r'^birds/$', views.bird_list, {'living': None}, name='birds'),
    url(r'^birds/living/$', views.bird_list, {'living': True}, name='birds_living'),
    url(r'^birds/(?P<uuid>[a-f0-9\-]{36})/$', views.BirdView.as_view(), name='bird'),
    url(r'^events/$', views.event_list, name='events'),
    url(r'^events/summary/([0-9]{4})/([0-9]{1,2})/$', views.EventSummary.as_view(), name="event_summary"),
    # forms
    url(r'^clutch$', login_required(views.ClutchEntry.as_view()), name='clutch'),
    url(r'^birds/new$', login_required(views.BandingEntry.as_view()), name='new_bird'),
]
