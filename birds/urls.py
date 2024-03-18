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
        login_required(views.NewAnimalEntry.as_view()),
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
        r"^animals/(?P<animal>[a-f0-9\-]{36})/events/$",
        views.event_list,
        name="animal_events",
    ),
    re_path(
        r"^animals/(?P<uuid>[a-f0-9\-]{36})/events/new/$",
        login_required(views.new_event_entry),
        name="new_event",
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
        r"^animals/(?P<uuid>[a-f0-9\-]{36})/set-sex/$",
        login_required(views.update_sex),
        name="set_sex",
    ),
    re_path(
        r"^animals/(?P<uuid>[a-f0-9\-]{36})/reserve/$",
        login_required(views.ReservationEntry.as_view()),
        name="update_reservation",
    ),
    re_path(r"^events/$", views.event_list, name="events"),
    re_path(r"^pairings/$", views.pairing_list, name="pairings"),
    re_path(r"^pairings/active/$", views.active_pairing_list, name="pairings_active"),
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
    re_path(r"^summary/nests/$", views.nest_report, name="nest-summary"),
    path(
        "summary/events/<int:year>/<int:month>/",
        views.event_summary,
        name="event_summary",
    ),
    # forms
    re_path(r"^nest-check/$", login_required(views.nest_check), name="nest-check"),
    re_path(r"^new-band/$", login_required(views.new_band_entry), name="new_band"),
    re_path(r"^set-sex/$", login_required(views.update_sex), name="set_sex"),
    re_path(
        r"^reserve/$",
        login_required(views.ReservationEntry.as_view()),
        name="update_reservation",
    ),
    # api
    re_path(r"^api/info/$", views.api_info, name="api_info"),
    re_path(r"^api/animals/$", views.APIAnimalsList.as_view(), name="animals_api"),
    re_path(r"^api/animals/(?P<pk>[a-f0-9\-]{36})/$", views.APIAnimalDetail.as_view()),
    re_path(
        r"^api/animals/(?P<pk>[a-f0-9\-]{36})/children/$",
        views.APIAnimalChildList.as_view(),
    ),
    re_path(r"^api/events/$", views.APIEventsList.as_view(), name="events_api"),
    re_path(r"^api/pedigree/$", views.APIAnimalPedigree.as_view(), name="pedigree_api"),
]
