# -*- coding: utf-8 -*-
# -*- mode: python -*-
import re

from django.core.management.base import BaseCommand
from django.db import IntegrityError

from birds.models import Event, Measure, Measurement


class Command(BaseCommand):
    help = (
        "Parses event descriptions for measurements and creates Measurements for them"
    )

    def handle(self, *args, **options):
        measures = Measure.objects.all()
        for measure in measures:
            rx = re.compile(rf"{measure.name}.*?([0-9.]+)", re.IGNORECASE)
            candidates = Event.objects.filter(description__icontains=measure.name)
            for candidate in candidates:
                m = rx.search(candidate.description)
                try:
                    value = float(m.group(1))
                    measurement = Measurement.objects.create(
                        event=candidate, type=measure, value=value
                    )
                    self.stdout.write(self.style.SUCCESS(str(measurement)))
                except (AttributeError, ValueError):
                    self.stdout.write(
                        self.style.NOTICE(
                            f"{candidate} -> no match ({candidate.description})"
                        )
                    )
                except IntegrityError:
                    self.stdout.write(
                        self.style.NOTICE(f"{candidate} -> already migrated")
                    )
