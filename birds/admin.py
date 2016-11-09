from django.contrib import admin
from birds.models import Species, Color, Location, Animal, Event, Status, Age, DataCollection, DataType, Recording, Parent

# Register your models here.

class ParentInline(admin.TabularInline):
    model = Parent
    fk_name = 'child'
    max_num = 2
    min_num = 2

class AnimalAdmin(admin.ModelAdmin):
    fields = ('species', 'sex', 'band_color', 'band_number', 'reserved_by')
    list_display = ('name', 'species', 'band', 'uuid', 'sex', 'reserved_by')
    list_filter = ('species', 'sex', 'band_color','parents')
    search_fields = ('band', 'uuid')
    inlines = (ParentInline,)


class EventAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    fields = ('animal', 'status', 'location', 'description', 'date', 'entered_by')
    list_display = ('animal', 'date', 'status', 'description')
    list_filter = ('animal', 'entered_by', 'status', 'location')
    search_fields = ('animal', 'entered_by', 'description')


class StatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'count')


class RecordingAdmin(admin.ModelAdmin):
    date_hierarchy = 'timestamp'
    list_display = ('animal', 'collection', 'identifier', 'datatype', 'timestamp')
    list_filter = ('animal', 'collection', 'datatype')
    search_fields = ('animal', 'identifier')


admin.site.register(Animal, AnimalAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Status, StatusAdmin)
admin.site.register(Recording, RecordingAdmin)

for model in (Species, Color, Location, Age, DataCollection, DataType):
    admin.site.register(model)
