# -*- coding: utf-8 -*-
# -*- mode: python -*-
from __future__ import unicode_literals

import datetime
import uuid
from functools import lru_cache
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import (
    Case,
    CheckConstraint,
    Count,
    DateField,
    F,
    Max,
    Min,
    OuterRef,
    Q,
    Subquery,
    Sum,
    When,
)
from django.db.models.functions import Cast, Now, Trunc, TruncDay
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

BIRTH_EVENT_NAME = "hatched"
DEATH_EVENT_NAME = "died"
UNBORN_ANIMAL_NAME = "egg"
UNBORN_CREATION_EVENT_NAME = "laid"
ADULT_ANIMAL_NAME = "adult"
LOST_EVENT_NAME = "lost"
MOVED_EVENT_NAME = "moved"
NOTE_EVENT_NAME = "note"
BANDED_EVENT_NAME = "banded"
RESERVATION_EVENT_NAME = "reservation"


@lru_cache
def get_birth_event_type():
    return Status.objects.get(name=BIRTH_EVENT_NAME)


@lru_cache
def get_unborn_creation_event_type():
    return Status.objects.get(name=UNBORN_CREATION_EVENT_NAME)


@lru_cache
def get_death_event_type():
    return Status.objects.get(name=DEATH_EVENT_NAME)


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
    description = models.TextField(default="")
    nest = models.BooleanField(
        default=False, help_text="select for locations used for breeding"
    )

    def birds(self, on_date: Optional[datetime.date] = None):
        """Returns an AnimalQuerySet with all the birds in this location"""
        return Animal.objects.with_location(on_date=on_date).filter(last_location=self)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("birds:location", kwargs={"pk": self.id})

    class Meta:
        ordering = ["name"]


class Age(models.Model):
    DEFAULT = "unclassified"

    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=16,
    )
    # it may be possible to do this with an IntegerRangeField
    min_days = models.PositiveIntegerField()
    species = models.ForeignKey("Species", on_delete=models.CASCADE)

    def __str__(self):
        return "%s %s (≥ %d days)" % (self.species, self.name, self.min_days)

    class Meta:
        unique_together = ("name", "species")


class AnimalManager(models.Manager):
    def create_with_event(
        self,
        species: Species,
        *,
        date: datetime.date,
        status: Status,
        entered_by: settings.AUTH_USER_MODEL,
        location: Location,
        description: Optional[str] = None,
        **animal_properties,
    ):
        """Create a new animal and add a creation event"""
        animal = self.create(species=species, **animal_properties)
        _event = Event.objects.create(
            animal=animal,
            date=date,
            status=status,
            location=location,
            entered_by=entered_by,
            description=description or "",
        )
        return animal

    def create_from_parents(
        self,
        *,
        sire: "Animal",
        dam: "Animal",
        date: datetime.date,
        status: Status,
        entered_by: settings.AUTH_USER_MODEL,
        location: Location,
        description: Optional[str] = None,
        **animal_properties,
    ):
        species = sire.species
        if species != dam.species:
            raise ValueError("sire and dam species do not match")
        animal = self.create_with_event(
            species,
            date=date,
            status=status,
            entered_by=entered_by,
            location=location,
            description=description,
            **animal_properties,
        )
        animal.parents.set([sire, dam])
        animal.save()
        return animal


