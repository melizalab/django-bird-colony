# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import uuidfield.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Age',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(max_length=16)),
                ('min_days', models.PositiveIntegerField()),
                ('max_days', models.PositiveIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Animal',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('sex', models.CharField(choices=[('M', 'male'), ('F', 'female'), ('U', 'unknown')], max_length=2)),
                ('band_number', models.IntegerField(blank=True, null=True)),
                ('uuid', uuidfield.fields.UUIDField(unique=True, blank=True, editable=False, max_length=32)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['band_color', 'band_number'],
            },
        ),
        migrations.CreateModel(
            name='Color',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(max_length=12)),
                ('abbrv', models.CharField(max_length=3, verbose_name='Abbreviation')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('date', models.DateField(default=datetime.date.today)),
                ('description', models.TextField(blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('animal', models.ForeignKey(to='birds.Animal')),
                ('entered_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(max_length=45)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Species',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('common_name', models.CharField(max_length=45)),
                ('genus', models.CharField(max_length=45)),
                ('species', models.CharField(max_length=45)),
                ('code', models.CharField(max_length=4)),
            ],
            options={
                'ordering': ['common_name'],
                'verbose_name_plural': 'species',
            },
        ),
        migrations.CreateModel(
            name='Status',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(max_length=16)),
                ('count', models.SmallIntegerField(choices=[(0, '0'), (-1, '-1'), (1, '+1')], help_text='1: animal acquired; -1: animal lost; 0: no change', default=0)),
                ('category', models.CharField(max_length=2, blank=True, choices=[('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E')], null=True)),
                ('description', models.TextField()),
            ],
            options={
                'ordering': ['name'],
                'verbose_name_plural': 'status codes',
            },
        ),
        migrations.AddField(
            model_name='event',
            name='location',
            field=models.ForeignKey(to='birds.Location', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='status',
            field=models.ForeignKey(to='birds.Status'),
        ),
        migrations.AddField(
            model_name='animal',
            name='band_color',
            field=models.ForeignKey(to='birds.Color', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='animal',
            name='parents',
            field=models.ManyToManyField(to='birds.Animal', blank=True),
        ),
        migrations.AddField(
            model_name='animal',
            name='reserved_by',
            field=models.ForeignKey(help_text='mark a bird as reserved for a specific user', null=True, to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='animal',
            name='species',
            field=models.ForeignKey(to='birds.Species'),
        ),
        migrations.AddField(
            model_name='age',
            name='species',
            field=models.ForeignKey(to='birds.Species'),
        ),
    ]
