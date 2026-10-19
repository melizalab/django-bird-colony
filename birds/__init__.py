# -*- mode: python -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright 2014-2026 C Daniel Meliza and contributors

try:
    from importlib.metadata import version

    __version__ = version("django-bird-colony")
except Exception:
    # If package is not installed (e.g. during development)
    __version__ = "unknown"
api_version = "1.0"