class AnimalQuerySet(models.QuerySet):
    """Supports queries based on status that require joining on the event table"""

    def with_dates(self, on_date: Optional[datetime.date] = None):
        """Annotate the birds with important dates (born, died, etc)

        Warning: use this before filtering birds on related events (e.g.
        with alive(), hatched(), or existed_on()), as the annotations depend on having
        all the events.

        """
        if on_date is None:
            on_date = datetime.date.today()
        q_date = Q(event__date__lte=on_date)
        return self.annotate(
            first_event_on=Min(
                "event__date", filter=Q(event__status__removes=False) & q_date
            ),
            born_on=Min(
                "event__date", filter=Q(event__status__name="hatched") & q_date
            ),
            died_on=Max("event__date", filter=Q(event__status__removes=True) & q_date),
            acquired_on=Min("event__date", filter=Q(event__status__adds=True) & q_date),
            alive=Case(
                When(died_on__isnull=False, then=False),
                When(acquired_on__isnull=True, then=False),
                default=True,
            ),
            age=Case(
                When(born_on__isnull=True, then=None),
                When(died_on__isnull=True, then=on_date - F("born_on")),
                default=F("died_on") - F("born_on"),
            ),
        )

    def with_location(self, on_date: Optional[datetime.date] = None):
        refdate = on_date or datetime.date.today()
        # return self.prefetch_related(
        #     Prefetch(
        #         "event_set",
        #         queryset=Event.objects.has_location().order_by("-date", "-created"),
        #         to_attr="locations",
        #     )
        # )
        return self.annotate(
            last_location=Subquery(
                Event.objects.filter(
                    location__isnull=False,
                    date__lte=refdate,
                    animal=OuterRef("pk"),
                )
                .order_by("-date", "-created")
                .values("location__name")[:1]
                # .values(data=JSONObject(id="location__pk", name="location__name"))[:1]
            ),
        )

    def with_child_counts(self):
        # TODO fix me - very slow
        return self.annotate(
            n_children=Count(
                "children", filter=Q(children__event__status=get_birth_event_type())
            )
        )

    def with_annotations(self, on_date: Optional[datetime.date] = None):
        return self.with_dates(on_date).with_location(on_date)

    def with_related(self):
        return self.select_related(
            "reserved_by", "species", "band_color"
        ).prefetch_related("species__age_set")

    def hatched(self, on_date: Optional[datetime.date] = None):
        """Only birds that were born in the colony (excludes eggs)."""
        return self.with_dates(on_date).filter(born_on__isnull=False)

    def unhatched(self, on_date: Optional[datetime.date] = None):
        """Only birds that were not born in the colony (includes eggs)"""
        return self.with_dates(on_date).filter(
            first_event_on__isnull=False, born_on__isnull=True
        )

    def alive(self, on_date: Optional[datetime.date] = None):
        """Only birds that are alive (added but not removed)"""
        return self.with_dates(on_date).filter(alive=True)

    def existing(self, on_date: Optional[datetime.date] = None):
        """Only birds that have not been removed"""
        return self.with_dates(on_date).filter(
            first_event_on__isnull=False, died_on__isnull=True
        )

    def ancestors_of(self, animal, generation: int = 1):
        """All ancestors of animal at specified generation"""
        key = "__".join(("children",) * generation)
        kwargs = {key: animal}
        return self.filter(**kwargs)

    def descendents_of(self, animal, generation: int = 1):
        """All descendents of animal at specified generation"""
        key = "__".join(("parents",) * generation)
        kwargs = {key: animal}
        return self.filter(**kwargs)


class Parent(models.Model):
    id = models.AutoField(primary_key=True)
    child = models.ForeignKey("Animal", related_name="+", on_delete=models.CASCADE)
    parent = models.ForeignKey("Animal", related_name="+", on_delete=models.CASCADE)

    def __str__(self):
        return "%s -> %s" % (self.parent, self.child)


