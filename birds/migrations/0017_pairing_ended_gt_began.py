# Generated by Django 4.1.5 on 2024-02-21 01:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('birds', '0016_event_animal_date_idx'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='pairing',
            constraint=models.CheckConstraint(check=models.Q(('ended__isnull', True), ('ended__gt', models.F('began')), _connector='OR'), name='ended_gt_began'),
        ),
    ]