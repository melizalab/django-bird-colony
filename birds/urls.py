# -*- mode: python -*-
from django.contrib.auth.decorators import login_required
from django.urls import path

from birds import api_views, views

app_name = "birds"
urlpatterns = [
    # browser ui
    path("", views.index, name="index"),
    path("animals/", views.animal_list, name="animals"),
    path(
        "animals/new/",
        login_required(views.new_animal_entry),
        name="new_animal",
    ),
    path(
        "animals/<uuid>/",
        views.animal_view,
        name="animal",
    ),
    path(
        "animals/<uuid>/genealogy/",
        views.animal_genealogy,
        name="genealogy",
    ),
    path(
        "animals/<uuid:parent>/children/",
        views.animal_list,
        name="animal_kids",
    ),
    path(
        "animals/<uuid>/set-sex/",
        login_required(views.update_sex),
        name="set_sex",
    ),
    path(
        "animals/<uuid>/reserve/",
        login_required(views.reservation_entry),
        name="update_reservation",
    ),
    path(
        "animals/<uuid>/new-band/",
        login_required(views.new_band_entry),
        name="new_band",
    ),
    path(
        "animals/<uuid:animal>/events/",
        views.event_list,
        name="events",
    ),
    path(
        "animals/<uuid:animal>/events/new/",
        login_required(views.event_entry),
        name="event_entry",
    ),
    path(
        "events/<int:event>/change/",
        views.event_entry,
        name="event_entry",
    ),
    path(
        "animals/<uuid:animal>/measurements/",
        views.measurement_list,
        name="measurements",
    ),
    path("events/", views.event_list, name="events"),
    path("measurements/", views.measurement_list, name="measurements"),
    path("locations/", views.location_list, name="locations"),
    path("locations/<int:pk>/", views.location_view, name="location"),
    path("locations/<int:location>/events/", views.event_list, name="events"),
    path(
        "animals/<uuid:animal>/samples/",
        views.sample_list,
        name="samples",
    ),
    path(
        "animals/<uuid>/samples/new/",
        login_required(views.new_sample_entry),
        name="new_sample",
    ),
    path("tags/", views.tag_list, name="tags"),
    path("tags/<int:pk>/", views.tag_view, name="tag"),
    path("pairings/", views.pairing_list, name="pairings"),
    path("pairings/active/", views.active_pairing_list, name="pairings_active"),
    path("pairings/<int:pk>/", views.pairing_view, name="pairing"),
    path(
        "pairings/<int:pk>/new/",
        login_required(views.new_pairing_entry),
        name="new_pairing",
    ),
    path(
        "pairings/<int:pk>/new-egg/",
        login_required(views.new_pairing_egg),
        name="new_pairing_egg",
    ),
    path(
        "pairings/<int:pk>/new-event/",
        login_required(views.new_pairing_event),
        name="new_pairing_event",
    ),
    path(
        "pairings/<int:pk>/end/",
        login_required(views.close_pairing),
        name="end_pairing",
    ),
    path("pairings/new/", login_required(views.new_pairing_entry), name="new_pairing"),
    path("sampletypes/", views.sample_type_list, name="sampletypes"),
    path("samples/", views.sample_list, name="samples"),
    path(
        "samples/<uuid>/",
        views.sample_view,
        name="sample",
    ),
    # summary views
    path(
        "summary/locations/",
        views.location_summary,
        name="location-summary",
    ),
    path("summary/breeding/", views.breeding_report, name="breeding-summary"),
    path(
        "summary/events/<int:year>/<int:month>/",
        views.event_summary,
        name="event_summary",
    ),
    # path("summary/breeding-stats/", views.breeding_stats_list, name="breeding-stats"),
    # forms
    path(
        "breeding-check/", login_required(views.breeding_check), name="breeding-check"
    ),
    # api
    path("api/info/", api_views.info, name="api_info"),
    path("api/animals/", api_views.AnimalsList.as_view(), name="animals_api"),
    path(
        "api/animals/<uuid:pk>/",
        api_views.animal_detail,
        name="animal_api",
    ),
    path(
        "api/animals/<uuid:pk>/children/",
        api_views.AnimalChildList.as_view(),
        name="children_api",
    ),
    path(
        "api/animals/<uuid:animal>/events/",
        api_views.EventList.as_view(),
        name="events_api",
    ),
    path("api/events/", api_views.EventList.as_view(), name="events_api"),
    path("api/events/<int:pk>/", api_views.event_detail, name="event_api"),
    path("api/measurements/", api_views.measurement_list, name="measurements_api"),
    path("api/pedigree/", api_views.animal_pedigree, name="pedigree_api"),
]
