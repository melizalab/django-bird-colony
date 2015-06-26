# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuidfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('birds', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='animal',
            name='uuid',
            field=uuidfield.fields.UUIDField(auto=True, name='uuid', hyphenate=True),
        ),
    ]
