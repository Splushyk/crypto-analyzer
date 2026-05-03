# Crypto Analyzer

Django REST API для сбора, хранения и анализа рыночных данных с **CoinGecko** и **CoinMarketCap**. Включает legacy CLI на Typer.

## Архитектура
Проект состоит из двух независимых слоёв, каждый со своей точкой входа и хранилищем.

### Django-приложение (`crypto/`)
Основной слой — REST API для сбора, хранения и анализа рыночных данных.

* **Models**: `Snapshot`, `CoinPrice`, `WatchlistItem` — реляционная схема в PostgreSQL.
* **Services** (`services.py`): бизнес-логика (аналитика, watchlist), не зависит от DRF.
* **Views + Serializers**: тонкий DRF-слой, отдаёт данные по REST API.
* **Management-команды**: `fetch_snapshot` для постановки задачи сбора в очередь Celery.
* **Фоновые задачи** (`tasks.py`): Celery-задача сбора снимка с retry и расписанием через Celery Beat. Брокер и result backend — Redis.

### Legacy CLI (`src/`)
Отдельный консольный инструмент на Typer — параллельный путь сбора и анализа с сохранением в SQLite/JSON. Работает независимо от Django, построен по принципу разделения ответственности (**Separation of Concerns**):

* **Infrastructure**: `ApiClient` (сетевое взаимодействие) и `Visualizers` (вывод в Console).
* **Storage**: База данных (SQLite/JSON) для сохранения снимков рынка и их сравнения.
* **Parser & Models**: Преобразование сырого JSON в объекты моделей `Cryptocurrency`.
* **Logic**: Провайдеры (оркестрация получения данных) и Анализатор (фильтрация, сортировка, расчет метрик).
* **Entry Point**: `main.py` — CLI-интерфейс на базе Typer с поддержкой работы с историей данных.

## Установка

