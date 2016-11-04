# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('birds', '0003_datacollection_datatype_recording'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datacollection',
            name='name',
            field=models.CharField(help_text='a short name for the collection', max_length=16),
        ),
        migrations.AlterField(
            model_name='datacollection',
            name='uri',
            field=models.CharField(help_text='canonical URL for retrieving a recording in this collection', max_length=512),
        ),
        migrations.AlterField(
            model_name='recording',
            name='identifier',
            field=models.CharField(help_text='canonical identifier for this recording', max_length=128),
        ),
    ]
