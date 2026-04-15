# Crypto Analyzer

Django REST API для сбора, хранения и анализа рыночных данных с **CoinGecko** и **CoinMarketCap**. Включает legacy CLI на Typer.

## Архитектура
Проект состоит из двух независимых слоёв, каждый со своей точкой входа и хранилищем.

### Django-приложение (`crypto/`)
Основной слой — REST API для сбора, хранения и анализа рыночных данных.

* **Models**: `Snapshot`, `CoinPrice`, `WatchlistItem` — реляционная схема в PostgreSQL.
* **Services** (`services.py`): бизнес-логика (аналитика, watchlist), не зависит от DRF.
* **Views + Serializers**: тонкий DRF-слой, отдаёт данные по REST API.
* **Management-команды**: `fetch_snapshot` для сбора данных с биржи в PostgreSQL.

### Legacy CLI (`src/`)
Отдельный консольный инструмент на Typer — параллельный путь сбора и анализа с сохранением в SQLite/JSON. Работает независимо от Django, построен по принципу разделения ответственности (**Separation of Concerns**):

* **Infrastructure**: `ApiClient` (сетевое взаимодействие) и `Visualizers` (вывод в Console).
* **Storage**: База данных (SQLite/JSON) для сохранения снимков рынка и их сравнения.
* **Parser & Models**: Преобразование сырого JSON в объекты моделей `Cryptocurrency`.
* **Logic**: Провайдеры (оркестрация получения данных) и Анализатор (фильтрация, сортировка, расчет метрик).
* **Entry Point**: `main.py` — CLI-интерфейс на базе Typer с поддержкой работы с историей данных.

## Команды

### Django management-команды
* `python manage.py fetch_snapshot --source [coingecko|cmc]` — сбор данных с биржи и сохранение в PostgreSQL.
* `python manage.py runserver` — запуск REST API.

### CLI (legacy, `src/main.py`)
* `run` — основной цикл: загрузка, анализ, вывод и сохранение данных.
* `list-snapshots` — просмотр списка всех сохранённых в базе снимков.
* `compare-snapshots ID1 ID2` — сравнение цен между двумя снимками по их ID.

## Работа с базой данных (Django & PostgreSQL)
Django-слой использует PostgreSQL. Legacy CLI из `src/` продолжает работать с SQLite/JSON-хранилищами независимо.

**Схема базы данных**
Архитектура БД построена на реляционной связи «Один-ко-многим»:
* **Snapshot**: хранит метаданные сеанса сбора (дата создания и общая капитализация).
* **CoinPrice**: содержит детальные метрики каждой монеты, связанные с конкретным снимком.

**REST API (Django REST Framework)**
* `GET /api/snapshots/` — список снимков с пагинацией
* `GET /api/snapshots/{id}/` — детали снимка с вложенными ценами
* `GET /api/coins/?symbol=BTC&min_price=X&max_price=Y` — история цен монеты с фильтрами по символу и диапазону цен (все параметры опциональны)
* `GET /api/analytics/market-stats/` — агрегаты по последнему снимку: min/max/avg цена и суммарная рыночная капитализация
* `GET /api/analytics/top-movers/` — топ-5 монет по росту и топ-5 по падению за 24ч из последнего снимка
* `GET /api/analytics/volume-leaders/` — топ-10 монет по объёму торгов из последнего снимка

**Watchlist API (JWT)**

Персональный список отслеживаемых монет с JWT-аутентификацией через simplejwt.

- `POST /api/token/` — получение access/refresh токенов (без JWT)
- `POST /api/token/refresh/` — обновление access-токена (без JWT)
- `GET /api/watchlist/` — список монет текущего пользователя (JWT)
- `POST /api/watchlist/` — добавление монеты в watchlist (JWT)
- `DELETE /api/watchlist/<symbol>/` — удаление монеты из watchlist (JWT)

Бизнес-логика вынесена в сервисный слой (`services.py`), который не зависит от DRF. Перед сохранением монеты символ валидируется через API биржи.

## Тестирование
Используется разделение на Unit-тесты (логика) и Integration-тесты (работа с БД через Django ORM и REST API через тестовый `APIClient`).

**Объекты тестирования:**
* **Алгоритмы**: Сортировка и расчеты в `CryptoAnalyzer`.
* **Отказоустойчивость**: Обработка сетевых исключений и ошибок базы данных.
* **Валидация**: Парсинг ответов и обработка пустых состояний БД.
* **Интерфейсы**: Проверка CLI-команд и визуализаторов через мокирование.
* **Сервисный слой**: Unit-тесты бизнес-логики watchlist (без HTTP, все запросы к бирже замокированы).
* **Watchlist API**: Интеграционные тесты CRUD-операций, JWT-аутентификации и изоляции данных между пользователями.
* **REST API и ORM**: Интеграционные тесты snapshots, coins и analytics эндпоинтов, включая регрессионные проверки количества SQL-запросов через `django_assert_num_queries`.

### Запуск тестов:
```bash
# Общая команда (конфигурация запуска настроена в pyproject.toml)
pytest

# Запуск по категориям
pytest -m unit
pytest -m integration
```