# -*- mode: python -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright 2014-2026 C Daniel Meliza and contributors

from django.apps import AppConfig


class BirdsConfig(AppConfig):
    name = "birds"

    def ready(self):
        from birds import triggers  # noqa: F401
