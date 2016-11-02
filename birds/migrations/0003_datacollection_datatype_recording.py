# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('birds', '0002_auto_20150626_1219'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataCollection',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=16)),
                ('uri', models.CharField(max_length=512)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='DataType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=16)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Recording',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('identifier', models.CharField(max_length=128)),
                ('timestamp', models.DateTimeField(blank=True, null=True)),
                ('animal', models.ForeignKey(to='birds.Animal')),
                ('collection', models.ForeignKey(to='birds.DataCollection')),
                ('datatype', models.ForeignKey(blank=True, to='birds.DataType', null=True)),
            ],
            options={
                'ordering': ['animal', 'collection', 'identifier'],
            },
        ),
    ]