class Animal(models.Model):
    class Sex(models.TextChoices):
        MALE = "M", _("male")
        FEMALE = "F", _("female")
        UNKNOWN_SEX = "U", _("unknown")

    species = models.ForeignKey("Species", on_delete=models.PROTECT)
    sex = models.CharField(max_length=2, choices=Sex.choices, default=Sex.UNKNOWN_SEX)
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
    objects = AnimalManager.from_queryset(AnimalQuerySet)()

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

    @cached_property
    def name(self):
        return "%s_%s" % (self.species.code, self.band() or self.short_uuid())

    def __str__(self):
        return self.name

    def sire(self):
        # find the male parent in python to avoid hitting the database again if
        # parents were prefetched
        return next((p for p in self.parents.all() if p.sex == Animal.Sex.MALE), None)

    def dam(self):
        return next((p for p in self.parents.all() if p.sex == Animal.Sex.FEMALE), None)

    def sexed(self):
        return self.sex != Animal.Sex.UNKNOWN_SEX

    def acquisition_event(self):
        """Returns event when bird was acquired.

        If there are multiple acquisition events, returns the most recent one.
        Returns None if no acquisition events.

        """
        return self.event_set.filter(status__adds=True).last()

    def age(self, on_date: Optional[datetime.date] = None):
        """Returns age (as of date).

        Age is days since birthdate if alive, age at death if dead, or None if
        unknown. This method is masked if with_dates() is used on the queryset.

        """
        refdate = on_date or datetime.date.today()
        events = self.event_set.filter(date__lte=refdate).aggregate(
            born_on=Min("date", filter=Q(status=get_birth_event_type())),
            died_on=Max("date", filter=Q(status__removes=True)),
        )
        if events["born_on"] is None:
            return None
        if events["died_on"] is None:
            return refdate - events["born_on"]
        else:
            return events["died_on"] - events["born_on"]

    def alive(self, on_date: Optional[datetime.date] = None):
        """Returns true if the bird is alive (as of date).

        This method is masked if with_dates() is used on the queryset.
        """
        refdate = on_date or datetime.date.today()
        is_alive = self.event_set.filter(date__lte=refdate).aggregate(
            added=Sum(Cast("status__adds", models.IntegerField())),
            removed=Sum(Cast("status__removes", models.IntegerField())),
        )
        return (is_alive["added"] or 0) > (is_alive["removed"] or 0)

    def age_group(self, on_date: Optional[datetime.date] = None):
        """Returns the age group of the animal by joining on the Age model.

        Classified as an adult if there was a non-hatch acquisition event.
        Otherwise, an egg if there was at least one non-acquisition event.
        Otherwise, None. Returns None if there is no match in the Age
        table (this can only happen if there is not an object with min_age = 0).

        This method can only be used if the object was retrieved using the
        with_dates() annotation.

        """
        refdate = on_date or datetime.date.today()
        if self.born_on is None or self.born_on > refdate:
            if self.acquired_on is not None and self.acquired_on <= refdate:
                return ADULT_ANIMAL_NAME
            elif self.first_event_on is not None and self.first_event_on <= refdate:
                return UNBORN_ANIMAL_NAME
            else:
                return None
        if self.died_on is None or self.died_on > refdate:
            age = refdate - self.born_on
        else:
            age = self.died_on - self.born_on
        age_days = age.days
        # faster to do this lookup in python if age_set is prefetched
        groups = sorted(
            filter(
                lambda ag: ag.min_days <= age_days,
                self.species.age_set.all(),
            ),
            key=lambda ag: ag.min_days,
            reverse=True,
        )
        try:
            return groups[0].name
        except IndexError:
            pass

    def expected_hatch(self):
        """For eggs, expected hatch date. None if not an egg, lost, already
        hatched, or incubation time is not known.

        """
        days = self.species.incubation_days
        if days is None:
            pass
        elif self.event_set.filter(
            Q(status__adds__gt=0) | Q(status__removes__gt=0)
        ).exists():
            pass
        else:
            evt_laid = self.event_set.filter(status=get_unborn_creation_event_type())
            if evt_laid.exists():
                return evt_laid.earliest().date + datetime.timedelta(days=days)

    def last_location(self, on_date: Optional[datetime.date] = None):
        """Returns the location recorded in the most recent event before `on_date`
        (today if not specified). This method will be masked if with_location()
        is used on the queryset.

        """
        refdate = on_date or datetime.date.today()
        try:
            return (
                self.event_set.select_related("location")
                .filter(date__lte=refdate)
                .exclude(location__isnull=True)
                .latest()
                .location
            )
        except (AttributeError, Event.DoesNotExist):
            return None

    def pairings(self):
        """Returns all pairings involving this animal as sire or dam"""
        return Pairing.objects.filter(Q(sire=self) | Q(dam=self))

    def birth_pairing(self):
        """Return the pairing to which this animal was born (or None)"""
        # find birthday (or when egg was laid
        events = self.event_set.aggregate(
            born_on=Min(
                "date",
                filter=Q(
                    status__name__in=(UNBORN_CREATION_EVENT_NAME, BIRTH_EVENT_NAME)
                ),
            )
        )
        if events["born_on"] is None:
            return None
        return (
            Pairing.objects.filter(
                sire=self.sire(),
                dam=self.dam(),
            )
            .exclude(began_on__gte=events["born_on"])
            .exclude(ended_on__lte=events["born_on"])
            .first()
        )

    def get_absolute_url(self):
        return reverse("birds:animal", kwargs={"uuid": self.uuid})

    def update_sex(
        self,
        sex: Sex,
        entered_by: settings.AUTH_USER_MODEL,
        date: datetime.date,
        *,
        description: Optional[str] = None,
    ):
        """Update the animal's sex and create an event to note this"""
        status = Status.objects.get(name=NOTE_EVENT_NAME)
        self.sex = sex
        self.save()
        return Event.objects.create(
            animal=self,
            date=date,
            status=status,
            entered_by=entered_by,
            description=description or f"sexed as {sex}",
        )

    def update_band(
        self,
        band_number: int,
        date: datetime.date,
        entered_by: settings.AUTH_USER_MODEL,
        *,
        band_color: Optional[Color] = None,
        sex: Optional[Sex] = None,
        plumage: Optional[Plumage] = None,
        location: Optional[Location] = None,
    ):
        """Update the animal's band and create an event to note this"""
        status = Status.objects.get(name=BANDED_EVENT_NAME)
        self.band_number = band_number
        if band_color:
            self.band_color = band_color
        if sex:
            self.sex = sex
        if plumage:
            self.plumage = plumage
        self.save()
        return Event.objects.create(
            animal=self,
            date=date,
            status=status,
            entered_by=entered_by,
            location=location,
            description=f"banded as {self.band()}",
        )

    class Meta:
        ordering = ["band_color", "band_number"]


