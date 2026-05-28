# Islamic Finance LMS

Внутренняя PWA-система для банка исламской рассрочки.  
Роли: Менеджер · Служба Безопасности · Руководитель.  
Типы сделок: Murabaha · Ijara · Musharaka.

## Стек

| Слой | Технологии |
|---|---|
| Frontend | Next.js 14 · TypeScript · Tailwind · shadcn/ui · TanStack Query · Zustand · Recharts |
| Backend | FastAPI · SQLAlchemy 2.0 async · PostgreSQL 16 · Redis 7 · Celery |
| Хранилище | MinIO (S3-совместимый самохостинг) |
| Уведомления | SMS.ru · Telegram Bot (Inferno Solution) · SMTP |
| Документы | WeasyPrint · openpyxl |
| Прод | Docker Compose · Nginx · reg.ru VPS · GitHub Actions |

## Быстрый старт (локально)

### 1. Требования

- Python 3.12
- Node.js 20
- PostgreSQL 16 (локально)
- Redis 7 (локально)
- MinIO (Docker: `docker run -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ":9001"`)

### 2. Backend

```bash
cp backend/.env.example backend/.env
# Отредактируйте backend/.env

make gen-keys          # Генерация RSA ключей для JWT
make install-backend

# Создайте БД в PostgreSQL:
# createdb lms_db && createuser lms_user

make migrate           # Применить миграции
make seed              # Создать директора + дефолтные настройки
make dev-backend       # Запустить API на :8000
```

### 3. Frontend

```bash
cp frontend/.env.local.example frontend/.env.local
make install-frontend
make dev-frontend      # Запустить на :3000
```

### 4. Celery (опционально для фоновых задач)

```bash
make dev-worker
make dev-beat
```

### 5. Telegram Bot (Inferno Solution — опционально для уведомлений)

```bash
cp tg_bot/.env.example tg_bot/.env
make install-bot
make dev-bot           # HTTP сервер на :8080
# В отдельном терминале:
cd tg_bot && python main.py
```

## Первый вход

После `make seed` доступен аккаунт директора:
- Телефон: `+79000000001`
- Пароль: `Admin12345!`

## Структура проекта

```
SheyKey_LMS/
├── backend/           FastAPI + SQLAlchemy + Celery
├── frontend/          Next.js 14 PWA
├── tg_bot/            Telegram Bot (Inferno Solution)
├── infra/             Docker Compose (прод) + Nginx
├── migration/         Скрипты миграции из Google Sheets
└── .github/workflows/ CI/CD (reg.ru + Inferno Solution)
```

## Тесты

```bash
make test              # Unit тесты (calculators, state machines, auth)
make test-all          # Все тесты
make test-load         # Нагрузочное тестирование (locust)
```

## Продакшн (reg.ru)

Требуются GitHub Secrets:
- `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`
- `INFERNO_HOST`, `INFERNO_USER`, `INFERNO_SSH_KEY`

```bash
git push origin main   # Запускает CI/CD
```

## Лицензия

Закрытый внутренний проект.
