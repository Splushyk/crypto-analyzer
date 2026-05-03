"""
Unit-тесты сервисного слоя watchlist.
Тестируем функции напрямую, без HTTP-слоя (без APIClient DRF).
Все запросы к бирже замокированы.
"""

import pytest

from crypto.models import WatchlistItem
from crypto.services import (
    validate_symbol,
    add_to_watchlist,
    get_user_watchlist,
    remove_from_watchlist,
    SymbolNotFoundError,
    ExistInWatchlistError,
)


# Тесты validate_symbol

def test_validate_symbol_found(mock_api_symbol_found):
    """Если символ существует — возвращает (symbol, name)."""
    result = validate_symbol("btc")
    assert result == ("BTC", "Bitcoin")


def test_validate_symbol_not_found(mock_api_symbol_not_found):
    """Если символа нет на бирже — выбрасывает SymbolNotFoundError."""
    with pytest.raises(SymbolNotFoundError):
        validate_symbol("NONEXISTENT")


def test_validate_symbol_case_insensitive(mock_api_symbol_found):
    """Поиск работает независимо от регистра ввода."""
    result = validate_symbol("BTC")
    assert result == ("BTC", "Bitcoin")

    result = validate_symbol("btc")
    assert result == ("BTC", "Bitcoin")


# Тесты add_to_watchlist

def test_add_to_watchlist_success(user_a, mock_api_symbol_found):
    """Успешное добавление монеты: запись создана с правильными данными."""
    item = add_to_watchlist(user_a, "btc")

    assert item.user == user_a
    assert item.symbol == "BTC"
    assert item.coin_name == "Bitcoin"
    # Проверяем что запись реально в тестовой базе
    assert WatchlistItem.objects.filter(user=user_a, symbol="BTC").exists()


def test_add_to_watchlist_invalid_symbol(user_a, mock_api_symbol_not_found):
    """Если символ не найден — SymbolNotFoundError, запись не создаётся."""
    with pytest.raises(SymbolNotFoundError):
        add_to_watchlist(user_a, "NONEXISTENT")

    assert WatchlistItem.objects.count() == 0


def test_add_to_watchlist_duplicate(user_a, mock_api_symbol_found):
    """Повторное добавление той же монеты — ExistInWatchlistError."""
    add_to_watchlist(user_a, "btc")  # первый раз — ок

    with pytest.raises(ExistInWatchlistError):
        add_to_watchlist(user_a, "btc")  # второй раз — ошибка


# Тесты get_user_watchlist

def test_get_user_watchlist_returns_own_items(user_a, user_b, mock_api_symbol_found):
    """Пользователь видит только свои монеты, не чужие."""
    add_to_watchlist(user_a, "btc")

    # У user_a — одна монета
    assert get_user_watchlist(user_a).count() == 1
    # У user_b — пусто
    assert get_user_watchlist(user_b).count() == 0


def test_get_user_watchlist_empty(user_a):
    """Пустой watchlist возвращает пустой QuerySet."""
    result = get_user_watchlist(user_a)
    assert result.count() == 0


# Тесты remove_from_watchlist

def test_remove_from_watchlist_success(user_a, mock_api_symbol_found):
    """Удаление существующей монеты — возвращает True, запись исчезает из базы."""
    add_to_watchlist(user_a, "btc")

    result = remove_from_watchlist(user_a, "BTC")
    assert result is True
    assert WatchlistItem.objects.count() == 0


def test_remove_from_watchlist_not_found(user_a):
    """Удаление несуществующей монеты — возвращает False."""
    result = remove_from_watchlist(user_a, "BTC")
    assert result is False