class EventQuerySet(models.QuerySet):
    def with_related(self):
        return self.select_related(
            "animal",
            "animal__species",
            "animal__band_color",
            "status",
            "location",
            "entered_by",
        )

    def has_location(self):
        return self.exclude(location__isnull=True)

    def latest_by_animal(self):
        return self.order_by("animal_id", "-date", "-created").distinct("animal_id")

    def in_month(self, date: Optional[datetime.date] = None):
        """Only events in a given month (the current one if None)"""
        if date is None:
            date = datetime.date.today()
        month = datetime.date(year=date.year, month=date.month, day=1)
        return self.annotate(
            month=Trunc("date", "month", output_field=DateField())
        ).filter(month=month)

    def count_by_status(self):
        return self.values("status__name").annotate(count=Count("id"))


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

    objects = EventQuerySet.as_manager()

    def __str__(self):
        return "%s: %s on %s" % (self.animal, self.status, self.date)

    def event_date(self):
        """Description of event and date"""
        return "%s on %s" % (self.status, self.date)

    def age(self):
        """Age of the animal at the time of the event, or None if birthday not known"""
        events = self.animal.event_set.filter(status=get_birth_event_type())
        if events:
            evt_birth = events.earliest()
            if evt_birth is not None and self.date >= evt_birth.date:
                return self.date - evt_birth.date

    class Meta:
        ordering = ["-date", "-created"]
        indexes = [
            models.Index(fields=["animal", "status"], name="animal_status_idx"),
            models.Index(fields=["animal", "date"], name="animal_date_idx"),
        ]
        get_latest_by = ["date", "created"]


class PairingManager(models.Manager):
    def create_with_events(
        self,
        *,
        sire: Animal,
        dam: Animal,
        began_on: datetime.date,
        purpose: str,
        entered_by: settings.AUTH_USER_MODEL,
        location: Location,
    ):
        """Create a new pairing and add events to the sire and dam"""
        status = Status.objects.get(name=MOVED_EVENT_NAME)
        pairing = self.create(
            sire=sire, dam=dam, began_on=began_on, ended_on=None, purpose=purpose
        )
        _sire_event = Event.objects.create(
            animal=sire,
            date=began_on,
            status=status,
            location=location,
            entered_by=entered_by,
            description=f"Paired with {dam}",
        )
        _dam_event = Event.objects.create(
            animal=dam,
            date=began_on,
            status=status,
            location=location,
            entered_by=entered_by,
            description=f"Paired with {sire}",
        )
        return pairing


