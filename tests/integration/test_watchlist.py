"""
Интеграционные тесты watchlist API.
Тестируем полный HTTP-цикл: запрос -> view -> сервис -> ответ.
Запросы к бирже замокированы.
"""

from rest_framework.test import APIClient


# Тесты аутентификации

def test_watchlist_requires_auth():
    """Без токена — 401."""
    client = APIClient()
    response = client.get('/api/watchlist/')
    assert response.status_code == 401


def test_existing_endpoints_remain_public(snapshots):
    """Публичные эндпоинты работают без токена."""
    client = APIClient()

    response = client.get('/api/snapshots/')
    assert response.status_code == 200

    response = client.get('/api/coins/')
    assert response.status_code == 200


# Тесты CRUD

def test_add_coin_to_watchlist(auth_client_a, mock_api_symbol_found):
    """POST /api/watchlist/ — добавление монеты, ответ 201."""
    response = auth_client_a.post('/api/watchlist/', {'symbol': 'btc'})

    assert response.status_code == 201
    assert response.data['symbol'] == 'BTC'
    assert response.data['coin_name'] == 'Bitcoin'


def test_add_invalid_symbol(auth_client_a, mock_api_symbol_not_found):
    """POST с несуществующим символом — 400."""
    response = auth_client_a.post('/api/watchlist/', {'symbol': 'NONEXISTENT'})
    assert response.status_code == 400


def test_add_duplicate_symbol(auth_client_a, mock_api_symbol_found):
    """Повторное добавление той же монеты — 409."""
    auth_client_a.post('/api/watchlist/', {'symbol': 'btc'})
    response = auth_client_a.post('/api/watchlist/', {'symbol': 'btc'})
    assert response.status_code == 409


def test_list_watchlist(auth_client_a, mock_api_symbol_found):
    """GET /api/watchlist/ — список монет пользователя."""
    auth_client_a.post('/api/watchlist/', {'symbol': 'btc'})

    response = auth_client_a.get('/api/watchlist/')
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['symbol'] == 'BTC'


def test_delete_from_watchlist(auth_client_a, mock_api_symbol_found):
    """DELETE /api/watchlist/BTC/ — удаление, ответ 204."""
    auth_client_a.post('/api/watchlist/', {'symbol': 'btc'})

    response = auth_client_a.delete('/api/watchlist/BTC/')
    assert response.status_code == 204

    # Проверяем что список пуст
    response = auth_client_a.get('/api/watchlist/')
    assert len(response.data) == 0


def test_delete_nonexistent_symbol(auth_client_a):
    """DELETE несуществующей монеты — 404."""
    response = auth_client_a.delete('/api/watchlist/BTC/')
    assert response.status_code == 404


# Тест изоляции данных между пользователями

def test_user_isolation(auth_client_a, auth_client_b, mock_api_symbol_found):
    """Пользователь A не видит данные пользователя B."""
    # A добавляет BTC
    auth_client_a.post('/api/watchlist/', {'symbol': 'btc'})

    # B видит пустой список
    response = auth_client_b.get('/api/watchlist/')
    assert response.status_code == 200
    assert len(response.data) == 0

    # A видит свою монету
    response = auth_client_a.get('/api/watchlist/')
    assert len(response.data) == 1
