=========
Changelog
=========

Releases are listed newest first. Dates come from the release tag, or from the
version-bump commit for releases that were never tagged (most releases before
0.13). Numbers like #57 refer to issues on GitHub.

0.15.0 (unreleased)
-------------------

Breaking changes
~~~~~~~~~~~~~~~~

* Dropped support for Python 3.10 and Django 4.2. Requires Python 3.11+ and
  Django 5.2+. Django 6.1 is now supported and tested.
* Requires Django REST framework 3.18+ (earlier releases do not import under
  Django 6.1). Upper limits were added for django (<7), djangorestframework
  (<4), django-filter (<27), and djangorestframework-link-header-pagination
  (<0.2).

Added
~~~~~

* Band colors have a ``kind``: ``available``, ``historical``, or ``external``.
  Only available colors are offered when adding an animal or banding a bird.
  **After migrating, every existing color is marked available**, so mark colors
  you no longer use as historical or external in the admin.
* The admin lists and filters band colors by kind, and animals can be filtered
  by the date they were created.

Changed
~~~~~~~

* ``django.contrib.postgres`` is no longer imported, so psycopg is only needed
  if you use postgres. The ``DISTINCT ON`` and ``ArrayAgg`` queries behind
  ``latest_by_animal`` and ``pedigree_subgraph_keys`` now work on any database,
  and ``oldest_living_progeny_age`` no longer uses database date arithmetic.
  Behavior on postgres is unchanged.
* Migrations 0005 and 0006 use ``models.JSONField`` instead of the postgres
  field, and migrations 0017, 0018, and 0024 use ``condition=`` instead of
  ``check=`` for constraints, which Django 6 requires.
* Migration 0039 records ``through_fields`` on ``Animal.parents``. It changes
  nothing in the database, but without it ``makemigrations`` reports a pending
  change.
* The test suite runs on in-memory sqlite by default. Set
  ``BIRDS_TEST_DB=postgres`` to use postgres, as CI does.

Fixed
~~~~~

