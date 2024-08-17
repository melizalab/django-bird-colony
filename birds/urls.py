# -*- coding: utf-8 -*-
# -*- mode: python -*-
from django.contrib.auth.decorators import login_required
from django.urls import path, re_path

from birds import views

app_name = "birds"
urlpatterns = [
    # browser ui
    re_path(r"^$", views.index, name="index"),
    re_path(r"^animals/$", views.animal_list, name="animals"),
    re_path(
        r"^animals/new/$",
        login_required(views.new_animal_entry),
        name="new_animal",
    ),
    re_path(
        r"^animals/(?P<uuid>[a-f0-9\-]{36})/$",
        views.animal_view,
        name="animal",
    ),
    re_path(
        r"^animals/(?P<uuid>[a-f0-9\-]{36})/genealogy/$",
        views.animal_genealogy,
        name="genealogy",
    ),
    re_path(
        r"^animals/(?P<uuid>[a-f0-9\-]{36})/events/new/$",
        login_required(views.new_event_entry),
        name="new_event",
    ),
    re_path(
        r"^animals/(?P<uuid>[a-f0-9\-]{36})/set-sex/$",
        login_required(views.update_sex),
        name="set_sex",
    ),
    re_path(
        r"^animals/(?P<uuid>[a-f0-9\-]{36})/reserve/$",
        login_required(views.reservation_entry),
        name="update_reservation",
    ),
    re_path(
        r"^animals/(?P<animal>[a-f0-9\-]{36})/samples/$",
        views.sample_list,
        name="animal_samples",
    ),
    re_path(
        r"^animals/(?P<uuid>[a-f0-9\-]{36})/samples/new/$",
        login_required(views.new_sample_entry),
        name="new_sample",
    ),
    re_path(
        r"^animals/(?P<uuid>[a-f0-9\-]{36})/new-band/$",
        login_required(views.new_band_entry),
        name="new_band",
    ),
    re_path(
        r"^animals/(?P<animal>[a-f0-9\-]{36})/events/$",
        views.event_list,
        name="animal_events",
    ),
    re_path(r"^events/$", views.event_list, name="events"),
    path("locations/", views.location_list, name="locations"),
    path("locations/<int:pk>/", views.location_view, name="location"),
    path("locations/<int:location>/events/", views.event_list, name="events"),
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
        "pairings/<int:pk>/end/",
        login_required(views.close_pairing),
        name="end_pairing",
    ),
    path("pairings/new/", login_required(views.new_pairing_entry), name="new_pairing"),
    re_path(r"^sampletypes/$", views.sample_type_list, name="sampletypes"),
    re_path(r"^samples/$", views.sample_list, name="samples"),
    re_path(
        r"^samples/(?P<uuid>[a-f0-9\-]{36})/$",
        views.sample_view,
        name="sample",
    ),
    # summary views
    re_path(
        r"^summary/locations/$",
        views.location_summary,
        name="location-summary",
    ),
    re_path(r"^summary/breeding/$", views.breeding_report, name="breeding-summary"),
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
    re_path(r"^api/info/$", views.api_info, name="api_info"),
    re_path(r"^api/animals/$", views.APIAnimalsList.as_view(), name="animals_api"),
    re_path(
        r"^api/animals/(?P<pk>[a-f0-9\-]{36})/$",
        views.api_animal_detail,
        name="animal_api",
    ),
    re_path(
        r"^api/animals/(?P<pk>[a-f0-9\-]{36})/children/$",
        views.APIAnimalChildList.as_view(),
        name="children_api",
    ),
    re_path(r"^api/events/$", views.APIEventsList.as_view(), name="events_api"),
    re_path(r"^api/pedigree/$", views.APIAnimalPedigree.as_view(), name="pedigree_api"),
]
