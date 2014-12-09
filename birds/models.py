# -*- coding: utf-8 -*-
# -*- mode: python -*-
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.db import models

from django.contrib.auth.models import User
from uuidfield import UUIDField
import datetime

class Species(models.Model):
    common_name = models.CharField(max_length=45)
    genus = models.CharField(max_length=45)
    species = models.CharField(max_length=45)
    code = models.CharField(max_length=4)

    def __unicode__(self):
        return self.common_name

    class Meta:
        ordering = ['common_name']
        verbose_name_plural = 'species'


class Color(models.Model):
    name = models.CharField(max_length=12)
    abbrv = models.CharField('Abbreviation', max_length=3)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Status(models.Model):
    name = models.CharField(max_length=16)
    count = models.SmallIntegerField(default=0, choices=((0, '0'), (-1, '-1'), (1, '+1')),
                                     help_text="1: animal acquired; -1: animal lost; 0: no change")
    category = models.CharField(max_length=2, choices=(('B','B'),('C','C'),('D','D'),('E','E')),
                                blank=True, null=True)
    description = models.TextField()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'status codes'


class Location(models.Model):
    name = models.CharField(max_length=45)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Age(models.Model):
    name = models.CharField(max_length=16)
    min_days = models.PositiveIntegerField()
    max_days = models.PositiveIntegerField()
    species = models.ForeignKey('Species')

    def __unicode__(self):
        return "%s %s (%d-%d days)" % (self.species, self.name, self.min_days, self.max_days)


class LivingAnimalManager(models.Manager):
    def get_queryset(self):
        return super(LivingAnimalManager, self).get_queryset().exclude(event__status__count=-1)


class Animal(models.Model):
    MALE = 'M'
    FEMALE = 'F'
    UNKNOWN_SEX = 'U'
    SEX_CHOICES = (
        (MALE, 'male'),
        (FEMALE, 'female'),
        (UNKNOWN_SEX, 'unknown')
    )

    species = models.ForeignKey('Species')
    sex = models.CharField(max_length=2, choices=SEX_CHOICES)
    band_color = models.ForeignKey('Color', blank=True, null=True)
    band_number = models.IntegerField(blank=True, null=True)
    uuid = UUIDField(auto=True, hyphenate=True)
    parents = models.ManyToManyField('Animal', blank=True)

    reserved_by = models.ForeignKey(User, blank=True, null=True,
                                    help_text="mark a bird as reserved for a specific user")

    created = models.DateTimeField(auto_now_add=True)

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

    def __unicode__(self):
        return self.name()

    def sire(self):
        try:
            return self.parents.filter(sex__exact='M')[0]
        except IndexError:
            return None

    def dam(self):
        try:
            return self.parents.filter(sex__exact='F')[0]
        except IndexError:
            return None

    def alive(self):
        """ Returns True if the bird is alive """
        return sum(evt.status.count for evt in self.event_set.all()) > 0

    def nchildren(self):
        """ Returns (living, total) children """
        chicks = self.animal_set
        # probably inefficient
        return (sum(1 for a in chicks.iterator() if a.alive()), chicks.count())

    objects = models.Manager()
    living = LivingAnimalManager()

    def acquisition_event(self):
        """ Returns event when bird was acquired.

        Returns None if no acquisition events
        """
        return self.event_set.filter(status__count=1).order_by('date').first()

    def age_days(self):
        """ Returns days since acquisition_event"""
        try:
            return (datetime.date.today() - self.acquisition_event().date).days
        except AttributeError:
            pass

    def get_absolute_url(self):
        return reverse("birds:bird", kwargs={'pk': self.pk})

    class Meta:
        ordering = ['band_color', 'band_number']


class Event(models.Model):

    animal = models.ForeignKey('Animal')
    date = models.DateField(default=datetime.date.today)
    status = models.ForeignKey('Status')
    location = models.ForeignKey('Location', blank=True, null=True)
    description = models.TextField(blank=True)

    entered_by = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return "%s: %s on %s" % (self.animal, self.status, self.date)

    def event_date(self):
        """ Description of event and date """
        return "%s on %s" % (self.status, self.date)

    class Meta:
        ordering = ['-date']
