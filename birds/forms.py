# -*- coding: utf-8 -*-
# -*- mode: python -*-
from django import forms
from django.template.defaultfilters import pluralize
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from birds import models
from birds.models import (
    Animal,
    Color,
    Event,
    Location,
    Pairing,
    Parent,
    Plumage,
    Sample,
    Species,
    Status,
)


def get_status_or_error(name: str):
    try:
        return Status.objects.get(name=name)
    except ObjectDoesNotExist as err:
        raise forms.ValidationError(
            _("No %(name)s status type - add one in admin"),
            params={"name": name},
        ) from err


class EventForm(forms.Form):
    date = forms.DateField()
    status = forms.ModelChoiceField(queryset=Status.objects.all())
    location = forms.ModelChoiceField(queryset=Location.objects.all(), required=False)
    description = forms.CharField(widget=forms.Textarea, required=False)
    entered_by = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))


class SampleForm(forms.ModelForm):
    class Meta:
        model = Sample
        fields = ["type", "source", "location", "comments", "date", "collected_by"]


class NewPairingForm(forms.Form):
    qs = Animal.objects.with_dates().alive()
    sire = forms.ModelChoiceField(queryset=qs.filter(sex=Animal.Sex.MALE))
    dam = forms.ModelChoiceField(queryset=qs.filter(sex=Animal.Sex.FEMALE))
    began = forms.DateField()
    purpose = forms.CharField(widget=forms.Textarea, required=False)
    entered_by = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))
    location = forms.ModelChoiceField(
        queryset=Location.objects.filter(nest=True), required=False
    )

    def clean(self):
        data = super().clean()
        sire = data.get("sire")
        if sire is None:
            raise forms.ValidationError(_("Must provide a sire"))
        if sire.sex != Animal.Sex.MALE:
            raise forms.ValidationError(_("Sire is not male"))
        if sire.age_group() != models.ADULT_ANIMAL_NAME:
            raise forms.ValidationError(_("Sire is not an adult"))
        if not sire.alive:
            raise forms.ValidationError(_("Sire is not alive"))
        if sire.pairings().filter(ended__isnull=True).count():
            raise forms.ValidationError(_("Sire is already in an active pairing"))
        sire_overlaps = sire.pairings().filter(
            began__lte=data["began"], ended__gte=data["began"]
        )
        if sire_overlaps.count() > 0:
            raise forms.ValidationError(
                _(
                    "Start date %(began)s overlaps with an existing pairing for sire: %(prev)s"
                ),
                code="invalid",
                params=data | {"prev": sire_overlaps.first()},
            )
        dam = data.get("dam")
        if dam is None:
            raise forms.ValidationError(_("Must provide a dam"))
        if dam.sex != Animal.Sex.FEMALE:
            raise forms.ValidationError(_("Dam is not female"))
        if dam.age_group() != models.ADULT_ANIMAL_NAME:
            raise forms.ValidationError(_("Dam is not an adult"))
        if not dam.alive:
            raise forms.ValidationError(_("Dam is not alive"))
        if dam.pairings().filter(ended__isnull=True).count():
            raise forms.ValidationError(_("Dam is in an active pairing"))
        dam_overlaps = dam.pairings().filter(
            began__lte=data["began"], ended__gte=data["began"]
        )
        if dam_overlaps.count() > 0:
            raise forms.ValidationError(
                _(
                    "Start date %(began)s overlaps with an existing pairing for dam: %(prev)s"
                ),
                code="invalid",
                params=data | {"prev": dam_overlaps.first()},
            )
        return data


class EndPairingForm(forms.Form):
    ended = forms.DateField(required=True)
    location = forms.ModelChoiceField(queryset=Location.objects.all(), required=False)
    entered_by = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))
    comment = forms.CharField(widget=forms.Textarea, required=False)


class NestCheckForm(forms.Form):
    location = forms.ModelChoiceField(
        queryset=Location.objects.filter(nest=True), widget=forms.HiddenInput()
    )
    eggs = forms.IntegerField(label="eggs", min_value=0)
    chicks = forms.IntegerField(label="chicks", min_value=0)

    def clean(self):
        data = super().clean()
        _location_name = self.initial["location"].name
        delta_chicks = data["chicks"] - self.initial["chicks"]
        _delta_eggs = data["eggs"] - self.initial["eggs"] + delta_chicks
        data["hatch_status"] = get_status_or_error(models.BIRTH_EVENT_NAME)
        data["laid_status"] = get_status_or_error(models.UNBORN_CREATION_EVENT_NAME)
        data["lost_status"] = get_status_or_error(models.LOST_EVENT_NAME)
        if delta_chicks < 0:
            raise forms.ValidationError(_("Missing chicks need to be removed manually"))
        elif delta_chicks > self.initial["eggs"]:
            raise forms.ValidationError(
                _("Not enough eggs to make %(chicks)d new chick%(plural)s"),
                params={"chicks": delta_chicks, "plural": pluralize(delta_chicks)},
            )

        return data


