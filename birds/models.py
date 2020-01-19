# -*- coding: utf-8 -*-
# -*- mode: python -*-
from __future__ import unicode_literals

import uuid
import datetime

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils.encoding import python_2_unicode_compatible
from django.urls import reverse
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

BIRTH_EVENT_NAME = "hatched"
UNBORN_ANIMAL_NAME = "egg"
UNBORN_CREATION_EVENT_NAME = "laid"
ADULT_ANIMAL_NAME = "adult"
LOST_EVENT_NAME = "lost"

def get_sentinel_user():
    return get_user_model().objects.get_or_create(username='deleted')[0]


@python_2_unicode_compatible
class Species(models.Model):
    common_name = models.CharField(max_length=45)
    genus = models.CharField(max_length=45)
    species = models.CharField(max_length=45)
    code = models.CharField(max_length=4, unique=True)
    incubation_days = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return self.common_name

    class Meta:
        ordering = ['common_name']
        verbose_name_plural = 'species'
        unique_together = ("genus", "species")


@python_2_unicode_compatible
class Color(models.Model):
    name = models.CharField(max_length=12, unique=True)
    abbrv = models.CharField('Abbreviation', max_length=3, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


@python_2_unicode_compatible
class Plumage(models.Model):
    name = models.CharField(max_length=16, unique=True)
    description = models.TextField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'plumage variants'



@python_2_unicode_compatible
class Status(models.Model):
    name = models.CharField(max_length=16, unique=True)
    adds = models.BooleanField(default=False, help_text="select for acquisition events")
    removes = models.BooleanField(default=False, help_text="select for loss/death/removal events")
    description = models.TextField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'status codes'


@python_2_unicode_compatible
class Location(models.Model):
    name = models.CharField(max_length=45, unique=True)
    nest = models.BooleanField(default=False, help_text="select for locations used for breeding")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


@python_2_unicode_compatible
class Age(models.Model):
    DEFAULT = "unclassified"

    name = models.CharField(max_length=16,)
    min_days = models.PositiveIntegerField()
    species = models.ForeignKey('Species', on_delete=models.CASCADE)

    def __str__(self):
        return "%s %s (≥ %d days)" % (self.species, self.name, self.min_days)

    class Meta:
        unique_together = ("name", "species")


class AnimalManager(models.Manager):
    """Annotates animal list with 'alive' field by counting add/remove events """
    def get_queryset(self):
        from django.db.models import Count, Q, Value
        from django.db.models.functions import Greatest
        qs = super(AnimalManager, self).get_queryset()
        return (qs
                .annotate(alive=Greatest(0,
                                         Count('event', filter=Q(event__status__adds=True)) -
                                         Count('event', filter=Q(event__status__removes=True))))
                .order_by("band_color", "band_number"))


class LivingAnimalManager(AnimalManager):
    def get_queryset(self):
        qs = super(LivingAnimalManager, self).get_queryset()
        return qs.filter(alive__gt=0)

    def on(self, date):
        """ Only include birds that were alive on date (added and not removed) """
        from django.db.models import Count, Q
        from django.db.models.functions import Greatest
        qs = super(AnimalManager, self).get_queryset()
        return (qs
                .annotate(alive=Greatest(0,
                                         Count('event', filter=Q(event__date__lte=date,
                                                                 event__status__adds=True)) -
                                         Count('event', filter=Q(event__date__lte=date,
                                                                 event__status__removes=True))))
                .filter(alive__gt=0)
                .order_by("band_color", "band_number"))

    def exists(self, date):
        """ Only include birds that existed on date (created but not removed) """
        from django.db.models import Count, Q
        qs = super(AnimalManager, self).get_queryset()
        return (qs
                .annotate(noted=Count('event', filter=Q(event__date__lte=date,
                                                        event__status__removes=False)),
                          removed=Count('event', filter=Q(event__date__lte=date,
                                                          event__status__removes=True)))
                .filter(noted__gt=0, removed__lte=0)
                .order_by("band_color", "band_number"))


class LastEventManager(models.Manager):
    """ Filters queryset so that only the most recent event is returned """
    def get_queryset(self):
        qs = super(LastEventManager, self).get_queryset()
        return qs.exclude(location__isnull=True).order_by("animal_id", "-date").distinct("animal_id")


@python_2_unicode_compatible
class Parent(models.Model):
    child = models.ForeignKey('Animal', related_name="+", on_delete=models.CASCADE)
    parent = models.ForeignKey('Animal', related_name="+", on_delete=models.CASCADE)

    def __str__(self):
        return "%s -> %s" % (self.parent, self.child)


@python_2_unicode_compatible
class Animal(models.Model):
    MALE = 'M'
    FEMALE = 'F'
    UNKNOWN_SEX = 'U'
    SEX_CHOICES = (
        (MALE, 'male'),
        (FEMALE, 'female'),
        (UNKNOWN_SEX, 'unknown')
    )

    species = models.ForeignKey('Species', on_delete=models.PROTECT)
    sex = models.CharField(max_length=2, choices=SEX_CHOICES)
    band_color = models.ForeignKey('Color', on_delete=models.SET_NULL,
                                   blank=True, null=True)
    band_number = models.IntegerField(blank=True, null=True)
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True)
    parents = models.ManyToManyField('Animal',
                                     related_name='children',
                                     through='Parent',
                                     through_fields=('child', 'parent'))

    reserved_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    blank=True, null=True,
                                    on_delete=models.SET(get_sentinel_user),
                                    help_text="mark a bird as reserved for a specific user")
    created = models.DateTimeField(auto_now_add=True)
    plumage = models.ForeignKey('Plumage', on_delete=models.SET_NULL, blank=True, null=True)
    attributes = JSONField(default=dict, blank=True, help_text="specify additional attributes for the animal")

    def short_uuid(self):
        return str(self.uuid).split('-')[0]

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
        return self.parents.filter(sex__exact='M').first()

    def dam(self):
        return self.parents.filter(sex__exact='F').first()

    def nchildren(self):
        """ Returns (living, total) children """
        chicks = self.children
        return (chicks.exclude(event__status__removes=True).count(),
                chicks.count())

    objects = AnimalManager()
    living = LivingAnimalManager()

    def acquisition_event(self):
        """Returns event when bird was acquired.

        If there are multiple acquisition events, returns the most recent one.
        Returns None if no acquisition events.

        """
        return self.event_set.filter(status__adds=True).last()

    def age_days(self, date=None):
        """ Returns days since birthdate (as of date) if alive, age at death if dead, or None if unknown"""
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
            grp = self.species.age_set.filter(min_days__lte=age_days).order_by('-min_days').first()
            return grp.name if grp is not None else Age.DEFAULT


    def expected_hatch(self):
        """ For eggs, expected hatch date. None if not an egg, already hatched, or incubation time is not known. """
        days = self.species.incubation_days
        if days is None:
            return None
        try:
            q = self.event_set.filter(status__name=BIRTH_EVENT_NAME).get()
            return None
        except ObjectDoesNotExist:
            pass
        try:
            evt_laid = self.event_set.filter(status__name=UNBORN_CREATION_EVENT_NAME).earliest()
            return evt_laid.date + datetime.timedelta(days=days)
        except ObjectDoesNotExist:
            return None

    def last_location(self):
        """ Returns the location recorded in the most recent event """
        try:
            return self.event_set.exclude(location__isnull=True).latest().location
        except AttributeError:
            return None

    def get_absolute_url(self):
        return reverse("birds:animal", kwargs={'uuid': self.uuid})

    class Meta:
        ordering = ['band_color', 'band_number']


