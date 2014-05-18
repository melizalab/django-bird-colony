
## bird-colony

bird-colony is a Django application used to manage bird colonies (including breeding colonies)

The admin interface is the primary tool used to create and update bird records, but there is a growing collection of views that can be used to browse the database and perform common updates (like adding clutches).

bird-colony is licensed for you to use under the Gnu Public License, version 3. See COPYING for details

### Quick start

1. Install the package from source: `python setup.py install`. Worth putting in a virtualenv.

1. Add `birds` to your INSTALLED_APPS setting like this:

```python
INSTALLED_APPS = (
    ...
    'birds',
)
```

2. Include the birds URLconf in your project urls.py like this::

```python
url(r'^birds/', include(birds.urls')),
```

3. Run `python manage.py migrate` to create the birds models.

4. Start the development server and visit http://127.0.0.1:8000/admin/birds/
   to create items, vendors, manufacturers, etc. (you'll need the Admin app enabled).

5. Visit http://127.0.0.1:8000/birds/ to use views.
