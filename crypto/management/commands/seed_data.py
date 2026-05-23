from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from crypto.models import Balance, CoinPrice, Portfolio, Snapshot


class Command(BaseCommand):
    help = "Наполняет БД тестовыми данными"

    def add_arguments(self, parser):
        parser.add_argument("--snapshots", type=int, default=500)
        parser.add_argument("--coins", type=int, default=100)

    def handle(self, *args, **options):
        snapshots = options["snapshots"]
        coins = options["coins"]

        Snapshot.objects.all().delete()

        snap_objs = [Snapshot(total_market_cap=1_000_000 + i) for i in range(snapshots)]
        snaps = Snapshot.objects.bulk_create(snap_objs)
        now = timezone.now()
        for i, snap in enumerate(snaps):
            snap.created_at = now - timedelta(hours=i)
        Snapshot.objects.bulk_update(snaps, ["created_at"])

        price_objs = []
        for snap in snaps:
            for i in range(coins):
                price_objs.append(
                    CoinPrice(
                        snapshot=snap,
                        name=f"COIN{i}",
                        symbol=f"SMB{i}",
                        price=100 + i,
                        change_24h=10 + i,
                        volume=1000 + i,
                        market_cap=2000 + i,
                    )
                )
        CoinPrice.objects.bulk_create(price_objs, batch_size=1000)

        user, _ = User.objects.get_or_create(
            username="seeduser",
            defaults={"email": "seed@example.com"},
        )
        user.set_password("seedpass123")
        user.save()

        balance, _ = Balance.objects.update_or_create(
            user=user,
            defaults={"amount": Decimal("100000")},
        )

        Portfolio.objects.filter(user=user).delete()
        positions = [
            Portfolio(
                user=user,
                symbol=f"SMB{i}",
                amount=Decimal("1.5"),
                buy_price=Decimal("100"),
            )
            for i in range(20)
        ]
        Portfolio.objects.bulk_create(positions)

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: {len(snaps)} снимков, {len(price_objs)} монет. \n"
                f"Пользователь: {user}. Баланс: {balance.amount}. Позиций:"
                f" {len(positions)}"
            )
        )
