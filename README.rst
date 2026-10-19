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
* Record events over the lifespan of each animal, from egg to grave. Events can be linked to locations, so you can find where an animal is or was on a certain date. Events can also be linked to measurements like weight so you can track these over time or use them to make breeding decisions.
* Track pairings, pedigrees, and breeding success statistics. You can export a complete pedigree for all living birds in the colony and compute relatedness using external software like the R `pedigree <https://www.rdocumentation.org/packages/pedigree/versions/1.4.2>`_ package.
* Useful forms for entering data, including periodic nest checks. Easy to track when eggs are laid and hatch and associate them with the correct parents.
* Associate biological samples with animals and track their physical location.

You’ll need to have a basic understanding of how to use
`Django <https://www.djangoproject.com/>`__. ``bird-colony`` is licensed
for you to use under the BSD License. See COPYING for details

Quick start
~~~~~~~~~~~

1. Requires Python 3.11+. Runs on Django 5.2 LTS and 6.1.

2. Install the package using pip: ``pip install django-bird-colony``.

3. Add ``birds`` and some dependencies to your INSTALLED_APPS setting
   like this:

.. code:: python

   INSTALLED_APPS = (
       ...
       'widget_tweaks',  # For form tweaking
       'rest_framework',
       'django_filters',
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
   ``python manage.py createsuperuser`` to create your admin user.

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
   allow you to find where a bird is by looking at the last event. Mark the
   locations where pairs are kept as nests, so they can be chosen when you
   create a pairing. Locations can also be grouped into rooms, and inactive
   locations are not offered in forms.
3. Edit and create new event types in the ``Status codes`` table. The
   application looks up some event types by name, so the table needs to
   include ``hatched``, ``laid``, ``banded``, ``died``, ``moved``, ``note``,
   ``reservation``, and ``bad egg``. The ``bird_colony_starter_kit`` fixture
   creates these, plus ``transferred in`` and ``transferred out``. For each
   status code, indicate whether it adds a bird to the colony (an egg being
   laid, a birth, or a transfer in) or removes one (an expected or unexpected
   death or removal). Unexpected removals are important to tabulate when
   looking at family history and breeding success. When you create an event
   that removes a bird, it will appear as no longer alive. The ``hatched``
   event is special, because if you add a bird to the database using the
   ``Add new bird`` view using this code, the system will require you to enter
   the bird’s parents. (If you don’t know the bird’s parents, you can always
   create it manually in the admin interface)

Optional steps:
^^^^^^^^^^^^^^^

1. If your bands are colored, add your colors to the ``Band colors`` table.
   This will affect the short name for your animals. Only colors with the kind
   ``available`` are offered when you add an animal or band a bird. Mark colors
   you no longer use as ``historical``, and colors from other labs as
   ``external``, so that existing animals keep their bands without cluttering
   the forms.
2. If you’re going to be adding samples to the databse, add or edit
   ``Sample locations`` and ``Sample types`` in the admin interface.
3. Add additional users to the database. Every event records who entered
   it, so add a user for each person who will be entering data.
4. Add tags to the ``Tags`` model. Each bird can be tagged with zero or more of
   these. Tags are used for reservations and for searching which birds were used
   for different experiments.
5. If you want to change some of the boilerplate text on the entry
   forms, you’ll need to install the app from source. The templates are
   found under ``birds/templates/birds`` in the source directory.

Development
~~~~~~~~~~~

Recommend using `uv <https://docs.astral.sh/uv/>`__ for development.

Run ``uv sync`` to create a virtual environment and install
dependencies. ``uv sync --no-dev --frozen`` for deployment.

Testing: ``uv run pytest``. Tests use an in-memory sqlite database by default;
set ``BIRDS_TEST_DB=postgres`` (and install the ``postgres`` dependency group)
to use a postgres server configured with ``POSTGRES_*`` environment variables,
as on CI.

Changelog
~~~~~~~~~

See `CHANGELOG.rst <https://github.com/melizalab/django-bird-colony/blob/master/CHANGELOG.rst>`_.
