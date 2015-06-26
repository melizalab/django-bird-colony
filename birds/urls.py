from django.contrib.auth.decorators import login_required
from django.conf.urls import include, url

from birds import views

urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^birds/$', views.bird_list, name='birds'),
    url(r'^birds/living/$', views.bird_living_list, name='birds_living'),
    url(r'^birds/(?P<pk>\d+)/$', views.BirdView.as_view(), name='bird'),
    url(r'^events/$', views.EventListView.as_view(), name='events'),
    url(r'^events/summary/([0-9]{4})/([0-9]{1,2})/$', views.EventSummary.as_view(), name="event_summary"),
    # forms
    url(r'^clutch$', login_required(views.ClutchEntry.as_view()), name='clutch'),
    url(r'^birds/new$', login_required(views.BandingEntry.as_view()), name='new_bird'),
]
