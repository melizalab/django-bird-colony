# -*- coding: utf-8 -*-
# -*- mode: python -*-
from django import forms

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from birds import models
from birds.models import (
    Animal,
    Event,
    Status,
    Location,
    Color,
    Plumage,
    Species,
    Parent,
    Sample,
    Pairing,
)
from django.utils.translation import gettext_lazy as _


class EventForm(forms.ModelForm):
    date = forms.DateField()
    entered_by = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))

    class Meta:
        model = Event
        fields = ["date", "status", "location", "description", "entered_by"]


class SampleForm(forms.ModelForm):
    class Meta:
        model = Sample
        fields = ["type", "source", "location", "comments", "date", "collected_by"]


class NewPairingForm(forms.ModelForm):
    sire = forms.ModelChoiceField(queryset=Animal.living.filter(sex=Animal.MALE))
    dam = forms.ModelChoiceField(queryset=Animal.living.filter(sex=Animal.FEMALE))
    entered_by = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))
    location = forms.ModelChoiceField(
        queryset=Location.objects.filter(nest=True), required=False
    )

    def clean(self):
        data = super().clean()
        sire = data["sire"]
        if sire.sex != Animal.MALE:
            raise forms.ValidationError("Sire is not male")
        if sire.age_group() != models.ADULT_ANIMAL_NAME:
            raise forms.ValidationError("Sire is not an adult")
        if not sire.alive:
            raise forms.ValidationError("Sire is not alive")
        if sire.pairings().filter(ended__isnull=True).count():
            raise forms.ValidationError("Sire is already in an active pairing")
        sire_overlaps = sire.pairings().filter(
            began__lte=data["began"], ended__gte=data["began"]
        )
        if sire_overlaps.count() > 0:
            raise forms.ValidationError(
                _(
                    "Start date %(began)s overlaps with an existing pairing for sire: %(prev)s",
                    code="invalid",
                    params=data | {"prev": sire_overlaps.first()},
                )
            )
        dam = data["dam"]
        if dam.sex != Animal.FEMALE:
            raise forms.ValidationError("Dam is not female")
        if dam.age_group() != models.ADULT_ANIMAL_NAME:
            raise forms.ValidationError("Dam is not an adult")
        if not dam.alive:
            raise forms.ValidationError("Dam is not alive")
        if dam.pairings().filter(ended__isnull=True).count():
            raise forms.ValidationError("Dam is in an active pairing")
        dam_overlaps = dam.pairings().filter(
            began__lte=data["began"], ended__gte=data["began"]
        )
        if dam_overlaps.count() > 0:
            raise forms.ValidationError(
                _(
                    "Start date %(began)s overlaps with an existing pairing for dam: %(prev)s",
                    code="invalid",
                    params=data | {"prev": dam_overlaps.first()},
                )
            )
        return data

    class Meta:
        model = Pairing
        fields = ["sire", "dam", "began", "purpose"]


class EndPairingForm(forms.ModelForm):
    ended = forms.DateField(required=True)
    location = forms.ModelChoiceField(queryset=Location.objects.all(), required=False)
    entered_by = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))

    class Meta:
        model = Pairing
        fields = ["began", "ended", "comment"]


class NestCheckForm(forms.Form):
    location = forms.ModelChoiceField(
        queryset=Location.objects.filter(nest=True), widget=forms.HiddenInput()
    )
    eggs = forms.IntegerField(label="eggs", min_value=0)
    chicks = forms.IntegerField(label="chicks", min_value=0)

    def clean(self):
        from birds.models import (
            BIRTH_EVENT_NAME,
            UNBORN_CREATION_EVENT_NAME,
            LOST_EVENT_NAME,
        )
        from django.template.defaultfilters import pluralize

        cleaned_data = super().clean()
        location_name = self.initial["location"].name
        delta_chicks = cleaned_data["chicks"] - self.initial["chicks"]
        delta_eggs = cleaned_data["eggs"] - self.initial["eggs"] + delta_chicks
        try:
            cleaned_data["hatch_status"] = Status.objects.get(name=BIRTH_EVENT_NAME)
        except ObjectDoesNotExist:
            raise forms.ValidationError(
                "No %(name)s status type - add one in admin",
                params={"name": BIRTH_EVENT_NAME},
            )
        try:
            cleaned_data["laid_status"] = Status.objects.get(
                name=UNBORN_CREATION_EVENT_NAME
            )
        except ObjectDoesNotExist:
            raise forms.ValidationError(
                "No %(name)s status type - add one in admin",
                params={"name": UNBORN_CREATION_EVENT_NAME},
            )
        try:
            cleaned_data["lost_status"] = Status.objects.get(name=LOST_EVENT_NAME)
        except ObjectDoesNotExist:
            raise forms.ValidationError(
                "No %(name)s status type - add one in admin",
                params={"name": LOST_EVENT_NAME},
            )
        if delta_chicks < 0:
            raise forms.ValidationError("Missing chicks need to be removed manually")
        elif delta_chicks > self.initial["eggs"]:
            raise forms.ValidationError(
                "Not enough eggs to make %(chicks)d new chick%(plural)s",
                params={"chicks": delta_chicks, "plural": pluralize(delta_chicks)},
            )

        return cleaned_data


