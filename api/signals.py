from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from api.gebruik import invalidate_gebruik_caches
from api.models import GewasGebruik


@receiver(post_save, sender=GewasGebruik)
@receiver(post_delete, sender=GewasGebruik)
def clear_gebruik_lookup_cache(sender, **kwargs) -> None:
    invalidate_gebruik_caches()
