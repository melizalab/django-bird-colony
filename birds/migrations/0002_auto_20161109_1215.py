# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-09 17:15
from __future__ import unicode_literals

import birds.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('birds', '0001_squashed_0009_auto_20161108_1647'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='animal',
            name='id',
        ),
        migrations.AlterField(
            model_name='animal',
            name='band_color',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='birds.Color'),
        ),
        migrations.AlterField(
            model_name='animal',
            name='reserved_by',
            field=models.ForeignKey(blank=True, help_text='mark a bird as reserved for a specific user', null=True, on_delete=models.SET(birds.models.get_sentinel_user), to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='animal',
            name='species',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='birds.Species'),
        ),
        migrations.AlterField(
            model_name='animal',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False, unique=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='entered_by',
            field=models.ForeignKey(on_delete=models.SET(birds.models.get_sentinel_user), to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='event',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='birds.Location'),
        ),
        migrations.AlterField(
            model_name='event',
            name='status',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='birds.Status'),
        ),
        migrations.AlterField(
            model_name='recording',
            name='datatype',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='birds.DataType'),
        ),
    ]
