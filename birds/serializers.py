# -*- mode: python -*-

from rest_framework import serializers

from birds.models import Animal, Event, Location, Measure, Measurement, Pairing, Status


class AnimalSerializer(serializers.ModelSerializer):
    species = serializers.StringRelatedField()
    band_color = serializers.StringRelatedField()
    plumage = serializers.StringRelatedField()
    reserved_by = serializers.StringRelatedField()
    sire = serializers.PrimaryKeyRelatedField(read_only=True)
    dam = serializers.PrimaryKeyRelatedField(read_only=True)
    alive = serializers.BooleanField(source="life_history.is_alive")

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


class AnimalDetailSerializer(AnimalSerializer):
    species = serializers.StringRelatedField()
    band_color = serializers.StringRelatedField()
    plumage = serializers.StringRelatedField()
    reserved_by = serializers.StringRelatedField()
    sire = serializers.PrimaryKeyRelatedField(read_only=True)
    dam = serializers.PrimaryKeyRelatedField(read_only=True)
    age_days = serializers.SerializerMethodField()
    alive = serializers.BooleanField(source="life_history.is_alive")
    last_location = serializers.StringRelatedField(source="life_history.last_location")
    inbreeding = serializers.FloatField(source="life_history.inbreeding_coefficient")

    def get_age_days(self, obj):
        try:
            return obj.life_history.age().days
        except (Animal.life_history.RelatedObjectDoesNotExist, AttributeError):
            pass

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
            "inbreeding",
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
    # animal = serializers.PrimaryKeyRelatedField(queryset=Animal.objects.all())
    animal = serializers.UUIDField()
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

    def validate_animal(self, value):
        # Validate that the animal exists
        try:
            return Animal.objects.get(uuid=value)
        except Animal.DoesNotExist:
            raise serializers.ValidationError("Animal does not exist") from None

    def to_representation(self, instance):
        # For serialization (GET requests), return the animal UUID. This is to
        # avoid a really expensive lookup when using PrimaryKeyRelatedField
        data = super().to_representation(instance)
        data["animal"] = str(instance.animal.uuid)
        return data

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


class PairingSerializer(serializers.ModelSerializer):
    sire = serializers.StringRelatedField(source="sire.uuid")
    dam = serializers.StringRelatedField(source="dam.uuid")

    class Meta:
        model = Pairing
        fields = (
            "id",
            "sire",
            "dam",
            "began_on",
            "ended_on",
        )


class BreedingOutcomesSerializer(serializers.Serializer):
    n_eggs_infertile = serializers.IntegerField(
        source="unhatched.lost.count", default=0
    )
    n_eggs_hatched = serializers.IntegerField(source="hatched.count", default=0)
    n_kids_unexpectedly_died = serializers.IntegerField(
        source="hatched.lost.count", default=0
    )


class AnimalPedigreeSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    name = serializers.CharField()
    sire = serializers.StringRelatedField()
    dam = serializers.StringRelatedField()
    sex = serializers.CharField()
    plumage = serializers.StringRelatedField()
    born_on = serializers.DateField(source="life_history.born_on")
    alive = serializers.BooleanField(source="life_history.is_alive")
    unexpectedly_died = serializers.BooleanField(
        source="life_history.has_unexpected_removal"
    )
    age_days = serializers.IntegerField(source="life_history.age.days", default=None)
    weight = serializers.SerializerMethodField()
    parent_lifespans = serializers.SerializerMethodField()
    grandparent_lifespans = serializers.SerializerMethodField()
    latest_pairing = PairingSerializer(source="pairings.first")
    # breeding_outcomes = BreedingOutcomesSerializer(source="children")
    n_eggs = serializers.IntegerField(default=0)
    n_eggs_hatched = serializers.IntegerField(source="n_hatched", default=0)
    n_kids_unexpectedly_died = serializers.IntegerField(
        source="children.hatched.lost.count", default=0
    )
    n_kids_alive = serializers.IntegerField(source="n_alive", default=0)
    inbreeding = serializers.FloatField(source="life_history.inbreeding_coefficient")
    reserved_by = serializers.StringRelatedField()

    def get_alive(self, obj):
        return obj.life_history.is_alive()

    def get_unexpectedly_died(self, obj):
        # Check if dead with unexpected removal
        stage = obj.life_history.life_stage()
        if stage in (
            obj.life_history.LifeStage.DEAD,
            obj.life_history.LifeStage.FAILED_EGG,
        ):
            outcome = obj.life_history.removal_outcome()
            return outcome == obj.life_history.RemovalOutcome.UNEXPECTED
        return False

    def get_age_days(self, obj):
        age = obj.life_history.age()
        return age.days if age is not None else None

    def get_weight(self, obj):
        try:
            return obj.measurements().get(type__name="weight").value
        except Measurement.DoesNotExist:
            return None

    def get_parent_lifespans(self, obj):
        lifespans = []
        for parent in obj.parents.all():
            if parent.history.died_unexpectedly():
                age = parent.history.age()
                if age is not None:
                    lifespans.append(age.days)
        return lifespans

    def get_grandparent_lifespans(self, obj):
        lifespans = []
        for grandparent in Animal.objects.ancestors_of(obj, 2):
            if grandparent.history.died_unexpectedly():
                age = grandparent.history.age()
                if age is not None:
                    lifespans.append(age.days)
        return lifespans
