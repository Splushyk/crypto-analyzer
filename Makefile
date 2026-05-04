.PHONY: help up down restart build logs ps shell migrate makemigrations \
        createsuperuser collectstatic lint format test

# По умолчанию (если просто запустить `make` без аргументов) выводится help
.DEFAULT_GOAL := help

help:  ## Показать список доступных команд
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# --- Docker Compose ---

up:  ## Поднять весь стек в фоне
	docker compose up -d

down:  ## Остановить и удалить контейнеры (volumes сохраняются)
	docker compose down

restart:  ## Перезапустить все сервисы
	docker compose restart

build:  ## Пересобрать образы
	docker compose build

logs:  ## Смотреть логи всех сервисов в реальном времени (Ctrl+C для выхода)
	docker compose logs -f

ps:  ## Показать статус контейнеров
	docker compose ps

shell:  ## Открыть bash внутри web-контейнера
	docker compose exec web sh

# --- Django management ---

migrate:  ## Применить миграции
	docker compose exec web python manage.py migrate

makemigrations:  ## Сгенерировать миграции по изменениям моделей
	docker compose exec web python manage.py makemigrations

createsuperuser:  ## Создать суперюзера (интерактивно)
	docker compose exec web python manage.py createsuperuser

collectstatic:  ## Пересобрать статические файлы
	docker compose exec web python manage.py collectstatic --noinput

# --- Качество кода (запускается локально, без docker) ---

lint:  ## Запустить все линтеры (ruff, mypy, etc.) через pre-commit
	uv run pre-commit run --all-files

format:  ## Отформатировать код (ruff format)
	uv run ruff format .

test:  ## Запустить тесты (compose должен быть up — для доступа к БД)
	uv run pytest
