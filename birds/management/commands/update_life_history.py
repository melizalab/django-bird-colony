# management/commands/update_life_history.py

import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from birds import pedigree
from birds.models import Animal, AnimalLifeHistory


class Command(BaseCommand):
    help = "Update cached life history"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--update",
            type=str,
            help="Update life history for a specific animal by UUID",
        )
        group.add_argument(
            "--clear",
            type=str,
            help="Remove life history record for a specific animal by UUID (for testing)",
        )
        group.add_argument(
            "--all", action="store_true", help="update all life history records"
        )

    def handle(self, *args, **options):
        update_uuid = options.get("update")
        clear_uuid = options.get("clear")

        if update_uuid:
            # Update single animal
            try:
                animal = Animal.objects.get(uuid=update_uuid)
                self.update_single_animal(animal)
            except Animal.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Animal with UUID {update_uuid} not found")
                )
                return
        elif clear_uuid:
            # Remove single animal's life history
            try:
                animal = Animal.objects.get(uuid=clear_uuid)
                self.remove_single_animal_history(animal)
            except Animal.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Animal with UUID {clear_uuid} not found")
                )
                return
        elif options.get("all"):
            # Update all animals using bulk operations
            self.populate_all_animals()
        else:
            self.stdout.write(
                self.style.ERROR("--update, --clear, or --all option is required")
            )

    def update_single_animal(self, animal):
        """Update life history for a single animal"""
        life_history, created_at = AnimalLifeHistory.objects.get_or_create(
            animal=animal
        )
        life_history.update_from_events()
        life_history.save()

        if created_at:
            self.stdout.write(f"Created life history for {animal}")
        else:
            self.stdout.write(f"Updated life history for {animal}")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully updated life history for {animal}")
        )

    def remove_single_animal_history(self, animal):
        """Remove life history record for a single animal (for testing)"""
        try:
            life_history = animal.life_history
            life_history.delete()
            self.stdout.write(self.style.SUCCESS(f"Removed life history for {animal}"))
        except AnimalLifeHistory.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(f"No life history record found for {animal}")
            )

    def populate_all_animals(self):
        """Bulk create/update life history records for all animals"""
        self.stdout.write("Clearing existing life history records...")
        AnimalLifeHistory.objects.all().delete()

        # Get all animals with their computed life history in one query
        self.stdout.write("Getting all animals with computed life history data...")
        animals_with_data = Animal.objects.with_dates().select_related("life_history")
        total_count = animals_with_data.count()

        self.stdout.write(f"Processing life history for {total_count} animals...")

        created_count = 0
        batch_size = 1000

        # Process in batches to manage memory
        for offset in range(0, total_count, batch_size):
            batch = animals_with_data[offset : offset + batch_size]

            with transaction.atomic():
                for animal in batch:
                    # Create new life history record
                    _life_history = AnimalLifeHistory.objects.create(
                        animal=animal,
                        first_event_on=animal.first_event_on,
                        laid_on=animal.laid_on,
                        born_on=animal.born_on,
                        acquired_on=animal.acquired_on,
                        died_on=animal.died_on,
                        has_unexpected_removal=animal.has_unexpected_removal,
                        last_location=animal.last_location(datetime.date.today()),
                    )
                    created_count += 1

            # Progress update
            processed = min(offset + batch_size, total_count)
            self.stdout.write(f"Processed {processed}/{total_count} animals...")
        self.stdout.write(
            self.style.SUCCESS(f"Updated life history for {total_count} animals")
        )

        self.stdout.write("Recalculating inbreeding coefficients for all animals...")
        pedigree_animals = Animal.objects.for_pedigree(all_animals=True)
        ped = pedigree.Pedigree.from_animals(
            [(animal.uuid, animal.sire, animal.dam) for animal in pedigree_animals]
        )
        inbreeding_coeffs = ped.get_inbreeding()
        # Update life history records for the target animals
        updated_count = 0
        for animal in pedigree_animals:
            try:
                animal_index = ped.index(animal.uuid)
                coefficient = float(inbreeding_coeffs[animal_index])
            except (KeyError, IndexError):
                coefficient = 0.0

            life_history = animal.history
            life_history.inbreeding_coefficient = coefficient
            life_history.save(update_fields=["inbreeding_coefficient"])
            updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated inbreeding coefficients for {updated_count} animals"
            )
        )
