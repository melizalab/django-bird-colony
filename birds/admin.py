from django.contrib import admin
from birds.models import Species, Color, Location, Animal, Event, Status, Age, Parent


class ParentInline(admin.TabularInline):
    model = Parent
    fk_name = 'child'
    max_num = 2
    min_num = 2

class AnimalAdmin(admin.ModelAdmin):
    fields = ('species', 'sex', 'band_color', 'band_number', 'reserved_by')
    list_display = ('name', 'species', 'band', 'uuid', 'sex', 'reserved_by')
    list_filter = ('species', 'sex', 'band_color','parents', 'reserved_by')
    search_fields = ('band_number', 'uuid')
    inlines = (ParentInline,)


class EventAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    fields = ('animal', 'status', 'location', 'description', 'date', 'entered_by')
    list_display = ('animal', 'date', 'status', 'description')
    list_filter = ('animal', 'entered_by', 'status', 'location')
    search_fields = ('description',)


class StatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'count')


admin.site.register(Animal, AnimalAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Status, StatusAdmin)

for model in (Species, Color, Location, Age):
    admin.site.register(model)
