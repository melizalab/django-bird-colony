# -*- coding: utf-8 -*-
# -*- mode: python -*-
from __future__ import unicode_literals

import uuid
import datetime

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.urls import reverse
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

BIRTH_EVENT_NAME = "hatched"
UNBORN_ANIMAL_NAME = "egg"
UNBORN_CREATION_EVENT_NAME = "laid"
ADULT_ANIMAL_NAME = "adult"
LOST_EVENT_NAME = "lost"
MOVED_EVENT_NAME = "moved"
NOTE_EVENT_NAME = "note"
RESERVATION_EVENT_NAME = "reservation"


def get_sentinel_user():
    return get_user_model().objects.get_or_create(username="deleted")[0]


class Species(models.Model):
    id = models.AutoField(primary_key=True)
    common_name = models.CharField(max_length=45)
    genus = models.CharField(max_length=45)
    species = models.CharField(max_length=45)
    code = models.CharField(max_length=4, unique=True)
    incubation_days = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return self.common_name

    class Meta:
        ordering = ["common_name"]
        verbose_name_plural = "species"
        unique_together = ("genus", "species")


class Color(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=12, unique=True)
    abbrv = models.CharField("Abbreviation", max_length=3, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Plumage(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=16, unique=True)
    description = models.TextField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "plumage variants"


class Status(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=16, unique=True)
    adds = models.BooleanField(default=False, help_text="select for acquisition events")
    removes = models.BooleanField(
        default=False, help_text="select for loss/death/removal events"
    )
    description = models.TextField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "status codes"


class Location(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=45, unique=True)
    nest = models.BooleanField(
        default=False, help_text="select for locations used for breeding"
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Age(models.Model):
    DEFAULT = "unclassified"

    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=16,
    )
    min_days = models.PositiveIntegerField()
    species = models.ForeignKey("Species", on_delete=models.CASCADE)

    def __str__(self):
        return "%s %s (≥ %d days)" % (self.species, self.name, self.min_days)

    class Meta:
        unique_together = ("name", "species")


class AnimalManager(models.Manager):
    """Annotates animal list with 'alive' field by counting add/remove events"""

    def get_queryset(self):
        from django.db.models import Count, Q, Value
        from django.db.models.functions import Greatest

        qs = super(AnimalManager, self).get_queryset()
        return qs.annotate(
            alive=Greatest(
                0,
                Count("event", filter=Q(event__status__adds=True))
                - Count("event", filter=Q(event__status__removes=True)),
            )
        ).order_by("band_color", "band_number")


class LivingAnimalManager(AnimalManager):
    def get_queryset(self):
        qs = super(LivingAnimalManager, self).get_queryset()
        return qs.filter(alive__gt=0)

    def on(self, date):
        """Only include birds that were alive on date (added and not removed)"""
        from django.db.models import Count, Q
        from django.db.models.functions import Greatest

        qs = super(AnimalManager, self).get_queryset()
        return (
            qs.annotate(
                alive=Greatest(
                    0,
                    Count(
                        "event",
                        filter=Q(event__date__lte=date, event__status__adds=True),
                    )
                    - Count(
                        "event",
                        filter=Q(event__date__lte=date, event__status__removes=True),
                    ),
                )
            )
            .filter(alive__gt=0)
            .order_by("band_color", "band_number")
        )

    def exists(self, date):
        """Only include birds that existed on date (created but not removed)"""
        from django.db.models import Count, Q

        qs = super(AnimalManager, self).get_queryset()
        return (
            qs.annotate(
                noted=Count(
                    "event",
                    filter=Q(event__date__lte=date, event__status__removes=False),
                ),
                removed=Count(
                    "event",
                    filter=Q(event__date__lte=date, event__status__removes=True),
                ),
            )
            .filter(noted__gt=0, removed__lte=0)
            .order_by("band_color", "band_number")
        )


class LastEventManager(models.Manager):
    """Filters queryset so that only the most recent event is returned"""

    def get_queryset(self):
        qs = super(LastEventManager, self).get_queryset()
        return (
            qs.exclude(location__isnull=True)
            .order_by("animal_id", "-date", "-created")
            .distinct("animal_id")
        )


class Parent(models.Model):
    id = models.AutoField(primary_key=True)
    child = models.ForeignKey("Animal", related_name="+", on_delete=models.CASCADE)
    parent = models.ForeignKey("Animal", related_name="+", on_delete=models.CASCADE)

    def __str__(self):
        return "%s -> %s" % (self.parent, self.child)


class Animal(models.Model):
    MALE = "M"
    FEMALE = "F"
    UNKNOWN_SEX = "U"
    SEX_CHOICES = ((MALE, "male"), (FEMALE, "female"), (UNKNOWN_SEX, "unknown"))

    species = models.ForeignKey("Species", on_delete=models.PROTECT)
    sex = models.CharField(max_length=2, choices=SEX_CHOICES)
    band_color = models.ForeignKey(
        "Color", on_delete=models.SET_NULL, blank=True, null=True
    )
    band_number = models.IntegerField(blank=True, null=True)
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True)
    parents = models.ManyToManyField(
        "Animal",
        related_name="children",
        through="Parent",
        through_fields=("child", "parent"),
    )

    reserved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET(get_sentinel_user),
        help_text="mark a bird as reserved for a specific user",
    )
    created = models.DateTimeField(auto_now_add=True)
    plumage = models.ForeignKey(
        "Plumage", on_delete=models.SET_NULL, blank=True, null=True
    )
    attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text="specify additional attributes for the animal",
    )

    def short_uuid(self):
        return str(self.uuid).split("-")[0]

    def band(self):
        if self.band_number:
            if self.band_color:
                return "%s_%d" % (self.band_color, self.band_number)
            else:
                return "%d" % self.band_number
        else:
            return None

    def name(self):
        return "%s_%s" % (self.species.code, self.band() or self.short_uuid())

    def __str__(self):
        return self.name()

    def sire(self):
        return self.parents.filter(sex__exact="M").first()

    def dam(self):
        return self.parents.filter(sex__exact="F").first()

    def sexed(self):
        return self.sex != Animal.UNKNOWN_SEX

    def living_children(self):
        return self.children.exclude(event__status__removes=True)

    def all_children(self):
        """Returns all of the children that hatched"""
        return self.children.filter(event__status__adds=True)

    def unhatched(self):
        """Returns all the unhatched eggs"""
        return self.children.exclude(event__status__adds=True)

    objects = AnimalManager()
    living = LivingAnimalManager()

    def acquisition_event(self):
        """Returns event when bird was acquired.

        If there are multiple acquisition events, returns the most recent one.
        Returns None if no acquisition events.

        """
        return self.event_set.filter(status__adds=True).last()

    def age_days(self, date=None):
        """Returns days since birthdate (as of date) if alive, age at death if dead, or None if unknown"""
        refdate = date or datetime.date.today()
        event_set = self.event_set.filter(date__lte=refdate)
        evt_birth = event_set.filter(status__name=BIRTH_EVENT_NAME).first()
        if evt_birth is None:
            return None
        evt_death = event_set.filter(status__removes=True).last()
        if evt_death is None:
            return (refdate - evt_birth.date).days
        else:
            return (evt_death.date - evt_birth.date).days

    def age_group(self, date=None):
        """Returns the age group of the animal (as of date) by joining on the Age model.

        Classified as an adult if there was a non-hatch acquisition event.
        Otherwise, an egg if there was at least one non-acquisition event.
        Otherwise, None. Returns "unclassified" if there is no match in the Age
        table (this can only happen if there is not an object with min_age = 0).

        """
        refdate = date or datetime.date.today()
        event_set = self.event_set.filter(date__lte=refdate)
        event_set_adds = event_set.filter(status__adds=True)
        event_birth = event_set_adds.filter(status__name=BIRTH_EVENT_NAME).first()
        if event_birth is None:
            if event_set_adds.count() > 0:
                return ADULT_ANIMAL_NAME
            elif event_set.count() == 0:
                return None
            else:
                return UNBORN_ANIMAL_NAME
        else:
            event_death = event_set.filter(status__removes=True).last()
            if event_death is None:
                age_days = (refdate - event_birth.date).days
            else:
                age_days = (event_death.date - event_birth.date).days
            grp = (
                self.species.age_set.filter(min_days__lte=age_days)
                .order_by("-min_days")
                .first()
            )
            return grp.name if grp is not None else Age.DEFAULT

    def expected_hatch(self):
        """For eggs, expected hatch date. None if not an egg, already hatched, or incubation time is not known."""
        days = self.species.incubation_days
        if days is None:
            return None
        try:
            q = self.event_set.filter(status__name=BIRTH_EVENT_NAME).get()
            return None
        except ObjectDoesNotExist:
            pass
        try:
            evt_laid = self.event_set.filter(
                status__name=UNBORN_CREATION_EVENT_NAME
            ).earliest()
            return evt_laid.date + datetime.timedelta(days=days)
        except ObjectDoesNotExist:
            return None

    def last_location(self):
        """Returns the location recorded in the most recent event"""
        try:
            return self.event_set.exclude(location__isnull=True).latest().location
        except AttributeError:
            return None

    def pairings(self):
        """Returns all pairings involving this animal"""
        from django.db.models import Q

        return Pairing.objects.filter(Q(sire=self) | Q(dam=self))

    def get_absolute_url(self):
        return reverse("birds:animal", kwargs={"uuid": self.uuid})

    class Meta:
        ordering = ["band_color", "band_number"]


