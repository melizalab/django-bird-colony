from django.contrib.auth.decorators import login_required
from django.conf.urls import patterns, url

from birds import views

urlpatterns = patterns('',
                       url(r'^$', views.IndexView.as_view(), name='index'),
                       url(r'^summary/(\d+)/(\d+)/$', views.EventSummary.as_view(),
                           name="summary"),
                       url(r'^clutch$', login_required(views.ClutchEntry.as_view()),
                           name='clutch'),
                       url(r'^band$', login_required(views.BandingEntry.as_view()),
                           name='band'),
                       url(r'^birds/$', views.BirdListView.as_view(), name='birds'),
                       url(r'^birds/(?P<pk>\d+)/$', views.BirdView.as_view(), name='bird'),
                       url(r'^events/$', views.EventListView.as_view(), name='events'),
                       # list events by bird
)
