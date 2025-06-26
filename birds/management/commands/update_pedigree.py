# -*- mode: python -*-

from django.core.management.base import BaseCommand

from birds import pedigree
from birds.models import Animal


class Command(BaseCommand):
    help = "Update inbreeding coefficients for animals in the pedigree (alive or with children)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recalculate all coefficients, even if already cached",
        )

    def handle(self, *args, **options):
        # Get only pedigree-relevant animals (alive or have children)
        pedigree_animals = Animal.objects.for_pedigree()

        if options["force"]:
            # Recalculate everything in the pedigree
            queryset = pedigree_animals
            self.stdout.write(
                "Recalculating inbreeding coefficients for all pedigree animals..."
            )
        else:
            # Only calculate missing ones in the pedigree
            queryset = pedigree_animals.filter(
                life_history__inbreeding_coefficient__isnull=True
            )
            self.stdout.write(
                f"Calculating missing inbreeding coefficients for {queryset.count()} pedigree animals..."
            )

        total_count = queryset.count()
        if total_count == 0:
            self.stdout.write("No pedigree animals need inbreeding coefficient updates")
            return

        # Calculate all inbreeding coefficients at once using the pedigree set
        ped = pedigree.Pedigree.from_animals(
            [(animal.uuid, animal.sire, animal.dam) for animal in pedigree_animals]
        )
        inbreeding_coeffs = ped.get_inbreeding()

        # Update life history records for the target animals
        updated_count = 0
        for animal in queryset:
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
                f"Updated inbreeding coefficients for {updated_count} pedigree animals"
            )
        )
