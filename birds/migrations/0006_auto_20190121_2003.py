# Generated by Django 2.1.5 on 2019-01-22 01:03

import birds.models
import datetime
from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('birds', '0005_auto_20190119_1603'),
    ]

    operations = [
        migrations.CreateModel(
            name='Sample',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False, unique=True)),
                ('consumed', models.BooleanField(default=False, help_text='set this field if the sample is no longer available')),
                ('attributes', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, help_text='specify additional sample-specific attributes')),
                ('comments', models.TextField(blank=True)),
                ('date', models.DateField(default=datetime.date.today, help_text='date of sample collection')),
                ('animal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='birds.Animal')),
                ('collected_by', models.ForeignKey(on_delete=models.SET(birds.models.get_sentinel_user), to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['animal', 'type'],
            },
        ),
        migrations.CreateModel(
            name='SampleLocation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='SampleType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=16, unique=True)),
                ('description', models.CharField(max_length=64, unique=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='sample',
            name='location',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='birds.SampleLocation'),
        ),
        migrations.AddField(
            model_name='sample',
            name='source',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='birds.Sample'),
        ),
        migrations.AddField(
            model_name='sample',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='birds.SampleType'),
        ),
    ]
