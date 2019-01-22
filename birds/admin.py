# -*- coding: utf-8 -*-
# -*- mode: python -*-
from django.contrib import admin
from birds import models


class ParentInline(admin.TabularInline):
    model = models.Parent
    fk_name = 'child'
    max_num = 2
    min_num = 0


class AnimalAdmin(admin.ModelAdmin):
    fields = ('species', 'sex', 'band_color', 'band_number', 'reserved_by', 'attributes')
    list_display = ('name', 'species', 'band', 'uuid', 'sex', 'reserved_by')
    list_filter = ('species', 'sex', 'band_color', 'parents', 'reserved_by')
    search_fields = ('band_number', 'uuid', 'attributes__icontains')
    inlines = (ParentInline,)


class EventAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    fields = ('animal', 'status', 'location', 'description', 'date', 'entered_by')
    list_display = ('animal', 'date', 'status', 'description')
    list_filter = ('animal', 'entered_by', 'status', 'location')
    search_fields = ('description',)


class StatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'adds', 'removes')


class SampleAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    fields = ('type', 'animal', 'source', 'location', 'attributes', 'comments', 'date', 'collected_by')
    list_display = ('type', 'animal', 'location', 'date', 'collected_by')
    list_filter = ('type', 'animal', 'source', 'location', 'collected_by')
    search_fields = ('description',)


admin.site.register(models.Animal, AnimalAdmin)
admin.site.register(models.Event, EventAdmin)
admin.site.register(models.Status, StatusAdmin)
admin.site.register(models.Sample, SampleAdmin)

for model in (models.Species, models.Color, models.Location, models.Age, models.SampleType, models.SampleLocation):
    admin.site.register(model)
