# -*- mode: python -*-
import datetime

from rest_framework import serializers

from birds.models import Animal, Event, Location, Measure, Measurement, Status


class AgeSerializer(serializers.Field):
    """Serialize age into days"""

    def to_representation(self, value: datetime.timedelta):
        return value.days


class AnimalSerializer(serializers.ModelSerializer):
    species = serializers.StringRelatedField()
    band_color = serializers.StringRelatedField()
    plumage = serializers.StringRelatedField()
    reserved_by = serializers.StringRelatedField()
    sire = serializers.PrimaryKeyRelatedField(read_only=True)
    dam = serializers.PrimaryKeyRelatedField(read_only=True)
    alive = serializers.BooleanField(required=False)

    class Meta:
        model = Animal
        fields = (
            "name",
            "uuid",
            "species",
            "sex",
            "plumage",
            "band_color",
            "band_number",
            "sire",
            "dam",
            "alive",
            "reserved_by",
        )


class AnimalPedigreeSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    name = serializers.CharField()
    sire = serializers.StringRelatedField()
    dam = serializers.StringRelatedField()
    sex = serializers.CharField()
    plumage = serializers.StringRelatedField()
    alive = serializers.BooleanField()
    unexpectedly_died = serializers.BooleanField(source="has_unexpected_removal")
    age_days = serializers.IntegerField(source="age.days", default=None)
    n_eggs_infertile = serializers.IntegerField(
        source="children.unhatched.lost.count", default=0
    )
    n_eggs_hatched = serializers.IntegerField(
        source="children.hatched.count", default=0
    )
    n_kids_unexpectedly_died = serializers.IntegerField(
        source="children.hatched.lost.count", default=0
    )


class PedigreeRequestSerializer(serializers.Serializer):
    """Used to parse requests for pedigree"""

    restrict = serializers.BooleanField(default=True)


class AnimalDetailSerializer(AnimalSerializer):
    species = serializers.StringRelatedField()
    band_color = serializers.StringRelatedField()
    plumage = serializers.StringRelatedField()
    reserved_by = serializers.StringRelatedField()
    sire = serializers.PrimaryKeyRelatedField(read_only=True)
    dam = serializers.PrimaryKeyRelatedField(read_only=True)
    age_days = AgeSerializer(source="age", read_only=True)
    alive = serializers.BooleanField()
    last_location = serializers.StringRelatedField()

    class Meta:
        model = Animal
        fields = (
            "name",
            "uuid",
            "species",
            "sex",
            "plumage",
            "band_color",
            "band_number",
            "sire",
            "dam",
            "reserved_by",
            "age_days",
            "alive",
            "last_location",
            "attributes",
        )


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ("name", "count")


class MeasurementSerializer(serializers.ModelSerializer):
    event_id = serializers.PrimaryKeyRelatedField(
        source="event", queryset=Event.objects.all()
    )
    animal = serializers.PrimaryKeyRelatedField(source="event.animal", read_only=True)
    date = serializers.DateField(source="event.date", read_only=True)
    measure = serializers.SlugRelatedField(
        source="type", slug_field="name", queryset=Measure.objects.all()
    )
    units = serializers.CharField(source="type.unit_sym", read_only=True)

    class Meta:
        model = Measurement
        fields = ("event_id", "animal", "date", "measure", "value", "units")


class MeasurementInlineSerializer(serializers.ModelSerializer):
    measure = serializers.SlugRelatedField(
        source="type", slug_field="name", queryset=Measure.objects.all()
    )
    units = serializers.CharField(source="type.unit_sym", read_only=True)

    class Meta:
        model = Measurement
        fields = ("measure", "value", "units")


class EventSerializer(serializers.ModelSerializer):
    animal = serializers.PrimaryKeyRelatedField(queryset=Animal.objects.all())
    entered_by = serializers.StringRelatedField()
    location = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Location.objects.all(),
        required=False,
    )
    status = serializers.SlugRelatedField(
        slug_field="name", queryset=Status.objects.all()
    )
    measurements = MeasurementInlineSerializer(many=True)

    def create(self, validated_data):
        measurements = validated_data.pop("measurements")
        event = Event.objects.create(**validated_data)
        for measurement in measurements:
            _ = Measurement.objects.create(event=event, **measurement)
        return event

    def update(self, instance, validated_data):
        measurements = validated_data.pop("measurements")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        # clear existing measurements
        instance.measurements.all().delete()
        for measurement in measurements:
            _ = Measurement.objects.create(event=instance, **measurement)
        return instance

    class Meta:
        model = Event
        fields = (
            "id",
            "animal",
            "date",
            "status",
            "location",
            "description",
            "entered_by",
            "measurements",
        )