class NestCheckUser(forms.Form):
    confirmed = forms.BooleanField()
    entered_by = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))
    comments = forms.CharField(widget=forms.Textarea, required=False)


class NewBandForm(forms.Form):
    animal = forms.ModelChoiceField(
        queryset=Animal.living.filter(band_number__isnull=True)
    )
    banding_date = forms.DateField()
    band_color = forms.ModelChoiceField(queryset=Color.objects.all(), required=False)
    band_number = forms.IntegerField(min_value=1)
    sex = forms.ChoiceField(choices=Animal.SEX_CHOICES, required=True)
    plumage = forms.ModelChoiceField(queryset=Plumage.objects.all(), required=False)
    location = forms.ModelChoiceField(queryset=Location.objects.all(), required=False)
    user = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))

    def clean(self):
        data = super().clean()
        try:
            data["band_status"] = Status.objects.get(name__startswith="band")
        except ObjectDoesNotExist:
            raise forms.ValidationError("No 'banded' status type - add one in admin")
        if Animal.objects.filter(
            band_color=data["band_color"], band_number=data["band_number"]
        ).exists():
            raise forms.ValidationError(
                _(
                    "A bird already exists with band color %(band_color)s and number %(band_number)d."
                ),
                code="invalid",
                params=data,
            )
        return data

    def add_band(self):
        data = self.cleaned_data
        animal = data["animal"]
        animal.band_color = data["band_color"]
        animal.band_number = data["band_number"]
        animal.sex = data["sex"]
        animal.plumage = data["plumage"]
        animal.save()
        evt = Event(
            animal=animal,
            date=data["banding_date"],
            status=data["band_status"],
            location=data["location"],
            description=animal.band(),
            entered_by=data["user"],
        )
        evt.save()
        return animal



class ReservationForm(forms.Form):
    animal = forms.ModelChoiceField(queryset=Animal.objects.all())
    date = forms.DateField()
    description = forms.CharField(widget=forms.Textarea, required=False)
    entered_by = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True), required=False)

    def clean(self):
        super().clean()
        try:
            self.cleaned_data["status"] = Status.objects.get(name=models.RESERVATION_EVENT_NAME)
        except ObjectDoesNotExist:
            raise forms.ValidationError(f"No '{models.RESERVATION_EVENT_NAME}' status type - add one in admin")
        return self.cleaned_data


class SexForm(forms.Form):
    animal = forms.ModelChoiceField(
        queryset=Animal.objects.filter(sex=Animal.UNKNOWN_SEX)
    )
    date = forms.DateField()
    sex = forms.ChoiceField(choices=Animal.SEX_CHOICES, required=True)
    description = forms.CharField(widget=forms.Textarea, required=False)
    entered_by = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))

    def clean(self):
        data = super().clean()
        try:
            data["status"] = Status.objects.get(name=models.NOTE_EVENT_NAME)
        except ObjectDoesNotExist:
            raise forms.ValidationError(f"No '{models.NOTE_EVENT_NAME}' status type - add one in admin")
        return data

    def update_sex(self):
        data = self.cleaned_data
        animal = data["animal"]
        animal.sex = data["sex"]
        descr = data["description"] or f"sexed as {animal.sex}"
        evt = Event(
            animal=animal,
            date=data["date"],
            status=data["status"],
            entered_by=data["entered_by"],
            description=descr,
        )
        animal.save()
        evt.save()
        return animal