* Birds that arrive or hatch after the server starts are now offered as sire
  and dam in the new pairing and new animal forms. The choices were calculated
  once, when the server started, so affected birds only appeared after a
  restart (#97).

0.14.1 (2026-02-18)
-------------------

* The tag form shows the actual current date.
* CI tests run on postgres 17 and Python 3.14.

0.14.0 (2025-10-13)
-------------------

Added
~~~~~

* Tags: animals can carry tags, with views and forms for editing them and an
  "untagged" row in the tag list.
* A kinship view (#71). ``update_life_history`` can now update all animals.
* Totals on the location lists (#63) and the room on the active pairing list.
* Autocomplete in some admin views.

Changed
~~~~~~~

* The ``created`` fields on animals, events, measurements, and pairings were
  renamed ``created_at``. Scripts that read ``created`` need to be updated.
* The ``reserved_by`` field on animals was removed (#64).

Fixed
~~~~~

* A duplicated line in the README setup instructions (#65).

0.13.7 (2025-07-02)
-------------------

* The pedigree update command was merged into ``update_life_history``
  (``update_pedigree`` was removed). Small fixes to forms and pedigree output.

0.13.6 (2025-06-27)
-------------------

* Only active locations are listed in forms.

0.13.5 (2025-06-27)
-------------------

* Fixed an error in ``tabulate_pairs`` that affected the breeding check.

0.13.4 (2025-06-27)
-------------------

* Added the missing migration for location names (see 0.13.3).

0.13.3 (2025-06-27)
-------------------

* Locations can share a name if they are in different rooms.
* The location admin is more useful.

0.13.2 (2025-06-26)
-------------------

* Lost eggs are now recorded with a status named "bad egg" (infertile egg
  discarded) instead of "lost", and the starter kit was updated. **Existing
  databases need a status with that name** for the breeding check to record
  lost eggs.

0.13.1 (2025-06-26)
-------------------

* Relaxed the numpy requirement from 2.0+ to 1.26+.

0.13.0 (2025-06-26)
-------------------

Added
~~~~~

* Cached life history for each animal (laid, born, acquired, and died dates, plus
  last location and inbreeding coefficient). It is kept up to date when events
  change, and ``manage.py update_life_history`` refreshes it. Views and filters
  use the cache to speed up queries (#59).
* Inbreeding coefficients and relatedness (kinship) calculations, shown in the
  pairing views and in the pedigree API, which also reports breeding outcomes
  and the last pairing. The pedigree can be fetched all at once for R. Adds a
  dependency on numpy.
* Rooms: a ``Room`` model, and locations have a room and an active flag (#58).
* Lost progeny counts and family history in the animal view.

Changed
~~~~~~~

* Status ``adds`` and ``removes`` changed from booleans to typed choices, and
  laying an egg is now a type of addition (#57, #62). Existing data is converted
  by the migrations.
* Added constraints and indices on statuses and parents.
* Tested on Django 5.2.

0.12.1 (2024-12-18)
-------------------

* Restored pagination (#54).
* ``manage.py migrate_measurements`` creates measurements from measurement
  values written in event descriptions.

0.12.0 (2024-12-17)
-------------------

* Measurements: measures and measurement values attached to events, with list
  views, the most recent values on the animal page, an inline in the event
  admin, and add/edit/remove in the event entry form.
* The event entry form can edit existing events.
* A form to add an egg to a pairing (#45) and a pairing event view (#37).
* The API can create and update events (#53).
* Releases are built and published to PyPI by GitHub Actions.

0.11.8 (2024-12-08)
-------------------

* Inactive pairs can be used in the nest check (#46), and the active pair list
  is ordered (#51).
* Supports Django 5. Requires Python 3.10+ and adds django-widget-tweaks as a
  dependency.
* Development moved to uv, pytest, and a GitHub Actions test matrix. The README
  is now reStructuredText.

0.11.7 (2024-08-29)
-------------------

* Breeding check form errors are printed to the console.

0.11.6 (2024-08-17)
-------------------

* Removed the old nest check code, which no longer worked with the colony's
  current setup. The breeding check form validates parent fields.

0.11.5 (2024-08-13)
-------------------

* Fixed pagination on filtered views (#48).

0.11.4 (2024-06-28)
-------------------

* Pagination links include query parameters (#47).

0.11.3 (2024-06-16)
-------------------

* Closed pairings are omitted from the breeding check form (#42).

0.11.2 (2024-06-15)
-------------------

* Fixed an incorrect version specification in ``setup.cfg``.

0.11.1 (2024-06-15)
-------------------

* Dam and sire choices are sorted by color and number (#41).
* Fixed an incorrectly named field in the close pairing form (#40).
* Adds django-fullurl as a dependency.

0.11.0 (2024-06-14)
-------------------

Added
~~~~~

* A pairing-based breeding report and breeding check form, with egg creation on
  pairings.
* Location views, a location description field, user views (#39), bird counts
  in the summary view (#30), and the day of the week in nest reports (#22).
* A test suite.

Changed
~~~~~~~

* Performance work on views: reworked age calculations, fewer queries with
  prefetching, optimized API queries, and new indexes on events.
* Class-based views were replaced with function-based views, and filters moved
  to their own module. Form URLs that were only reachable from an animal were
  removed from the top level.
* Pairing dates are checked by a database constraint and pairing sexes are
  validated. The ``began`` and ``ended`` fields on pairings were renamed
  ``began_on`` and ``ended_on``.
* Animal sex is an enum.

Fixed
~~~~~

* Living children count in the genealogy (#33), ``tabulate_locations`` (#34),
  progeny statistics, child sorting, and the event summary near the end of the
  month.

0.10.12 (2024-01-23)
--------------------

* Added a related lookup to the event manager.

0.10.9 - 0.10.11 (2023-06-14)
-----------------------------

* Packaging: dropped ``requirements.txt`` in favor of ``install_requires``,
  switched the declared license to BSD, and added package data.
* Fixed an error when a bird has no events with a location.

0.10.8 (2023-01-24)
-------------------

* Fixes for Django 4.0. Packaging moved from ``setup.py`` to ``setup.cfg``.

0.10.7 (2022-08-02)
-------------------

* A form to create reservations, and a way to clear them.
* The pedigree uses names instead of uuids.
* A uuid field in the search form.

0.10.6 (2022-07-05)
-------------------

* The event list shows age, who entered the event, and an edit link.

0.10.5 (2022-04-05)
-------------------

* Added an ancestors view, combined with descendents as the genealogy view.

0.10.4 (2022-04-04)
-------------------

* Added a descendents view.

0.10.3 (2022-04-04)
-------------------

* A form to update an animal's sex (#27).

0.10.2 (2022-04-03)
-------------------

* The pairing list shows location, and filtering was fixed.

0.10.1 (2022-04-02)
-------------------

* Fixed a bug in the new pairing form.

0.10.0 (2022-04-02)
-------------------

* Forms to create and end pairings, which create move events.
* The animal view lists pairings and the pairing view lists events.
* The oldest living progeny is shown in the pairing list (#26), and the total
  children count was fixed (#24).

0.9.3 (2022-03-30)
------------------

* Pairings are stored in the database, with general views for them.

0.9.2 (2021-12-10)
------------------

* Fixes for Django 3.2.

0.9.1 (2021-08-18)
------------------

* Added a children endpoint to the API.

0.9.0 (2021-04-06)
------------------

* Updated for Django 3.0. Removed Python 2 support; requires Python 3.6+, with
  djangorestframework 3.12.4 and django-filter 2.4.0.

0.8.2 (2020-01-27)
------------------

* The latest-event manager retrieves the most recently created event (#21).

0.8.1 (2020-01-20)
------------------

* Nest check forms with a confirmation page that creates new animals and
  events, a nest check log, and a comment field. Eggs can be removed in the
  nest check (#18).
* Birds with only removal events are dead (#17), and sort order is consistent
  across forms (#19).

0.8.0 (2020-01-13)
------------------

* Eggs are supported throughout: species have an incubation period and eggs get
  an expected hatch date.
* A location summary report and a nest report.
* Animals can be classified into age groups as of a given date; the age group
  maximum days field was removed.
* Locations have a nest flag. A view lists animals by location.
* An edit link in the animal event list (#15).

0.7.8 (2019-07-29)
------------------

* A link to add a clutch from the animal view, and the animal view shows only
  the 10 most recent events.

0.7.7 (2019-07-19)
------------------

* Added an info endpoint to the API.

0.7.6 (2019-07-03)
------------------

* Plumage: a ``Plumage`` model on animals, with views, forms, and filters.

0.7.5 (2019-06-15)
------------------

* Sex is included in the pedigree. Added R code for processing the pedigree.

0.7.4 (2019-06-12)
------------------

* A search form on the main page. Sex can be set at banding (#13).
* The pedigree has a simplified serializer and can be restricted to living
  leaves and stems (the default).

0.7.3 (2019-02-27)
------------------

* Search forms for animals, events, and samples.

0.7.2 (2019-02-05)
------------------

* Pagination keeps query parameters (#12).
* Forms only offer active users.
* The date on a sample can be blank.

0.7.1 (2019-01-29)
------------------

* Fixed a URL and added a missing template.

0.7.0 (2019-01-25)
------------------

* Samples: sample types, sample locations, and samples (which can derive from
  other samples), with views.
* A form to assign a band to an existing bird, and sex on the new bird form.
  Bands must be unique.
* Animals and samples have an ``attributes`` JSON field.
* The status ``category`` field was removed. New starter kit fixture.

0.6.0 (2019-01-19)
------------------

* Statuses are marked with ``adds`` and ``removes`` flags instead of a count,
  and whether an animal is alive is calculated differently (#9, #10).
* Forms only list living birds (#11), and ``last_location`` returns the last
  non-null location.
* Updated for Django 2.x. Started a by-location view.

0.5.7 (2018-03-23)
------------------

* The admin allows birds to have no parents (#8).

0.5.6 (2017-10-27)
------------------

* Fixed a field name error in ``/api/animals``.

0.5.5 (2017-08-08)
------------------

* Removed a broken migration.

0.5.3 - 0.5.4 (2017-07-28)
--------------------------

* The API returns sire and dam instead of a list of parents, and age at death.
* Faster alive calculation, and a fix to the living filter in API queries.

0.5.2 (2017-06-29)
------------------

* Added API filters for parent and child.

0.5.1 (2017-06-23)
------------------

* Removed the unused ``DataCollection`` and ``DataType`` models.

0.5.0 (2017-06-23)
------------------

* A form for entering events (#6).
* The API was cleaned up, gained filtering (#3), and is documented.
* URLs and templates were reorganized, and the event list pagination was fixed.
* The last location of an animal is shown.
* Removed the ``Recording`` model. Migrations were squashed into a new initial
  migration.

0.4.1 (2017-06-21)
------------------

* Fixed search for events and animals.

0.4.0 (2016-11-13)
------------------

* The primary key for animal records became the animal's uuid. To migrate from
  a previous version, data must be exported as JSON under the 0.3.999 release
  and then imported under 0.4.0.
