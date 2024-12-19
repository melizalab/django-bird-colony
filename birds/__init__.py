# -*- coding: utf-8 -*-
# -*- mode: python -*-
try:
    from importlib.metadata import version
    __version__ = version("django-bird-colony")
except ImportError:
    # For Python < 3.8
    from importlib_metadata import version
    __version__ = version("django-bird-colony")
except Exception:
    # If package is not installed (e.g. during development)
    __version__ = "unknown"
api_version = "1.0"


