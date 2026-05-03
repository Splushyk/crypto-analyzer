# syntax=docker/dockerfile:1.7

# Stage 1: builder — собирает venv с зависимостями через uv
FROM python:3.14-slim AS builder

# Pin версию uv — latest ломает воспроизводимость сборок
COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Сначала только lock-файлы — отдельный слой для зависимостей.
# Меняются редко → кэш переиспользуется при пересборке после правок кода.
COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Теперь сам код проекта — этот слой инвалидируется при любом изменении.
COPY . .



# Stage 2: runtime — минимальный образ без uv и build-артефактов
FROM python:3.14-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Системный пользователь без shell и home — запускаем приложение от него
RUN groupadd --system --gid 1000 app \
 && useradd --system --uid 1000 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

# Копируем готовый /app из builder сразу с правильным владельцем
COPY --from=builder --chown=app:app /app /app

USER app

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
