import pytest
from django.conf import settings


def pytest_collection_modifyitems(config, items):
    """Skip tests marked `postgres` unless the test database is postgres"""
    engine = settings.DATABASES["default"]["ENGINE"]
    if engine.endswith("postgresql"):
        return
    skip = pytest.mark.skip(reason="requires postgres (set BIRDS_TEST_DB=postgres)")
    for item in items:
        if "postgres" in item.keywords:
            item.add_marker(skip)
