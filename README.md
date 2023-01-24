
## bird-colony

bird-colony is a Django application used to manage bird colonies (including breeding colonies).
You may find that it can also be used for non-avian species. There's also support for storing information about samples associated with animals in the colony, like genomic DNA or song recordings.

There is a growing collection of views that can be used to browse the database and perform common updates (like adding clutches). There is also a JSON API that supports a variety of search queries.

bird-colony is licensed for you to use under the BSD License. See COPYING for details

### Quick start

You'll need to have a basic understanding of how to use [Django](https://www.djangoproject.com/). Requires Python 3.8+ and Django 4.0+.

1. Install the package using pip: `pip install django-bird-colony`.

1. Add `birds` and some dependencies to your INSTALLED_APPS setting like this:

```python
INSTALLED_APPS = (
    ...
    'rest_framework',
    'django_filters',
    'birds',
)
```

2. Include the birds URLconf in your project urls.py like this::

```python
url(r'^birds/', include('birds.urls'))
```

3. Run `python manage.py migrate` to create the database tables. If this is a new django install, run `python migrate.py createsuperuser` to create your admin user.

4. Run `python manage.py loaddata bird_colony_starter_kit` to create some useful initial records.

5. Start the development server (`python manage.py runserver`) and visit http://127.0.0.1:8000/admin/birds/
   to set up your colony, as described in the next section.

6. Visit http://127.0.0.1:8000/birds/ to use views.

Make sure to consult the Django documentation on deployment if you are at all concerned about security.

### Initial setup

This is a work in progress. Before you start entering birds and events, you need
to set up some tables using the Django admin app.

#### Required steps:

1. Edit species records in the `Species` table. The `bird_colony_starter_kit` fixture will create a record for zebra finches. The `code` field is used to give animals their names, so if you have zebra finches and use `zebf` as your code, your birds will be named `zebf_red_1` and so forth.
2. Edit and add locations to the `Locations` table. You need to have at least one location created. The main use for this field is to allow you to find where a bird is by looking at the last event.
3. Edit and create new event types in the `Status codes` table. Common event types include `hatched`, `added`, `moved`, `died`, `used for anatomy`, etc. For each status code, indicate whether it adds or removes a bird from the colony. When you create an event that removes a bird, it will appear as no longer alive. The `hatched` event is special, because if you add a bird to the database using the `Add new bird` view using this code, the system will require you to enter the bird's parents. (If you don't know the bird's parents, you can always create it manually in the admin interface)

#### Optional steps:

1. If your bands are colored, add your colors to the `Colors` table. This will affect the short name for your animals.
2. If you're going to be adding samples to the databse, add or edit `Sample locations` and `Sample types` in the admin interface.
2. Add additional users to the database. This is particularly useful if you want to allow specific users to reserve animals.
3. If you want to change some of the boilerplate text on the entry forms, you'll need to install the app from source. The templates are found under `birds/templates/birds` in the source directory.

### Changelog

In the 0.4.0 release, the primary key for animal records became the animal's uuid. To migrate from previous version, data must be exported as JSON under the 0.3.999 release and then imported under 0.4.0
