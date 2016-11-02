# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid
from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('birds', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='animal',
            name='uuid',
            field=models.UUIDField(name='uuid', default=uuid.uuid4),
        ),
    ]
