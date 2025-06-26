# -*- mode: python -*-
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from birds.models import Animal, AnimalLifeHistory, Event


@receiver([post_save, post_delete], sender=Event)
def update_life_history_on_event_change(sender, instance, **kwargs):
    """Update life history when events are added/changed/deleted"""
    life_history, _ = AnimalLifeHistory.objects.get_or_create(animal=instance.animal)
    life_history.update_from_events()
    life_history.save()


@receiver(m2m_changed, sender=Animal.parents.through)
def update_inbreeding_on_parent_change(sender, instance, action, **kwargs):
    """Update inbreeding coefficient when animal's parents are set"""
    if action == "post_add":
        # Only handle the common case of adding parents
        instance.history.update_from_pedigree()


@receiver(post_save, sender=Animal)
def update_inbreeding_on_animal_creation(sender, instance, created, **kwargs):
    """Update inbreeding coefficient for newly created animals with parents"""
    if created:
        instance.history.update_from_pedigree()
