# -*- mode: python -*-

import datetime
import uuid
from collections.abc import Sequence
from functools import lru_cache
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import (
    CheckConstraint,
    Count,
    DateField,
    Exists,
    F,
    Max,
    Min,
    OuterRef,
    Q,
    Subquery,
    Value,
    Window,
)
from django.db.models.functions import Coalesce, Now, RowNumber, Trunc, TruncDay
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.formats import date_format
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
    """Represents an animal species. Every animal belongs to a species."""

    id = models.AutoField(primary_key=True)
    common_name = models.CharField(max_length=45)
    genus = models.CharField(max_length=45)
    species = models.CharField(max_length=45)
    code = models.CharField(max_length=4, unique=True)
    incubation_days = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self) -> str:
        return self.common_name

    class Meta:
        ordering = ("common_name",)
        verbose_name_plural = "species"
        unique_together = ("genus", "species")


class Color(models.Model):
    """Represents a band color. Animals may be banded, and the bands can be colored."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=12, unique=True)
    abbrv = models.CharField("Abbreviation", max_length=3, unique=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "band colors"


class Plumage(models.Model):
    """Represents a plumage type.

    This is pretty rudimentary and should be expanded into a more detailed trait system.
    """

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=16, unique=True)
    description = models.TextField()

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "plumage variants"


class Status(models.Model):
    """Represents a type of event in the life of an animal.

    Event types with the `adds` field set to True are for events that add a living
    animal to the colony (e.g., hatching, transferring in). The `removes` field is an
    enum that indicates whether the event removes the animal from the colony and whether
    it was expected or unexpected. This allows the database to determine the dates when
    animals were alive and distinguish between different kinds of removal events.

    """

    class AdditionType(models.TextChoices):
        EGG = ("egg", "Adds an unborn animal")
        BIRTH = ("birth", "Adds a living animal")
        TRANSFER = ("transfer", "Transfers animal into the colony")
        __empty__ = "Not an addition"

    class RemovalType(models.TextChoices):
        EXPECTED = ("expected", "Expected death or removal")
        UNEXPECTED = ("unexpected", "Unexpected death")
        __empty__ = "Not a removal"

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=16, unique=True)
    adds = models.CharField(
        max_length=10,
        choices=AdditionType.choices,
        null=True,
        blank=True,
        help_text="type of addition event, or None for events that don't add an animal",
    )
    removes = models.CharField(
        max_length=10,
        choices=RemovalType.choices,
        null=True,
        blank=True,
        help_text="type of removal event, or None for events that don't remove an animal",
    )
    description = models.TextField()

    def __str__(self) -> str:
        return self.name

    def effect(self) -> str | None:
        """Summarize the effect of the event"""
        if self.adds is not None:
            return Status.AdditionType(self.adds).label
        elif self.removes is not None:
            return Status.RemovalType(self.removes).label

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "status codes"
        indexes = (
            models.Index(fields=("adds",), name="add_type_idx"),
            models.Index(fields=("removes",), name="remove_type_idx"),
        )
        constraints = (
            CheckConstraint(
                check=Q(adds__isnull=True) | Q(removes__isnull=True),
                name="adds_or_removes_null",
            ),
        )


class Measure(models.Model):
    """Represents a type of measurement, like weight, with associated units"""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=16, unique=True)
    unit_sym = models.CharField(
        "SI unit symbol",
        max_length=8,
        help_text="SI symbol for the unit of the measure (including prefix)",
    )
    unit_full = models.CharField(
        "SI unit name",
        max_length=16,
        help_text="full SI name for the unit of the measure",
    )
    format_str = models.CharField(
        "Format string",
        max_length=8,
        default="{:.1f}",
        help_text="how to format values for this measure (use Python str.format() mini-language)",
    )

    def __str__(self) -> str:
        return f"{self.name} ({self.unit_sym})"

    class Meta:
        verbose_name_plural = "measurement types"


class Measurement(models.Model):
    """Represents a measurement taken from an animal.

    Measurements are associated with events. This is more complex than
    associating them with animals, but it makes some downstream views easier to
    generate. There can only be one measurement of each type associated with
    each event.

    """

    id = models.AutoField(primary_key=True)
    type = models.ForeignKey("Measure", on_delete=models.CASCADE)
    event = models.ForeignKey(
        "Event", related_name="measurements", on_delete=models.CASCADE
    )
    # different measures will require different degrees of precision, so we use
    # FloatField here instead of DecimalField.
    value = models.FloatField(help_text="the value of the measurement")
    created = models.DateTimeField(auto_now_add=True)

    @property
    def formatted(self) -> str:
        val = self.type.format_str.format(self.value)
        return f"{val} {self.type.unit_sym}"

    def __str__(self) -> str:
        event = self.event
        return f"{event.animal}: {self.type.name} {self.formatted} on {event.date}"

    class Meta:
        unique_together = ("type", "event")


class Location(models.Model):
    """Represents a physical location in the colony.

    Locations with the `nest` field set to True are designed as breeding
    locations.

    """

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=45, unique=True)
    description = models.TextField(default="")
    # This field should probably be deprecated, as some locations are not
    # permanently used for breeding.
    nest = models.BooleanField(
        default=False, help_text="select for locations used for breeding"
    )

    def birds(self, on_date: datetime.date | None = None):
        """Returns an AnimalQuerySet with all the birds in this location"""
        return Animal.objects.with_location(on_date=on_date).filter(last_location=self)

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse("birds:location", kwargs={"pk": self.id})

    class Meta:
        ordering = ("name",)


class Age(models.Model):
    """Represents a named range of ages for a species.

    For example, a zebra finch between 0 and 18 days is considered a hatchling.

    """

    DEFAULT = "unclassified"

    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=16,
    )
    # it may be possible to do this with an IntegerRangeField
    min_days = models.PositiveIntegerField()
    species = models.ForeignKey("Species", on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.species} {self.name} (≥ {self.min_days:d} days)"

    class Meta:
        ordering = ("-min_days",)  # ensure that ages are sorted
        unique_together = ("name", "species")
        verbose_name_plural = "age ranges"


class AnimalManager(models.Manager):
    def create_with_event(
        self,
        species: Species,
        *,
        date: datetime.date,
        status: Status,
        entered_by: settings.AUTH_USER_MODEL,
        location: Location,
        description: str | None = None,
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
        description: str | None = None,
        **animal_properties,
    ):
        species = sire.species
        if species != dam.species:
            raise ValueError(_("sire and dam species do not match"))
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

    def with_location(self, on_date: datetime.date | None = None):
        """Annotate the birds with their location as of `on_date`"""
        refdate = on_date or datetime.date.today()
        return self.annotate(
            last_location=Subquery(
                Event.objects.filter(
                    location__isnull=False,
                    date__lte=refdate,
                    animal=OuterRef("pk"),
                )
                .order_by("-date", "-created")
                .values("location__name")[:1]
            ),
        )

    def with_dates(self, on_date: datetime.date | None = None):
        """Annotate the birds with important dates and current status using events on or prior to `on_date`.

        Generally, use cached life_history intead of this method.

        """
        if on_date is None:
            on_date = datetime.date.today()
        q_date = Q(event__date__lte=on_date)

        return self.annotate(
            # Dates needed for age and age_group calculation
            first_event_on=Min(
                "event__date",
                filter=q_date,
            ),
            laid_on=Min(
                "event__date",
                filter=Q(event__status__adds=Status.AdditionType.EGG) & q_date,
            ),
            born_on=Min(
                "event__date",
                filter=Q(event__status__adds=Status.AdditionType.BIRTH) & q_date,
            ),
            acquired_on=Min(
                "event__date",
                filter=Q(
                    event__status__adds__in=(
                        Status.AdditionType.BIRTH,
                        Status.AdditionType.TRANSFER,
                    )
                )
                & q_date,
            ),
            # the animal is no longer alive as far as this colony is concerned
            died_on=Max(
                "event__date", filter=Q(event__status__removes__isnull=False) & q_date
            ),
            # Flags for status determination
            has_unexpected_removal=Exists(
                Event.objects.filter(
                    animal=OuterRef("pk"),
                    status__removes=Status.RemovalType.UNEXPECTED,
                    date__lte=on_date,
                )
            ),
        )

    def with_child_counts(self, on_date: datetime.date | None = None):
        """Annotate the birds with child counts (uses life history)."""
        refdate = on_date or datetime.date.today()
        return self.annotate(
            n_eggs=Count(
                "children",
                filter=Q(children__life_history__laid_on__lte=refdate),
            ),
            n_hatched=Count(
                "children",
                filter=Q(children__life_history__born_on__lte=refdate),
            ),
            n_alive=Count(
                "children",
                filter=Q(children__life_history__born_on__lte=refdate)
                & ~Q(children__life_history__died_on__lte=refdate),
            ),
        )

    def with_related(self):
        return self.select_related(
            "life_history",
            "life_history__last_location",
            "reserved_by",
            "species",
            "band_color",
        ).prefetch_related("species__age_set")

    def hatched(self, on_date: datetime.date | None = None):
        """Only birds that were born in the colony (excludes eggs)."""
        refdate = on_date or datetime.date.today()
        return self.filter(life_history__born_on__lte=refdate)

    def unhatched(self, on_date: datetime.date | None = None):
        """Only birds that were not born in the colony (includes eggs)"""
        refdate = on_date or datetime.date.today()
        return self.filter(
            Q(life_history__born_on__isnull=True) | Q(life_history__born_on__gt=refdate)
        )

    def eggs(self, on_date: datetime.date | None = None):
        """Only birds that were eggs on on_date (default today)"""
        refdate = on_date or datetime.date.today()
        return self.unhatched(on_date).filter(life_history__laid_on__lte=refdate)

    def alive(self, on_date: datetime.date | None = None):
        """Only birds that are alive (added but not removed)"""
        refdate = on_date or datetime.date.today()
        return self.filter(life_history__acquired_on__lte=refdate).exclude(
            life_history__died_on__lte=refdate
        )

    def existing(self, on_date: datetime.date | None = None):
        """Only birds/eggs that have not been removed"""
        refdate = on_date or datetime.date.today()
        return self.filter(life_history__first_event_on__lte=refdate).exclude(
            life_history__died_on__lte=refdate
        )

    def lost(self, on_date: datetime.date | None = None):
        """Only birds/eggs that were spontaneously lost due to unexpected causes"""
        refdate = on_date or datetime.date.today()
        return self.filter(
            life_history__has_unexpected_removal=True,
            life_history__died_on__lte=refdate,
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

    def order_by_life_stage(self):
        """List living animals first, then dead, then unborn"""
        return self.order_by(
            "-life_history__died_on", F("life_history__born_on").asc(nulls_last=True)
        )

    def for_pedigree(self):
        """All parents and currently living animals annotated with sire/dam and topologically sorted"""
        return (
            self.select_related("life_history")
            .with_child_counts()
            .filter(Q(n_hatched__gt=0) | Q(life_history__died_on__isnull=True))
            .annotate(
                sire=Subquery(
                    Animal.objects.filter(children=OuterRef("uuid"), sex="M").values(
                        "uuid"
                    )[:1]
                ),
                dam=Subquery(
                    Animal.objects.filter(children=OuterRef("uuid"), sex="F").values(
                        "uuid"
                    )[:1]
                ),
                idx=Window(expression=RowNumber(), order_by=["created", "uuid"]),
            )
            .order_by("idx")
        )


class ParentManger(models.Manager):
    def pedigree_subgraph(self, target_animals: list["Animal"] | None = None):
        """Returns only the instances where the child is in `target_animals` or has its own children"""
        parents_with_kids = Subquery(
            Parent.objects.values_list("parent__uuid", flat=True)
        )
        query = Q(child__uuid__in=parents_with_kids)
        if target_animals:
            query |= Q(child__in=target_animals)
        return Parent.objects.filter(query)

    def pedigree_subgraph_keys(
        self, target_animals: list["Animal"] | None = None
    ) -> list[uuid.UUID, list[uuid.UUID | None]]:
        """Returns the pedigree for all animals with children and `target_animals`

        Each bird is listed with its parents (which can be 2, 1, or 0 birds). The dam is always listed first.

        """
        ped = self.pedigree_subgraph(target_animals)
        founders = ped.exclude(
            parent__in=Subquery(ped.values_list("child__uuid", flat=True))
        ).distinct("parent")
        # these are all the children with their parents
        qs = (
            ped.values("child")
            .annotate(parents=ArrayAgg("parent", ordering="parent__sex"))
            # ensure topological sort
            .order_by("child__created", "child__uuid")
            .values_list("child", "parents")
        )
        return [
            (founder, []) for founder in founders.values_list("parent", flat=True)
        ] + list(qs)


class Parent(models.Model):
    """Represents a parent-child relationship between animals.

    Duplicate relationships are not allowed, but there are no other constraints
    enforced at the model level. In principle, animals should either have no
    parents, if they were transferred in, or exactly one male and one female
    parent, if they were born in the colony, but these invariants have to be
    checked in forms.

    """

    id = models.AutoField(primary_key=True)
    child = models.ForeignKey("Animal", related_name="+", on_delete=models.CASCADE)
    parent = models.ForeignKey("Animal", related_name="+", on_delete=models.CASCADE)
    objects = ParentManger()

    def __str__(self) -> str:
        return f"{self.parent} -> {self.child}"

    class Meta:
        indexes = (
            models.Index(fields=("parent",), name="parent_idx"),
            models.Index(fields=("child",), name="child_idx"),
        )
        unique_together = ("parent", "child")


class Animal(models.Model):
    """Represents an individual animal"""

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

    def short_uuid(self) -> str:
        return str(self.uuid).split("-")[0]

    def band(self) -> str:
        if self.band_number:
            if self.band_color:
                return f"{self.band_color}_{self.band_number:d}"
            else:
                return str(self.band_number)
        else:
            return None

    @cached_property
    def name(self) -> str:
        return f"{self.species.code}_{self.band() or self.short_uuid()}"

    def __str__(self) -> str:
        return self.name

    def sire(self):
        # find the male parent in python to avoid hitting the database again if
        # parents were prefetched
        return next((p for p in self.parents.all() if p.sex == Animal.Sex.MALE), None)

    def dam(self):
        return next((p for p in self.parents.all() if p.sex == Animal.Sex.FEMALE), None)

    def full_siblings(self):
        """Queryset with all the full siblings of this animal (sharing both parents).

        Empty if the bird does not have exactly two parents.
        """
        parents = self.parents.all()
        if parents.count() != 2:
            return Animal.objects.none()
        # we're assuming all the matches have exactly two parents. This isn't
        # enforced in the database but it should be the case if every animal is
        # created using forms that only allow two parents. Could filter on
        # parent count but I don't think it's worth it.
        return (
            Animal.objects.filter(parents=parents[0])
            .filter(parents=parents[1])
            .exclude(uuid=self.uuid)
        )

    def sexed(self) -> bool:
        return self.sex != Animal.Sex.UNKNOWN_SEX

    def acquisition_event(self) -> Optional["Event"]:
        """Returns event when bird was acquired, or None

        Acqusition does not include eggs being laid. If there are multiple acquisition
        events, returns the most recent one.

        """
        return self.event_set.filter(
            status__adds__in=(Status.AdditionType.BIRTH, Status.AdditionType.TRANSFER)
        ).last()

    def removal_event(self) -> Optional["Event"]:
        """Returns event when bird was removed/died/etc, or None

        If there are multiple removal events, returns the first one.

        """
        return self.event_set.filter(status__removes__isnull=False).first()

    def last_location(self, on_date: datetime.date) -> Optional["Location"]:
        """Returns the Location recorded in the most recent event before `on_date`

        Use the cached life_history.last_location if you need the location on the
        current date. Use with_locations() on the queryset if you just need the name of
        the last location as of a given date for a bunch of birds.

        """
        try:
            return (
                self.event_set.select_related("location")
                .filter(date__lte=on_date)
                .exclude(location__isnull=True)
                .latest()
                .location
            )
        except (AttributeError, Event.DoesNotExist):
            return None

    @cached_property
    def history(self):
        """Use this instead of life_history to ensure the record exists"""
        try:
            return self.life_history
        except AnimalLifeHistory.DoesNotExist:
            life_history, created = AnimalLifeHistory.objects.get_or_create(animal=self)
            if created:
                life_history.update_from_events()
                life_history.save()
            return life_history

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
                    status__adds__in=(
                        Status.AdditionType.BIRTH,
                        Status.AdditionType.EGG,
                    )
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

    def measurements(self, on_date=None):
        """Returns the most recent measurements as of `on_date` (today if not
        specified) of each type for this animal.

        """
        refdate = on_date or datetime.date.today()
        qs = Measurement.objects.filter(
            event__animal=self.uuid, event__date__lte=refdate
        )
        return (
            qs.annotate(
                row_num=Window(
                    expression=RowNumber(),
                    partition_by=[F("type")],
                    order_by=F("event__date").desc(),
                )
            )
            .filter(row_num=1)
            .select_related("type", "event")
        )

    def get_absolute_url(self):
        return reverse("birds:animal", kwargs={"uuid": self.uuid})

    def update_sex(
        self,
        sex: Sex,
        entered_by: settings.AUTH_USER_MODEL,
        date: datetime.date,
        *,
        description: str | None = None,
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
        band_color: Color | None = None,
        sex: Sex | None = None,
        plumage: Plumage | None = None,
        location: Location | None = None,
    ) -> "Event":
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

    def add_measurements(
        self,
        measurements: Sequence[tuple[Measure, float]],
        date: datetime.date,
        entered_by: settings.AUTH_USER_MODEL,
        *,
        location: Location | None = None,
        description: str | None = None,
    ) -> "Event":
        """Create an event with one or more associated measurements"""
        status = Status.objects.get(name=NOTE_EVENT_NAME)
        if description is None:
            description = "measured " + " ".join(
                measure.name for measure, _ in measurements
            )
        event = Event.objects.create(
            animal=self,
            date=date,
            status=status,
            entered_by=entered_by,
            location=location,
            description=description,
        )
        for type, value in measurements:
            _ = Measurement.objects.create(event=event, type=type, value=value)
        return event

    class Meta:
        ordering = ["band_color", "band_number"]


class AnimalLifeHistory(models.Model):
    """Life history information for an animal, computed from events and cached"""

    class LifeStage(models.TextChoices):
        EGG = "egg", _("Egg")
        ALIVE = "alive", _("Alive")
        DEAD = "dead", _("Died")
        BAD_EGG = "bad egg", _("Infertile egg")

    class RemovalOutcome(models.TextChoices):
        EXPECTED = "expected", _("Expected death/removal")
        UNEXPECTED = "unexpected", _("Unexpected death")

    id = models.AutoField(primary_key=True)
    animal = models.OneToOneField(
        Animal, on_delete=models.CASCADE, related_name="life_history"
    )

    # Core dates
    first_event_on = models.DateField(null=True, blank=True)
    laid_on = models.DateField(null=True, blank=True)
    born_on = models.DateField(null=True, blank=True)
    acquired_on = models.DateField(null=True, blank=True)
    died_on = models.DateField(null=True, blank=True)

    # Status flags
    has_unexpected_removal = models.BooleanField(default=False)

    # Last location
    last_location = models.ForeignKey(Location, null=True, on_delete=models.SET_NULL)

    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["born_on"]),
            models.Index(fields=["died_on"]),
            models.Index(fields=["has_unexpected_removal"]),
        ]

    def first_event_as_of(self, on_date: datetime.date) -> bool:
        return self.first_event_on is not None and self.first_event_on <= on_date

    def laid_as_of(self, on_date: datetime.date) -> bool:
        return self.laid_on is not None and self.laid_on <= on_date

    def born_as_of(self, on_date: datetime.date) -> bool:
        return self.born_on is not None and self.born_on <= on_date

    def acquired_as_of(self, on_date: datetime.date) -> bool:
        return self.acquired_on is not None and self.acquired_on <= on_date

    def died_as_of(self, on_date: datetime.date) -> bool:
        return self.died_on is not None and self.died_on <= on_date

    def life_stage(self, on_date: datetime.date | None = None) -> LifeStage | None:
        """Returns the life stage of the animal, or None if not calculable"""
        date = on_date or datetime.date.today()

        if not self.first_event_as_of(date):
            pass
        elif self.died_as_of(date):
            if self.acquired_as_of(date):
                return self.LifeStage.DEAD
            else:
                return self.LifeStage.BAD_EGG
        elif self.acquired_as_of(date):
            # Animal has hatched or been transferred into colony - it's alive
            return self.LifeStage.ALIVE
        elif self.laid_as_of(date):
            # Animal was laid as egg but hasn't hatched yet
            return self.LifeStage.EGG

    def age(self, on_date: datetime.date | None = None) -> datetime.timedelta | None:
        """Age of the animal as of today or date of death, or None if not calculable"""
        date = on_date or datetime.date.today()
        if not self.born_as_of(date):
            return None
        end_date = self.died_on if self.died_as_of(date) else date
        return end_date - self.born_on

    def removal_outcome(
        self, on_date: datetime.date | None = None
    ) -> RemovalOutcome | None:
        """Returns the removal outcome if animal is dead, None otherwise"""
        date = on_date or datetime.date.today()

        if not self.died_as_of(date):
            return None
        elif self.has_unexpected_removal:
            return self.RemovalOutcome.UNEXPECTED
        else:
            return self.RemovalOutcome.EXPECTED

    def is_alive(self, on_date: datetime.date | None = None) -> bool:
        """Returns true if the animal is alive on the specified date (default today)"""
        return self.life_stage(on_date) == self.LifeStage.ALIVE

    def died_unexpectedly(self, on_date: datetime.date | None = None) -> bool:
        """Returns true if the animal died unexpectedly on or before the specified date (default today)"""
        return self.removal_outcome(on_date) == self.RemovalOutcome.UNEXPECTED

    def age_group(self, on_date: datetime.date | None = None) -> str | None:
        """Returns the age group of the animal by joining on the Age model.

        If the animal was hatched in the colony, uses the hatch date to
        determine age and then group. Animals acquired through transfer are
        always classified as adults. Otherwise, None. Will also return None if
        there is no match in the Age table (this can only happen if there is not
        an object with min_age = 0).

        This method will be more performant if age_set is prefetched.

        """
        stage = self.life_stage(on_date)

        if stage in (None, self.LifeStage.EGG, self.LifeStage.BAD_EGG):
            return None

        age = self.age(on_date)
        if age is None:
            # Acquired animal with unknown birth date
            return ADULT_ANIMAL_NAME
        age_days = age.days

        # Age groups are pre-sorted by min_days (descending)
        for age_group in self.animal.species.age_set.all():
            if age_group.min_days <= age_days:
                return age_group.name

    def expected_hatch(self) -> datetime.date | None:
        """For eggs, expected hatch date. None if not an egg, lost, already
        hatched, or incubation time is not known.

        """
        days = self.animal.species.incubation_days
        # incubation time not known, no egg laid event, removed, already born
        if (
            days is None
            or self.laid_on is None
            or self.died_on is not None
            or self.born_on is not None
        ):
            pass
        else:
            return self.laid_on + datetime.timedelta(days=days)

    def age_display(self) -> str:
        """Short summary of the bird's current age"""
        age = self.age()
        if age is None:
            return ""
        days = age.days
        return f"{days // 365}y {days % 365}d"

    def status_display(self) -> str:
        """Returns age group for living animals or life stage for others"""
        stage = self.life_stage()
        if stage in (self.LifeStage.EGG, self.LifeStage.BAD_EGG):
            return stage.label.lower()
        elif stage == self.LifeStage.DEAD:
            if self.removal_outcome() == self.RemovalOutcome.UNEXPECTED:
                return "lost"
            else:
                return stage.label.lower()
        elif stage == self.LifeStage.ALIVE:
            age_group = self.age_group()
            return age_group or stage.label.lower()
        else:
            return "unknown"

    def summary(self) -> str:
        """Summarizes the status of the animal for family history. More verbose than status_display."""
        stage = self.life_stage()
        if stage == self.LifeStage.ALIVE:
            age_str = self.age_display()
            if age_str:
                return f"alive, {age_str} old"
            else:
                return "alive, unknown age"
        elif stage == self.LifeStage.DEAD:
            status = (
                "unexpected death"
                if self.died_unexpectedly()
                else "expected death/removal"
            )
            age_str = self.age_display()
            death_date = date_format(self.died_on) if self.died_on else "unknown date"
            if age_str:
                return f"{status} on {death_date} at {age_str} old"
            else:
                return f"{status} on {death_date}"
        elif stage == self.LifeStage.FAILED_EGG:
            death_date = date_format(self.died_on) if self.died_on else "unknown date"
            return f"infertile egg, removed on {death_date}"
        elif stage == self.LifeStage.EGG:
            if self.laid_on:
                laid_date = date_format(self.laid_on)
                return f"egg, laid on {laid_date}"
            else:
                return "egg"
        else:
            return "unknown"

    def update_from_events(self) -> None:
        """Recompute life history - trigger when adding/removing/updating an event for the animal"""
        annotated = Animal.objects.with_dates().get(uuid=self.animal.uuid)
        self.first_event_on = annotated.first_event_on
        self.laid_on = annotated.laid_on
        self.born_on = annotated.born_on
        self.acquired_on = annotated.acquired_on
        self.died_on = annotated.died_on
        self.has_unexpected_removal = annotated.has_unexpected_removal
        self.last_location = self.animal.last_location(datetime.date.today())


