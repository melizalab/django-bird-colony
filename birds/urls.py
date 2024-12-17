# -*- coding: utf-8 -*-
# -*- mode: python -*-
from django.contrib.auth.decorators import login_required
from django.urls import path

from birds import views

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
    path("users/", views.user_list, name="users"),
    path("users/<int:pk>/", views.user_view, name="user"),
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
    # forms
    path(
        "breeding-check/", login_required(views.breeding_check), name="breeding-check"
    ),
    # api
    path("api/info/", views.api_info, name="api_info"),
    path("api/animals/", views.APIAnimalsList.as_view(), name="animals_api"),
    path(
        "api/animals/<uuid:pk>/",
        views.api_animal_detail,
        name="animal_api",
    ),
    path(
        "api/animals/<uuid:pk>/children/",
        views.APIAnimalChildList.as_view(),
        name="children_api",
    ),
    path("api/events/", views.api_event_list, name="events_api"),
    path("api/animals/<uuid:animal>/events/", views.api_event_list, name="events_api"),
    path(
        "api/measurements/",
        views.APIMeasurementsList.as_view(),
        name="measurements_api",
    ),
    path("api/pedigree/", views.APIAnimalPedigree.as_view(), name="pedigree_api"),
]