class Event(models.Model):
    id = models.AutoField(primary_key=True)
    animal = models.ForeignKey("Animal", on_delete=models.CASCADE)
    date = models.DateField(default=datetime.date.today)
    status = models.ForeignKey("Status", on_delete=models.PROTECT)
    location = models.ForeignKey(
        "Location", blank=True, null=True, on_delete=models.SET_NULL
    )
    description = models.TextField(blank=True)

    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET(get_sentinel_user)
    )
    created = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()
    latest = LastEventManager()

    def __str__(self):
        return "%s: %s on %s" % (self.animal, self.status, self.date)

    def event_date(self):
        """Description of event and date"""
        return "%s on %s" % (self.status, self.date)

    class Meta:
        ordering = ["-date", "-created"]
        get_latest_by = ["date", "created"]


class Pairing(models.Model):
    id = models.AutoField(primary_key=True)
    sire = models.ForeignKey(
        "Animal",
        on_delete=models.CASCADE,
        related_name="+",
        limit_choices_to={"sex": Animal.MALE},
    )
    dam = models.ForeignKey(
        "Animal",
        on_delete=models.CASCADE,
        related_name="+",
        limit_choices_to={"sex": Animal.FEMALE},
    )
    began = models.DateField(help_text="date the animals were paired")
    ended = models.DateField(null=True, blank=True, help_text="date the pairing ended")
    created = models.DateTimeField(auto_now_add=True)
    purpose = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="purpose of the pairing (leave blank if unknown)",
    )
    comment = models.TextField(
        blank=True, help_text="notes on the outcome of the pairing"
    )

    def __str__(self):
        return "♂{} × ♀{} ({} — {})".format(
            self.sire, self.dam, self.began, self.ended or ""
        )

    def get_absolute_url(self):
        return reverse("birds:pairing", kwargs={"pk": self.id})

    def active(self):
        return self.ended is None

    def progeny(self):
        """Queryset with all the chicks hatched during this pairing"""
        # TODO: restrict to children who match both parents
        qs = self.sire.children.filter(
            event__status__name=BIRTH_EVENT_NAME, event__date__gte=self.began
        )
        if self.ended:
            return qs.filter(event__date__lte=self.ended)
        return qs

    def oldest_living_progeny_age(self):
        # probably quite slow
        ages = [a.age_days() for a in self.progeny() if a.alive]
        return max(ages, default=None)

    def eggs(self):
        """Queryset with all the eggs laid during this pairing"""
        # TODO: restrict to children who match both parents
        # We have to include hatch events here too for older pairings because
        # eggs were not entered prior to ~2021
        from django.db.models import Q

        qs = self.sire.children.filter(
            event__status__name__in=(UNBORN_CREATION_EVENT_NAME, BIRTH_EVENT_NAME),
            event__date__gte=self.began,
        )
        if self.ended:
            qs = qs.filter(event__date__lte=self.ended)
        return qs

    def related_events(self):
        """Queryset with all events for the pair and their progeny during the pairing"""
        from django.db.models import Q

        qs = Event.objects.filter(
            Q(animal__in=self.eggs()) | Q(animal__in=(self.sire, self.dam)),
            date__gte=self.began,
        )
        if self.ended:
            qs = qs.filter(date__lte=self.ended)
        return qs.order_by("date")

    def last_location(self):
        """Returns the most recent location in the pairing"""
        qs = Event.objects.filter(
            animal__in=(self.sire, self.dam),
            date__gte=self.began,
        )
        if self.ended:
            qs = qs.filter(date__lte=self.ended)
        try:
            return qs.exclude(location__isnull=True).latest().location
        except AttributeError:
            return None

    def clean(self):
        # ended must be after began
        if self.ended is not None and self.ended <= self.began:
            raise ValidationError(_("End date must be after the pairing began"))

    class Meta:
        ordering = ["-began", "-ended"]


