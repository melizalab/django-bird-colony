bird-colony
-----------

|ProjectStatus|_ |Version|_ |BuildStatus|_ |License|_ |PythonVersions|_

.. |ProjectStatus| image:: https://www.repostatus.org/badges/latest/active.svg
.. _ProjectStatus: https://www.repostatus.org/#active

.. |Version| image:: https://img.shields.io/pypi/v/django-bird-colony.svg
.. _Version: https://pypi.python.org/pypi/django-bird-colony/

.. |BuildStatus| image:: https://github.com/melizalab/django-bird-colony/actions/workflows/test.yml/badge.svg
.. _BuildStatus: https://github.com/melizalab/django-bird-colony/actions/workflows/test.yml

.. |License| image:: https://img.shields.io/pypi/l/django-bird-colony.svg
.. _License: https://opensource.org/license/bsd-3-clause/

.. |PythonVersions| image:: https://img.shields.io/pypi/pyversions/django-bird-colony.svg
.. _PythonVersions: https://pypi.python.org/pypi/django-bird-colony/

bird-colony is a Django application the Meliza Lab uses to manage its zebra
finch colony and keep breeding records. You may find it useful, even if you work
with non-avian species.

Features:

* Animals have globally unique identifiers and can optionally have colored and numbered leg bands (one band per animal). This means they keep their identities even if you have to reband them.
* Record events over the lifespan of each animal, from egg to grave. Events can be linked to locations, so you can find where an animal is, or was on a certain date. Events can also be linked to measurements like weight so you can track these over time or use them to make breeding decisions.
* Track pairings, pedigrees, and breeding success statistics. You can export a complete pedigree for all living birds in the colony and compute relatedness using external software like the R `pedigree <https://www.rdocumentation.org/packages/pedigree/versions/1.4.2>`_ package.
* Useful forms for entering data, including periodic nest checks. Easy to track when eggs are laid and hatch and associate them with the correct parents.
* Associate biological samples with animals and track their physical location.

You’ll need to have a basic understanding of how to use
`Django <https://www.djangoproject.com/>`__. ``bird-colony`` is licensed
for you to use under the BSD License. See COPYING for details

Quick start
~~~~~~~~~~~

1. Requires Python 3.10+. Runs on Django 4.2 LTS and 5.1.

2. Install the package using pip: ``pip install django-bird-colony``.

3. Add ``birds`` and some dependencies to your INSTALLED_APPS setting
   like this:

.. code:: python

   INSTALLED_APPS = (
       ...
       'widget_tweaks',  # For form tweaking
       'rest_framework',
       'django_filters',
       'widget_tweaks',
       'fullurl',
       'birds',
   )

2. Include birds in ``urlpatterns`` in your project ``urls.py``. Some of
   the views link to the admin interface, so make sure that is included,
   too:

.. code:: python

       path("birds/", include("birds.urls")),
       path("admin/", admin.site.urls),

3. Run ``python manage.py migrate`` to create the database tables. If
   this is a new django install, run
   ``python migrate.py createsuperuser`` to create your admin user.

4. Run ``python manage.py loaddata bird_colony_starter_kit`` to create
   some useful initial records.

5. Start the development server (``python manage.py runserver``) and
   visit http://127.0.0.1:8000/admin/birds/ to set up your colony, as
   described in the next section.

6. Visit http://127.0.0.1:8000/birds/ to use views.

Make sure to consult the Django documentation on deployment if you are
at all concerned about security.

Initial setup
~~~~~~~~~~~~~

This is a work in progress. Before you start entering birds and events,
you need to set up some tables using the Django admin app.

Required steps:
^^^^^^^^^^^^^^^

1. Edit species records in the ``Species`` table. The
   ``bird_colony_starter_kit`` fixture will create a record for zebra
   finches. The ``code`` field is used to give animals their names, so
   if you have zebra finches and use ``zebf`` as your code, your birds
   will be named ``zebf_red_1`` and so forth.
2. Edit and add locations to the ``Locations`` table. You need to have
   at least one location created. The main use for this field is to
   allow you to find where a bird is by looking at the last event.
3. Edit and create new event types in the ``Status codes`` table. Common
   event types include ``hatched``, ``added``, ``moved``, ``died``,
   ``used for anatomy``, etc. For each status code, indicate whether it
   adds or removes a bird from the colony. When you create an event that
   removes a bird, it will appear as no longer alive. The ``hatched``
   event is special, because if you add a bird to the database using the
   ``Add new bird`` view using this code, the system will require you to
   enter the bird’s parents. (If you don’t know the bird’s parents, you
   can always create it manually in the admin interface)

Optional steps:
^^^^^^^^^^^^^^^

1. If your bands are colored, add your colors to the ``Colors`` table.
   This will affect the short name for your animals.
2. If you’re going to be adding samples to the databse, add or edit
   ``Sample locations`` and ``Sample types`` in the admin interface.
3. Add additional users to the database. This is particularly useful if
   you want to allow specific users to reserve animals.
4. If you want to change some of the boilerplate text on the entry
   forms, you’ll need to install the app from source. The templates are
   found under ``birds/templates/birds`` in the source directory.

Development
~~~~~~~~~~~

Recommend using `uv <https://docs.astral.sh/uv/>`__ for development.

Run ``uv sync`` to create a virtual environment and install
dependencies. ``uv sync --no-dev --frozen`` for deployment.

Testing: ``uv run pytest``. Requires a test database, will use settings
from ``inventory/test/settings.py``.

Changelog
~~~~~~~~~

In the 0.4.0 release, the primary key for animal records became the
animal’s uuid. To migrate from previous version, data must be exported
as JSON under the 0.3.999 release and then imported under 0.4.0
