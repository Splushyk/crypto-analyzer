"""
Модуль интеграционного тестирования компонентов хранилища.

Ключевые сценарии:
1. Проверка жизненного цикла данных в SQLite: сохранение (INSERT) и извлечение (SELECT).
2. Тестирование сложной SQL-логики: корректность JOIN-запросов при сравнении снимков.
3. Валидация агрегатных функций и сортировки: проверка работы LIMIT и ORDER BY в методах аналитики.
4. Проверка реального взаимодействия с файловой системой для JsonStorage через временные директории (tmp_path).

Тесты используют реальный движок SQLite (в памяти) и проверяют интеграцию кода с СУБД.
"""

import json
import pytest

from src.models import Cryptocurrency
from src.storage import JsonStorage



def test_sqlite_save_and_get_all_snapshots(sqlite_storage, sample_coin, sample_results):
    """Проверка сохранения данных и получения списка снимков."""
    # Сохраняем первый снимок
    results_v1 = {"total_market_cap": 500.0}
    sqlite_storage.save([sample_coin], results_v1)

    # Сохраняем второй снимок
    results_v2 = {"total_market_cap": 888.888}
    sqlite_storage.save([sample_coin], results_v2)

    snapshots = sqlite_storage.get_all_snapshots()

    assert len(snapshots) == 2
    assert snapshots[0]["total_market_cap"] == 500.0
    assert snapshots[1]["total_market_cap"] == 888.888


def test_sqlite_comparison_logic(sqlite_storage, sample_results):
    """Проверка сложного SQL-запроса сравнения цен (JOIN) между двумя снимками."""
    # Создаем две версии одной монеты (цена выросла со 100 до 150)
    c1 = Cryptocurrency(name="SomeCoin", symbol="SC", price=100.0,
                        change_24h=0, volume=1000, market_cap=10000)
    c2 = Cryptocurrency(name="SomeCoin", symbol="SC", price=150.0,
                        change_24h=0, volume=1000, market_cap=15000)

    # Сохраняем два снимка
    sqlite_storage.save([c1], sample_results)  # ID 1
    sqlite_storage.save([c2], sample_results)  # ID 2

    # Вызываем метод сравнения
    diff = sqlite_storage.get_snapshot_compare(1, 2)

    assert len(diff) == 1
    assert diff[0]["symbol"] == "SC"
    assert diff[0]["old_price"] == 100.0
    assert diff[0]["new_price"] == 150.0
    # Проверяем расчет разницы и процента в SQL
    assert diff[0]["price_diff"] == 50.0
    assert diff[0]["percent_change"] == 50.0


def test_sqlite_top_movers_returns_correct_coins(sqlite_storage, sample_results):
    """Проверка, что get_top_movers возвращает монеты с наибольшим и наименьшим изменением."""
    coins = [
        Cryptocurrency(name="CoinA", symbol="CA", price=1.0, change_24h=10.0, volume=100, market_cap=1000),
        Cryptocurrency(name="CoinB",  symbol="CB", price=1.0, change_24h=5.0,  volume=100, market_cap=1000),
        Cryptocurrency(name="CoinC", symbol="CC", price=1.0, change_24h=-8.0, volume=100, market_cap=1000),
    ]
    sqlite_storage.save(coins, sample_results)

    movers = sqlite_storage.get_top_movers()

    assert movers["gainers"][0]["symbol"] == "CA"  # наибольший рост
    assert movers["losers"][0]["symbol"] == "CC"   # наибольшее падение


def test_sqlite_coin_history(sqlite_storage, sample_coin, sample_results):
    """Проверка получения истории конкретной монеты (используются фикстуры)."""
    # Используем готовую монету из conftest.py (SomeCoin / SC)
    sqlite_storage.save([sample_coin], sample_results)

    # Ищем историю именно по её символу
    history = sqlite_storage.get_coin_history(sample_coin.symbol)

    assert len(history) == 1
    assert history[0]["price"] == sample_coin.price


def test_json_storage_save_integration(sample_coin, sample_results, tmp_path):
    # Создаем путь к временному файлу
    test_file = tmp_path / "test_report.json"
    storage = JsonStorage(filename=str(test_file))

    # Выполняем сохранение
    storage.save([sample_coin], sample_results)

    # Проверяем, что файл создался
    assert test_file.exists()

    # Читаем файл и проверяем структуру
    with open(test_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "generated_at" in data
    assert data["total_market_cap_usd"] == sample_results["total_market_cap"]
    assert data["top_gainers"][0]["symbol"] == sample_coin.symbol
    assert data["highest_volume"]["volume"] == sample_results["max_volume"].volume