class NestCheck(models.Model):
    id = models.AutoField(primary_key=True)
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET(get_sentinel_user)
    )
    datetime = models.DateTimeField(default=datetime.datetime.now)
    comments = models.TextField(blank=True)

    def __str__(self):
        return "{} at {}".format(self.entered_by, self.datetime)


class SampleType(models.Model):
    """Defines a type of biological sample"""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=16, unique=True)
    description = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class SampleLocation(models.Model):
    """Defines a location where a sample can be stored"""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Sample(models.Model):
    """Defines a specific sample, which may be derived from another sample"""

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True)
    type = models.ForeignKey(SampleType, on_delete=models.CASCADE)
    animal = models.ForeignKey("Animal", on_delete=models.CASCADE)
    source = models.ForeignKey("self", blank=True, null=True, on_delete=models.SET_NULL)
    location = models.ForeignKey(
        SampleLocation, blank=True, null=True, on_delete=models.SET_NULL
    )
    attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text="specify additional sample-specific attributes",
    )
    comments = models.TextField(blank=True)

    date = models.DateField(
        default=datetime.date.today,
        blank=True,
        null=True,
        help_text="date of sample collection (blank if not known)",
    )
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET(get_sentinel_user)
    )

    def short_uuid(self):
        return str(self.uuid).split("-")[0]

    def __str__(self):
        return "%s:%s" % (self.animal.name(), self.type.name)

    def get_absolute_url(self):
        return reverse("birds:sample", kwargs={"uuid": self.uuid})

    class Meta:
        ordering = ["animal", "type"]