@python_2_unicode_compatible
class Event(models.Model):
    animal = models.ForeignKey('Animal', on_delete=models.CASCADE)
    date = models.DateField(default=datetime.date.today)
    status = models.ForeignKey('Status', on_delete=models.PROTECT)
    location = models.ForeignKey('Location', blank=True, null=True, on_delete=models.SET_NULL)
    description = models.TextField(blank=True)

    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET(get_sentinel_user))
    created = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()
    latest = LastEventManager()

    def __str__(self):
        return "%s: %s on %s" % (self.animal, self.status, self.date)

    def event_date(self):
        """ Description of event and date """
        return "%s on %s" % (self.status, self.date)

    class Meta:
        ordering = ['-date', '-created']
        get_latest_by = ['date', 'created']

@python_2_unicode_compatible
class NestCheck(models.Model):
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET(get_sentinel_user))
    datetime = models.DateTimeField(default=datetime.datetime.now)
    comments = models.TextField(blank=True)

    def __str__(self):
        return "{} at {}".format(self.entered_by, self.datetime)


@python_2_unicode_compatible
class SampleType(models.Model):
    """ Defines a type of biological sample """
    name = models.CharField(max_length=16, unique=True)
    description = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


@python_2_unicode_compatible
class SampleLocation(models.Model):
    """ Defines a location where a sample can be stored """
    name = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


@python_2_unicode_compatible
class Sample(models.Model):
    """ Defines a specific sample, which may be derived from another sample """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True)
    type = models.ForeignKey(SampleType, on_delete=models.CASCADE)
    animal = models.ForeignKey("Animal", on_delete=models.CASCADE)
    source = models.ForeignKey("self", blank=True, null=True, on_delete=models.SET_NULL)
    location = models.ForeignKey(SampleLocation, blank=True, null=True, on_delete=models.SET_NULL)
    attributes = JSONField(default=dict, blank=True,
                           help_text="specify additional sample-specific attributes")
    comments = models.TextField(blank=True)

    date = models.DateField(default=datetime.date.today,
                            blank=True, null=True,
                            help_text="date of sample collection (blank if not known)")
    collected_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET(get_sentinel_user))

    def short_uuid(self):
        return str(self.uuid).split('-')[0]

    def __str__(self):
        return "%s:%s" % (self.animal.name(), self.type.name)

    def get_absolute_url(self):
        return reverse("birds:sample", kwargs={'uuid': self.uuid})

    class Meta:
        ordering = ['animal', 'type']