class NewAnimalForm(forms.Form):
    acq_status = forms.ModelChoiceField(queryset=Status.objects.filter(adds=True))
    acq_date = forms.DateField()
    sex = forms.ChoiceField(
        choices=Animal.SEX_CHOICES, initial=Animal.UNKNOWN_SEX, required=True
    )
    plumage = forms.ModelChoiceField(queryset=Plumage.objects.all(), required=False)
    sire = forms.ModelChoiceField(
        queryset=Animal.living.filter(sex__exact="M"), required=False
    )
    dam = forms.ModelChoiceField(
        queryset=Animal.living.filter(sex__exact="F"), required=False
    )
    species = forms.ModelChoiceField(queryset=Species.objects.all(), required=False)
    banding_date = forms.DateField()
    band_color = forms.ModelChoiceField(queryset=Color.objects.all(), required=False)
    band_number = forms.IntegerField(min_value=1)
    location = forms.ModelChoiceField(queryset=Location.objects.all())
    comments = forms.CharField(widget=forms.Textarea, required=False)
    user = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))

    def clean(self):
        super(NewAnimalForm, self).clean()
        data = self.cleaned_data
        try:
            data["band_status"] = Status.objects.get(name__startswith="band")
        except ObjectDoesNotExist:
            raise forms.ValidationError("No 'banded' status type - add one in admin")
        if "acq_status" in data and data["acq_status"].name == "hatched":
            if data["dam"] is None or data["sire"] is None:
                raise forms.ValidationError("Parents required for hatched birds")
            if data["dam"].species != data["sire"].species:
                raise forms.ValidationError("Parents must be the same species")
            data["species"] = data["dam"].species
        else:
            if data["species"] is None:
                raise forms.ValidationError(
                    "Species required for non-hatch acquisition"
                )
            data["dam"] = None
            data["sire"] = None
        if Animal.objects.filter(
            band_color=data["band_color"], band_number=data["band_number"]
        ).exists():
            raise forms.ValidationError(
                _(
                    "A bird already exists with band color %(band_color)s and number %(band_number)d."
                ),
                code="invalid",
                params=data,
            )
        return data

    def create_chick(self):
        data = self.cleaned_data
        chick = Animal(
            species=data["species"],
            sex=data["sex"],
            plumage=data["plumage"],
            band_color=data["band_color"],
            band_number=data["band_number"],
        )
        chick.save()
        if data["sire"] and data["dam"]:
            Parent.objects.create(child=chick, parent=data["sire"])
            Parent.objects.create(child=chick, parent=data["dam"])
            chick.save()
        evt = Event(
            animal=chick,
            date=data["acq_date"],
            status=data["acq_status"],
            description=data["comments"],
            location=data["location"],
            entered_by=data["user"],
        )
        evt.save()
        evt = Event(
            animal=chick,
            date=data["banding_date"],
            status=data["band_status"],
            location=data["location"],
            description=chick.band(),
            entered_by=data["user"],
        )
        evt.save()
        return chick


class ClutchForm(forms.Form):
    sire = forms.ModelChoiceField(queryset=Animal.living.filter(sex__exact="M"))
    dam = forms.ModelChoiceField(queryset=Animal.living.filter(sex__exact="F"))
    chicks = forms.IntegerField(min_value=1)
    hatch_date = forms.DateField()
    location = forms.ModelChoiceField(queryset=Location.objects.all())
    comments = forms.CharField(widget=forms.Textarea, required=False)
    user = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))

    def clean(self):
        super(ClutchForm, self).clean()
        try:
            self.cleaned_data["status"] = Status.objects.get(name__startswith="hatch")
        except ObjectDoesNotExist:
            raise forms.ValidationError("No 'hatch' status type - add one in admin")
        if (
            "dam" in self.cleaned_data
            and "sire" in self.cleaned_data
            and self.cleaned_data["dam"].species != self.cleaned_data["sire"].species
        ):
            raise forms.ValidationError("Parents must be the same species")
        return self.cleaned_data

    def create_clutch(self):
        ret = {"chicks": [], "events": []}
        for i in range(self.cleaned_data["chicks"]):
            chick = Animal(species=self.cleaned_data["sire"].species, sex="U")
            chick.save()
            Parent.objects.create(child=chick, parent=self.cleaned_data["sire"])
            Parent.objects.create(child=chick, parent=self.cleaned_data["dam"])
            chick.save()
            evt = Event(
                animal=chick,
                date=self.cleaned_data["hatch_date"],
                status=self.cleaned_data["status"],
                description=self.cleaned_data["comments"],
                location=self.cleaned_data["location"],
                entered_by=self.cleaned_data["user"],
            )
            evt.save()
            ret["chicks"].append(chick)
            ret["events"].append(evt)
        return ret