class PairingQuerySet(models.QuerySet):
    def active(self, on_date: Optional[datetime.date] = None):
        on_date = on_date or datetime.date.today()
        return self.filter(
            Q(began_on__lte=on_date), Q(ended_on__isnull=True) | Q(ended_on__gt=on_date)
        )

    def active_between(self, since: datetime.date, until: datetime.date):
        return self.filter(
            Q(began_on__lte=until), Q(ended_on__isnull=True) | Q(ended_on__gt=since)
        )

    def with_related(self):
        return self.select_related(
            "sire",
            "dam",
            "sire__species",
            "sire__band_color",
            "dam__species",
            "dam__band_color",
        )

    def with_progeny_stats(self):
        qq_before_ended = Q(sire__children__event__date__lte=F("ended_on")) | Q(
            ended_on__isnull=True
        )
        qq_after_began = Q(sire__children__event__date__gte=F("began_on"))
        return self.annotate(
            n_progeny=Count(
                "sire__children",
                filter=Q(sire__children__event__status=get_birth_event_type())
                & qq_after_began
                & qq_before_ended,
            ),
            n_eggs=Count(
                "sire__children",
                filter=Q(sire__children__event__status=get_unborn_creation_event_type())
                & qq_after_began
                & qq_before_ended,
            ),
        )

    def with_location(self):
        """Active pairs only, annotated with the *name* of the most recent location"""
        return self.active().annotate(
            last_location=Subquery(
                Event.objects.filter(
                    Q(location__isnull=False),
                    Q(date__gte=OuterRef("began_on")),
                    (Q(animal=OuterRef("sire")) | Q(animal=OuterRef("dam"))),
                )
                .order_by("-date", "-created")
                .values("location__name")[:1]
            )
        )


