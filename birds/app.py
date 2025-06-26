# -*- mode: python -*-

from django.apps import AppConfig


class BirdsConfig(AppConfig):
    name = "birds"

    def ready(self):
        from birds import triggers  # noqa: F401
