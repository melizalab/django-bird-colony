# Generated by Django 2.2.9 on 2020-01-16 16:41

import birds.models
import datetime
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('birds', '0011_auto_20200110_1510'),
    ]

    operations = [
        migrations.AlterField(
            model_name='species',
            name='incubation_days',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='NestCheck',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateTimeField(default=datetime.datetime.now)),
                ('comments', models.TextField(blank=True)),
                ('entered_by', models.ForeignKey(on_delete=models.SET(birds.models.get_sentinel_user), to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