class Pairing(models.Model):
    id = models.AutoField(primary_key=True)
    sire = models.ForeignKey(
        "Animal",
        on_delete=models.CASCADE,
        related_name="+",
        limit_choices_to={"sex": Animal.Sex.MALE},
    )
    dam = models.ForeignKey(
        "Animal",
        on_delete=models.CASCADE,
        related_name="+",
        limit_choices_to={"sex": Animal.Sex.FEMALE},
    )
    began_on = models.DateField(help_text="date the animals were paired")
    ended_on = models.DateField(
        null=True, blank=True, help_text="date the pairing ended"
    )
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

    objects = PairingManager.from_queryset(PairingQuerySet)()

    def __str__(self):
        return f"{self.short_name()} ({self.began_on} - {self.ended_on})"

    def short_name(self):
        return f"♂{self.sire} × ♀{self.dam}"  # noqa: RUF001

    def get_absolute_url(self):
        return reverse("birds:pairing", kwargs={"pk": self.id})

    def active(self, on_date: Optional[datetime.date] = None) -> bool:
        on_date = on_date or datetime.date.today()
        if on_date < self.began_on:
            return False
        return self.ended_on is None or self.ended_on > on_date

    def oldest_living_progeny_age(self):
        # this is slow, but I'm not sure how to do it any faster
        params = {
            "event__status__name": BIRTH_EVENT_NAME,
            "event__date__gte": self.began_on,
        }
        if self.ended_on is not None:
            params["event__date__lte"] = self.ended_on
        qs = self.sire.children.with_dates().filter(**params)
        # ages = [a.age_days() for a in qs if a.alive]
        # return max(ages, default=None)
        agg = qs.annotate(
            age=Case(
                When(born_on__isnull=True, then=None),
                When(died_on__isnull=True, then=TruncDay(Now()) - F("born_on")),
                default=None,
            )
        ).aggregate(Max("age"))
        return agg["age__max"]

    def eggs(self):
        """All the eggs laid during this pairing (hatched and unhatched)"""
        d_query = Q(first_event_on__gte=self.began_on)
        if self.ended_on is not None:
            d_query &= Q(first_event_on__lte=self.ended_on)
        qs = Animal.objects.filter(parents=self.sire).filter(parents=self.dam)
        return qs.with_dates().filter(d_query)

    def events(self):
        """All events for the pair and their progeny during the pairing"""
        qs = Event.objects.filter(
            Q(animal__in=self.eggs()) | Q(animal__in=(self.sire, self.dam)),
            date__gte=self.began_on,
        )
        if self.ended_on is not None:
            qs = qs.filter(date__lte=self.ended_on)
        return qs.order_by("date")

    def last_location(self, on_date: Optional[datetime.date] = None):
        """Returns the location recorded in the most recent event for the sire
        or dam. For an inactive pair, only events between the beginning and
        ending are considered. For an active pair, only dates between the
        beginning and `on_date` (or today if not specified) are considered.
        Returns None if no events match these criteria. This method will be
        masked if with_location() is used on the queryset.

        """
        end_date = on_date or self.ended_on or datetime.date.today()
        qs = Event.objects.filter(
            animal__in=(self.sire, self.dam),
            date__gte=self.began_on,
            date__lte=end_date,
        )
        try:
            return qs.exclude(location__isnull=True).latest().location
        except (AttributeError, Event.DoesNotExist):
            return None

    def other_pairings(self):
        """Returns queryset with all other pairings of this sire and dam"""
        return Pairing.objects.filter(sire=self.sire, dam=self.dam).exclude(id=self.id)

    def create_egg(
        self,
        date: datetime.date,
        *,
        entered_by: settings.AUTH_USER_MODEL,
        location: Optional[Location] = None,
        description: Optional[str] = None,
        **animal_properties,
    ):
        """Create an egg and associated event for the pair"""
        if date < self.began_on:
            raise ValueError(_("Date must be on or after start of pairing"))
        if self.ended_on is not None and date > self.ended_on:
            raise ValueError(_("Date must be on or before end of pairing"))
        return Animal.objects.create_from_parents(
            sire=self.sire,
            dam=self.dam,
            date=date,
            status=get_unborn_creation_event_type(),
            entered_by=entered_by,
            location=location,
            description=description,
            **animal_properties,
        )

    def close(
        self,
        ended_on: datetime.date,
        entered_by: settings.AUTH_USER_MODEL,
        *,
        location: Optional[Location] = None,
        comment: Optional[str] = None,
        remove_unhatched: bool = False,
    ):
        """Close an active pairing. Marks all remaining eggs as lost.

        Raises a ValueError if the pairing is not active. Sets ended date and a
        comment on the model. If `location` is not None, adds "moved" events to
        the sire and the dam. If `remove_unhatched` is True, adds "lost" events
        to all unhatched eggs.

        """
        if not self.active():
            raise ValueError("Pairing is already closed")
        self.ended_on = ended_on
        self.comment = comment or ""
        self.save()  # will throw integrity error if ended_on <= began_on
        status = Status.objects.get(name=MOVED_EVENT_NAME)
        if location is not None:
            Event.objects.create(
                animal=self.sire,
                date=ended_on,
                status=status,
                entered_by=entered_by,
                location=location,
                description=f"Ended pairing with {self.dam}",
            )
            Event.objects.create(
                animal=self.dam,
                date=ended_on,
                status=status,
                entered_by=entered_by,
                location=location,
                description=f"Ended pairing with {self.sire}",
            )
        if remove_unhatched:
            unhatched_eggs = self.eggs().unhatched().existing()
            lost_event = Status.objects.get(name=LOST_EVENT_NAME)
            for egg in unhatched_eggs:
                Event.objects.create(
                    animal=egg,
                    date=ended_on,
                    status=lost_event,
                    entered_by=entered_by,
                    description="marked as lost when pairing ended",
                )

    def clean(self):
        """Validate the pairing"""
        if self.sire.sex != Animal.Sex.MALE:
            raise ValidationError(_("Sire must be a male"))
        if self.dam.sex != Animal.Sex.FEMALE:
            raise ValidationError(_("Dam must be a female"))
        if self.ended_on is not None and self.ended_on <= self.began_on:
            raise ValidationError(_("End date must be after start date"))

    class Meta:
        ordering = ["-began_on", "-ended_on"]
        constraints = [
            CheckConstraint(
                check=Q(ended_on__isnull=True) | Q(ended_on__gt=F("began_on")),
                name="ended_on_gt_began_on",
            )
        ]


class NestCheck(models.Model):
    id = models.AutoField(primary_key=True)
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET(get_sentinel_user)
    )
    datetime = models.DateTimeField()
    comments = models.TextField(blank=True)

    def __str__(self):
        return "{} at {}".format(self.entered_by, self.datetime)


class SampleType(models.Model):
    """Doefines a type of biological sample"""

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
        return "%s:%s" % (self.animal.name, self.type.name)

    def get_absolute_url(self):
        return reverse("birds:sample", kwargs={"uuid": self.uuid})

    class Meta:
        ordering = ["animal", "type"]
