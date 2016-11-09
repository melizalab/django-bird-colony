# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-09 17:15
from __future__ import unicode_literals

from django.db import migrations

def clear_animals(apps, schema_editor):
    Animal = apps.get_model("birds", "Animal")
    for animal in Animal.objects.all():
        animal.delete()

def clear_events(apps, schema_editor):
    Event = apps.get_model("birds", "Event")
    for event in Event.objects.all():
        event.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('birds', '0002_auto_20161109_1215'),
    ]

    operations = [
        # remove all animals; will need to repopulate
        migrations.RunPython(clear_animals, migrations.RunPython.noop),
        migrations.RunPython(clear_events, migrations.RunPython.noop)
    ]