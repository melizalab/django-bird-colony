# -*- mode: python -*-
from django.contrib import admin

from birds import models


class ParentInline(admin.TabularInline):
    model = models.Parent
    fk_name = "child"
    max_num = 2
    min_num = 0
    autocomplete_fields = ("parent",)


class MeasurementInline(admin.TabularInline):
    model = models.Measurement
    extra = 1


class AnimalAdmin(admin.ModelAdmin):
    fields = (
        "species",
        "sex",
        "band_color",
        "band_number",
        "plumage",
        "reserved_by",
        "attributes",
    )
    list_display = ("name", "species", "band", "uuid", "sex", "plumage", "reserved_by")
    list_filter = ("species", "sex", "band_color", "plumage", "reserved_by")
    inlines = (ParentInline,)


class EventAdmin(admin.ModelAdmin):
    date_hierarchy = "date"
    fields = ("animal", "status", "location", "description", "date", "entered_by")
    autocomplete_fields = ("animal",)
    list_display = ("animal", "date", "status", "location", "description", "entered_by")
    list_filter = (
        "entered_by",
        "status",
        "status__adds",
        "status__removes",
        "location",
    )
    search_fields = ("description",)
    inlines = (MeasurementInline,)


class StatusAdmin(admin.ModelAdmin):
    list_display = ("name", "adds", "removes")


class SampleAdmin(admin.ModelAdmin):
    date_hierarchy = "date"
    fields = (
        "type",
        "source",
        "location",
        "attributes",
        "comments",
        "date",
        "collected_by",
    )
    list_display = ("type", "animal", "location", "date", "collected_by")
    list_filter = ("type", "location", "collected_by")
    search_fields = ("description",)


class PairingAdmin(admin.ModelAdmin):
    date_hierarchy = "began_on"
    fields = ("sire", "dam", "began_on", "purpose", "ended_on", "comment")
    autocomplete_fields = ("sire", "dam")
    list_display = ("sire", "dam", "began_on", "purpose", "ended_on", "comment")
    list_filter = (
        "began_on",
        "ended_on",
    )
    search_fields = (
        "purpose",
        "comment",
    )


class MeasurementAdmin(admin.ModelAdmin):
    fields = (
        "value",
        "type",
    )
    list_display = ("event__animal", "event__date", "value", "type")
    date_hierarchy = "event__date"
    list_filter = ("type",)


class LocationAdmin(admin.ModelAdmin):
    fields = ("name", "description", "room", "nest", "active")
    list_display = ("name", "room", "description", "nest", "active")
    list_filter = ("room", "nest", "active")


admin.site.register(models.Animal, AnimalAdmin)
admin.site.register(models.Event, EventAdmin)
admin.site.register(models.Status, StatusAdmin)
admin.site.register(models.Sample, SampleAdmin)
admin.site.register(models.Pairing, PairingAdmin)
admin.site.register(models.Measurement, MeasurementAdmin)
admin.site.register(models.Location, LocationAdmin)


for model in (
    models.Species,
    models.Color,
    models.Plumage,
    models.Age,
    models.Room,
    models.SampleType,
    models.SampleLocation,
    models.NestCheck,
    models.Measure,
):
    admin.site.register(model)
