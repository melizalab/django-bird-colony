# Generated by Django 3.2.10 on 2022-03-30 16:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('birds', '0012_auto_20200116_1141'),
    ]

    operations = [
        migrations.AlterField(
            model_name='age',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='animal',
            name='attributes',
            field=models.JSONField(blank=True, default=dict, help_text='specify additional attributes for the animal'),
        ),
        migrations.AlterField(
            model_name='color',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='event',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='location',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='nestcheck',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='parent',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='plumage',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='sample',
            name='attributes',
            field=models.JSONField(blank=True, default=dict, help_text='specify additional sample-specific attributes'),
        ),
        migrations.AlterField(
            model_name='samplelocation',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='sampletype',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='species',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='status',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.CreateModel(
            name='Pairing',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('began', models.DateField(help_text='date the animals were paired')),
                ('ended', models.DateField(blank=True, help_text='date the pairing ended', null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('purpose', models.CharField(blank=True, help_text='purpose of the pairing (leave blank if unknown)', max_length=64, null=True)),
                ('comment', models.TextField(blank=True, help_text='notes on the outcome of the pairing')),
                ('dam', models.ForeignKey(limit_choices_to={'sex': 'F'}, on_delete=django.db.models.deletion.CASCADE, related_name='dam_pairings', to='birds.animal')),
                ('sire', models.ForeignKey(limit_choices_to={'sex': 'M'}, on_delete=django.db.models.deletion.CASCADE, related_name='sire_pairings', to='birds.animal')),
            ],
        ),
    ]