class NestCheckUser(forms.Form):
    confirmed = forms.BooleanField()
    entered_by = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))
    comments = forms.CharField(widget=forms.Textarea, required=False)


class NewBandForm(forms.Form):
    """Form to assign a band to an existing bird, optionally updating sex and plumage"""

    banding_date = forms.DateField()
    band_color = forms.ModelChoiceField(queryset=Color.objects.all(), required=False)
    band_number = forms.IntegerField(min_value=1)
    sex = forms.ChoiceField(choices=Animal.Sex.choices, required=True)
    plumage = forms.ModelChoiceField(queryset=Plumage.objects.all(), required=False)
    location = forms.ModelChoiceField(queryset=Location.objects.all(), required=False)
    user = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))

    def clean(self):
        data = super().clean()
        data["band_status"] = get_status_or_error(models.BANDED_EVENT_NAME)
        if Animal.objects.filter(
            band_color=data.get("band_color"), band_number=data["band_number"]
        ).exists():
            raise forms.ValidationError(
                _(
                    "A bird already exists with band color %(band_color)s and number %(band_number)d."
                ),
                code="invalid",
                params=data,
            )
        return data


class ReservationForm(forms.Form):
    """Form to create or clear a reservation"""

    date = forms.DateField()
    description = forms.CharField(widget=forms.Textarea, required=False)
    entered_by = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True), required=False
    )

    def clean(self):
        data = super().clean()
        data["status"] = get_status_or_error(models.RESERVATION_EVENT_NAME)
        return data


class SexForm(forms.Form):
    """Form to update an existing bird's sex"""

    date = forms.DateField()
    sex = forms.ChoiceField(choices=Animal.Sex.choices, required=True)
    description = forms.CharField(widget=forms.Textarea, required=False)
    entered_by = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))

    def clean(self):
        data = super().clean()
        data["status"] = get_status_or_error(models.NOTE_EVENT_NAME)
        return data


class NewAnimalForm(forms.Form):
    acq_status = forms.ModelChoiceField(queryset=Status.objects.filter(adds=True))
    acq_date = forms.DateField()
    sex = forms.ChoiceField(
        choices=Animal.Sex.choices, initial=Animal.Sex.UNKNOWN_SEX, required=True
    )
    plumage = forms.ModelChoiceField(queryset=Plumage.objects.all(), required=False)
    qs = Animal.objects.alive()
    sire = forms.ModelChoiceField(queryset=qs.filter(sex__exact="M"), required=False)
    dam = forms.ModelChoiceField(queryset=qs.filter(sex__exact="F"), required=False)
    species = forms.ModelChoiceField(queryset=Species.objects.all(), required=False)
    banding_date = forms.DateField()
    band_color = forms.ModelChoiceField(queryset=Color.objects.all(), required=False)
    band_number = forms.IntegerField(min_value=1)
    location = forms.ModelChoiceField(queryset=Location.objects.all())
    comments = forms.CharField(widget=forms.Textarea, required=False)
    user = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))

    def clean(self):
        data = super().clean()
        _status = get_status_or_error(models.BANDED_EVENT_NAME)
        if "acq_status" in data and data["acq_status"].name == models.BIRTH_EVENT_NAME:
            dam = data.get("dam")
            sire = data.get("sire")
            if dam is None or sire is None:
                raise forms.ValidationError(_("Parents required for hatched birds"))
            if dam.species != sire.species:
                raise forms.ValidationError(_("Parents must be the same species"))
            data["species"] = dam.species
        else:
            if data.get("species") is None:
                raise forms.ValidationError(
                    _("Species required for non-hatch acquisition")
                )
            data["dam"] = None
            data["sire"] = None
        if Animal.objects.filter(
            band_color=data.get("band_color"), band_number=data["band_number"]
        ).exists():
            raise forms.ValidationError(
                _(
                    "A bird already exists with band color %(band_color)s and number %(band_number)d."
                ),
                code="invalid",
                params=data,
            )
        return data
