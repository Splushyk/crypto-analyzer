"""
Интеграционные тесты портфеля и баланса пользователя.
"""

from decimal import Decimal

from django.contrib.auth.models import User

from crypto.models import Balance


def test_balance_is_created_for_new_user(db):
    """При создании юзера сигналом автоматически заводится нулевой баланс."""
    user = User.objects.create_user(username="new_user", password="pass12345")

    assert Balance.objects.filter(user=user).count() == 1
    assert user.balance.amount == Decimal("0")


def test_balance_is_not_recreated_on_user_update(user_a):
    """При сохранении уже существующего юзера новый Balance не создаётся."""
    initial_count = Balance.objects.filter(user=user_a).count()

    user_a.email = "changed@example.com"
    user_a.save()

    assert Balance.objects.filter(user=user_a).count() == initial_count