Зависимости: Python 3.14+, Postgres, Redis, пакетный менеджер [`uv`](https://docs.astral.sh/uv/).

```bash
git clone <repo-url>
cd crypto-analyzer
uv sync
cp .env.example .env  # затем заполнить значения
```

### Переменные окружения (`.env`)

| Переменная | Назначение |
| --- | --- |
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` для разработки, `False` для продакшена |
| `ALLOWED_HOSTS` | Список через запятую, напр. `localhost,127.0.0.1` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Параметры подключения к Postgres |
| `CELERY_BROKER_URL` | URL Redis (по умолчанию `redis://localhost:6379/0`) |
| `CELERY_RESULT_BACKEND` | URL Redis для результатов |
| `CRYPTO_PROVIDER` | `coingecko` или `cmc` (по умолчанию `coingecko`) |
| `CMC_API_KEY` | API-ключ CoinMarketCap (нужен только при `CRYPTO_PROVIDER=cmc`) |

### Миграции и суперпользователь

```bash
uv run python manage.py migrate
uv run python manage.py createsuperuser
```

## Запуск

### Development

```bash
uv run python manage.py runserver
uv run celery -A config worker -l INFO
uv run celery -A config beat -l INFO
```

### Production (Gunicorn + Whitenoise)

Перед первым запуском (и после каждого деплоя) собрать статику:

```bash
uv run python manage.py collectstatic --noinput
```

Запуск приложения:

```bash
uv run gunicorn config.wsgi:application
```

По умолчанию слушает `127.0.0.1:8000` с одним sync-воркером. Для прод-окружения адрес и количество воркеров задаются флагами `--bind` и `--workers`.

Статика (админка, Swagger UI, DRF browsable API) отдаётся через [Whitenoise](https://whitenoise.readthedocs.io/) с хешированием имён и gzip-сжатием (`CompressedManifestStaticFilesStorage`).

## Команды

### Django management-команды
* `uv run python manage.py fetch_snapshot --source [coingecko|cmc]` — постановка задачи сбора в очередь Celery (вернёт `task_id`).
* `uv run python manage.py runserver` — запуск dev REST API.
* `uv run python manage.py migrate` — применение миграций.
* `uv run python manage.py collectstatic --noinput` — сборка статики для прод.

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

Все бизнес-эндпоинты находятся под префиксом `/api/v1/` (`URLPathVersioning`). Эндпоинты JWT-токенов и документации (`/api/auth/token/`, `/api/docs/` и т.п.) — без версии.

**Аутентификация:** JWT (`rest_framework_simplejwt`). Access-токен передаётся в заголовке:

```
Authorization: Bearer <access_token>
```

Access TTL — 5 минут, refresh — 1 день, refresh-токены ротируются.

**Throttling** (по ролям):

| Роль | Лимит |
| --- | --- |
| Анонимный | 5 запросов / минуту |
| Авторизованный | 100 запросов / минуту |
| Суперпользователь | 1000 запросов / минуту |

При превышении — `429 Too Many Requests`.

**Пагинация:**
* По умолчанию — `PageNumberPagination`, `page_size=10` (параметры: `?page=N`).
* Для `/api/v1/snapshots/` — `PageNumberPagination` с `page_size=2` (снимок — тяжёлый объект с вложенными ценами).
* Для истории цен (`/api/v1/coins/`) — `CursorPagination` (параметр: `?cursor=...`).

**Фильтрация:** через `django-filter`. Сортировка — через `OrderingFilter` (где явно подключена).

**Документация:**
* Swagger UI — `/api/docs/` (с кнопкой Authorize для JWT).
* ReDoc — `/api/redoc/`.
* OpenAPI-схема — `/api/schema/`.

**Формат ошибок:** все ошибки приведены к единому виду через кастомный `exception_handler`:

```json
{"error": "human-readable message", "code": "machine_readable_code"}
```

Покрываются: `400`, `401`, `403`, `404`, `409`, `429`, `500`.

**Эндпоинты:**

| Метод | Путь | Права | Описание |
| --- | --- | --- | --- |
| `GET` | `/api/v1/snapshots/` | Anyone | Список снимков с пагинацией, ordering по `created_at` / `total_market_cap` |
| `GET` | `/api/v1/snapshots/{id}/` | Anyone | Детали снимка с вложенными ценами |
| `GET` | `/api/v1/coins/` | Anyone | История цен. Фильтры: `symbol`, `min_price`, `max_price`. CursorPagination |
| `GET` | `/api/v1/analytics/market-stats/` | Anyone | min/max/avg цена и суммарная капитализация по последнему снимку |
| `GET` | `/api/v1/analytics/top-movers/` | Anyone | Топ-5 по росту и топ-5 по падению за 24ч |
| `GET` | `/api/v1/analytics/volume-leaders/` | Anyone | Топ-10 монет по объёму торгов |
| `POST` | `/api/v1/tasks/fetch-snapshot/` | Staff | Запуск задачи сбора, возвращает `202` и `task_id` |
| `GET` | `/api/v1/tasks/{task_id}/status/` | Anyone | Статус задачи (`PENDING` / `STARTED` / `SUCCESS` / `FAILURE`) |
| `POST` | `/api/auth/token/` | — | Получение access/refresh токенов |
| `POST` | `/api/auth/token/refresh/` | — | Обновление access-токена |
| `GET` | `/api/v1/watchlist/` | JWT | Список монет текущего пользователя |
| `POST` | `/api/v1/watchlist/` | JWT | Добавить монету в watchlist |
| `DELETE` | `/api/v1/watchlist/{symbol}/` | JWT | Удалить монету из watchlist |

Бизнес-логика watchlist вынесена в сервисный слой (`services.py`), который не зависит от DRF. Перед сохранением монеты символ валидируется через API биржи.

## Фоновые задачи (Celery)
Сбор снимка рынка выполняется асинхронно через Celery. Брокер и result backend — Redis.

* **Задача**: `fetch_snapshot_task` в `crypto/tasks.py` — получает данные от провайдера и сохраняет `Snapshot` и связанные `CoinPrice` в PostgreSQL.
* **Retry**: при сетевых ошибках (`RequestException`) задача повторяется до 5 раз с экспоненциальным backoff и jitter, потолок задержки — 600 секунд.
* **Расписание**: Celery Beat запускает задачу раз в час (`fetch-snapshot-hourly`).

**Запуск воркера и планировщика:**
```bash
uv run celery -A config worker -l INFO
uv run celery -A config beat -l INFO
```

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
* **Celery-задачи**: Интеграционные тесты в eager-режиме (провайдер замокирован): успешное выполнение задачи, retry на сетевой ошибке и контракт API-эндпоинта запуска задачи.

### Запуск тестов:
```bash
# Общая команда (конфигурация запуска настроена в pyproject.toml)
uv run pytest

# Запуск по категориям
uv run pytest -m unit
uv run pytest -m integration
```

## Разработка

Перед коммитом запустить линтеры и форматтеры:

```bash
uv run pre-commit run --all-files
```