class EventQuerySet(models.QuerySet):
    def with_related(self):
        return self.select_related(
            "animal",
            "animal__life_history",
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

    def in_month(self, date: datetime.date | None = None):
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
    """Represents an event in the life of an animal"""

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

    def __str__(self) -> str:
        return f"{self.animal}: {self.status} on {self.date}"

    def event_date(self) -> str:
        """Description of event and date"""
        return f"{self.status} on {self.date:%b %-d, %Y}"

    def age(self) -> datetime.timedelta | None:
        """Age of the animal at the time of the event, or None if birthday not known"""
        try:
            born_on = self.animal.life_history.born_on
            if self.date >= born_on:
                return self.date - born_on
        except (Animal.life_history.RelatedObjectDoesNotExist, TypeError):
            pass

    def age_display(self) -> str:
        """Age at time of event, formatted for display"""
        age = self.age()
        if age is None:
            return ""
        days = age.days
        return f"{days // 365}y {days % 365}d"

    def measures(self):
        """Returns a queryset with all defined Measures. Each Measure is
        annotated with `measurement_value`, which is the value of the
        measurement if one is defined for this event and None otherwise. Useful
        for generating forms and tables.

        """
        return Measure.objects.annotate(
            measurement_value=Coalesce(
                Subquery(
                    Measurement.objects.filter(
                        event=self.id, type=OuterRef("pk")
                    ).values("value")[:1]
                ),
                Value(None),
            )
        )

    class Meta:
        ordering = ("-date", "-created")
        indexes = (
            models.Index(fields=["animal", "status"], name="animal_status_idx"),
            models.Index(fields=["animal", "date"], name="animal_date_idx"),
        )
        get_latest_by = ("date", "created")


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
    def active(self, on_date: datetime.date | None = None):
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
        qq_before_ended = Q(
            sire__children__life_history__born_on__lte=F("ended_on")
        ) | Q(ended_on__isnull=True)
        qq_after_began = Q(sire__children__life_history__born_on__gte=F("began_on"))
        qq_laid_before_ended = Q(
            sire__children__life_history__laid_on__lte=F("ended_on")
        ) | Q(ended_on__isnull=True)
        qq_laid_after_began = Q(
            sire__children__life_history__laid_on__gte=F("began_on")
        )

        return self.annotate(
            n_eggs=Count(
                "sire__children",
                filter=qq_laid_after_began & qq_laid_before_ended,
            ),
            n_hatched=Count(
                "sire__children",
                filter=qq_after_began & qq_before_ended,
            ),
            n_living=Count(
                "sire__children",
                filter=qq_after_began
                & qq_before_ended
                & Q(sire__children__life_history__died_on__isnull=True),
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
    """Represents a pairing of a sire and a dam for breeding.

    Pairings start when a male and female bird are placed together and end when
    they are separated. The pairing is considered to be active between the date
    it started (inclusive) and the date it ended (exclusive). Any eggs laid and animals
    hatched while the pairing is active are associated with the pairing.

    """

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

    def __str__(self) -> str:
        return f"{self.short_name} ({self.date_range()})"

    @cached_property
    def short_name(self) -> str:
        return f"♂{self.sire} × ♀{self.dam}"  # noqa: RUF001

    def date_range(self) -> str:
        return f"{self.began_on} - {self.ended_on or ''}"

    def get_absolute_url(self):
        return reverse("birds:pairing", kwargs={"pk": self.id})

    def active(self, on_date: datetime.date | None = None) -> bool:
        """True if the pairing is active (as of today or on_date, if supplied)"""
        on_date = on_date or datetime.date.today()
        if on_date < self.began_on:
            return False
        return self.ended_on is None or self.ended_on > on_date

    def oldest_living_progeny_age(self) -> datetime.timedelta:
        date_query = Q(life_history__born_on__gte=self.began_on)
        if self.ended_on is not None:
            date_query &= Q(life_history__born_on__lte=self.ended_on)

        qs = self.sire.children.alive().filter(date_query)
        agg = qs.annotate(age=TruncDay(Now()) - F("life_history__born_on")).aggregate(
            Max("age")
        )
        return agg["age__max"]

    def eggs(self) -> AnimalQuerySet:
        """All the eggs laid during this pairing (hatched and unhatched)"""
        d_query = Q(life_history__laid_on__gte=self.began_on)
        if self.ended_on is not None:
            d_query &= Q(life_history__laid_on__lte=self.ended_on)
        return (
            Animal.objects.filter(parents=self.sire)
            .filter(parents=self.dam)
            .filter(d_query)
        )

    def events(self) -> EventQuerySet:
        """All events for the pair and their progeny during the pairing"""
        qs = Event.objects.filter(
            Q(animal__in=self.eggs()) | Q(animal__in=(self.sire, self.dam)),
            date__gte=self.began_on,
        )
        if self.ended_on is not None:
            qs = qs.filter(date__lte=self.ended_on)
        return qs.order_by("date")

    def last_location(self, on_date: datetime.date | None = None) -> Location | None:
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

    def other_pairings(self) -> PairingQuerySet:
        """Returns queryset with all other pairings of this sire and dam"""
        return Pairing.objects.filter(sire=self.sire, dam=self.dam).exclude(id=self.id)

    def create_egg(
        self,
        date: datetime.date,
        *,
        entered_by: settings.AUTH_USER_MODEL,
        location: Location | None = None,
        description: str | None = None,
        **animal_properties,
    ) -> Animal:
        """Create an egg and associated event for the pair.

        Date must be during the pairing.

        """
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
        location: Location | None = None,
        comment: str | None = None,
        remove_unhatched: bool = False,
    ) -> None:
        """Close an active pairing. Marks all remaining eggs as lost.

        Raises a ValueError if the pairing is not active. Sets ended date and a
        comment on the model. If `location` is not None, adds "moved" events to
        the sire and the dam. If `remove_unhatched` is True, adds "lost" events
        to all unhatched eggs.

        """
        if not self.active():
            raise ValueError(_("Pairing is already closed"))
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

    def clean(self) -> None:
        """Validate the pairing"""
        if self.sire.sex != Animal.Sex.MALE:
            raise ValidationError(_("Sire must be a male"))
        if self.dam.sex != Animal.Sex.FEMALE:
            raise ValidationError(_("Dam must be a female"))
        if self.ended_on is not None and self.ended_on <= self.began_on:
            raise ValidationError(_("End date must be after start date"))

    class Meta:
        ordering = ("-began_on", "-ended_on")
        constraints = (
            CheckConstraint(
                check=Q(ended_on__isnull=True) | Q(ended_on__gt=F("began_on")),
                name="ended_on_gt_began_on",
            ),
        )


class NestCheck(models.Model):
    """Represents a nest check, which is when someone counts the number of eggs and chicks for each pairing"""

    id = models.AutoField(primary_key=True)
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET(get_sentinel_user)
    )
    datetime = models.DateTimeField()
    comments = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.entered_by} at {self.datetime}"


class SampleType(models.Model):
    """Defines a type of biological sample"""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=16, unique=True)
    description = models.CharField(max_length=64, unique=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ("name",)


class SampleLocation(models.Model):
    """Defines a location where a sample can be stored"""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=64, unique=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ("name",)


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
        blank=True,
        null=True,
        help_text="date of sample collection (blank if not known)",
    )
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET(get_sentinel_user)
    )

    def short_uuid(self) -> str:
        return str(self.uuid).split("-")[0]

    def __str__(self) -> str:
        return f"{self.animal.name}:{self.type.name}"

    def get_absolute_url(self):
        return reverse("birds:sample", kwargs={"uuid": self.uuid})

    class Meta:
        ordering = ("animal", "type")


### Triggers


@receiver([post_save, post_delete], sender=Event)
def update_life_history_on_event_change(sender, instance, **kwargs):
    """Update life history when events are added/changed/deleted"""
    life_history, _ = AnimalLifeHistory.objects.get_or_create(animal=instance.animal)
    life_history.update_from_events()
    life_history.save()
