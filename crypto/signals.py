from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from crypto.models import Balance

User = get_user_model()


@receiver(post_save, sender=User)
def create_balance_for_new_user(sender, instance, created, **kwargs):
    """Заводит нулевой баланс при регистрации пользователя."""
    if created:
        Balance.objects.create(user=instance)
