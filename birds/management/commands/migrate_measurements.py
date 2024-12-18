# -*- coding: utf-8 -*-
# -*- mode: python -*-
import re

from django.core.management.base import BaseCommand, CommandError

from birds.models import Event, Measure, Measurement


class Command(BaseCommand):
    help = "Parses event descriptions for measurements and creates Measurements for them"

    def handle(self, *args, **options):
        measures = Measure.objects.all()
        for measure in measures:
            rx = re.compile(rf"{measure.name}.*?([0-9.]+)")
            candidates = Event.objects.filter(description__icontains=measure.name)
            for candidate in candidates:
                m = rx.search(candidate.description)
                if m:
                    value = float(m.group(1))
                    self.stdout.write(
                        self.style.SUCCESS(f"{candidate} -> {measure.name} = {value}")
                    )
            

