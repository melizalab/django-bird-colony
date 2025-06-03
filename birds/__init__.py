# -*- mode: python -*-
try:
    from importlib.metadata import version

    __version__ = version("django-bird-colony")
except Exception:
    # If package is not installed (e.g. during development)
    __version__ = "unknown"
api_version = "1.0"
