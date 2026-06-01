# SheyKey Islamic Finance LMS

Внутренняя PWA-система для управления исламскими финансовыми сделками.  
Роли: Менеджер · Служба Безопасности · Руководитель.  
Типы сделок: Мурабаха · Иджара.

## Стек

| Слой | Технологии |
|---|---|
| Frontend | Next.js 14 · TypeScript · Tailwind · shadcn/ui · TanStack Query · Zustand · Recharts |
| Backend | FastAPI · SQLAlchemy 2.0 async · PostgreSQL 16 · Redis 7 · Celery |
| Хранилище | MinIO (S3-совместимый самохостинг) |
| Уведомления | SMS.ru · Web Push · SMTP |
| Документы | WeasyPrint · openpyxl |
| Прод | Docker Compose · Nginx · reg.ru VPS |

## Быстрый старт (локально)

### 1. Требования

- Python 3.12 (`brew install python@3.12`)
- Node.js 20 (`brew install node@20`)
- PostgreSQL 16 (`brew install postgresql@16 && brew services start postgresql@16`)
- Redis 7 (`brew install redis && redis-server --daemonize yes`)
- MinIO (опционально, для загрузки файлов):
  ```bash
  docker run -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ":9001"
  ```

### 2. Первоначальная настройка

```bash
# Скопировать и заполнить .env
cp backend/.env.example backend/.env

# Сгенерировать RSA ключи для JWT (один раз)
make gen-keys

# Создать БД
createdb lms_db
createuser lms_user
psql -c "ALTER USER lms_user WITH PASSWORD 'lms_pass';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE lms_db TO lms_user;"

# Установить зависимости
make install-backend
make install-frontend

# Применить миграции и создать начальные данные
make migrate
make seed
```

### 3. Запуск

```bash
make dev          # Запускает бэкенд + фронтенд одной командой
```

Или по отдельности:
```bash
make dev-backend  # API на :8000
make dev-frontend # Интерфейс на :3000
```

Фоновые задачи (SMS-напоминания, авторассылки — опционально):
```bash
make dev-worker
make dev-beat
```

## Аккаунты после `make seed`

| Роль | Телефон | Пароль |
|---|---|---|
| Руководитель | `+79000000001` | `Admin12345!` |
| Менеджер | `+79000000002` | `Manager12345!` |
| Служба Безопасности | `+79000000003` | `SB12345678!` |

> Создать аккаунты менеджера и СБ можно через кабинет руководителя → Настройки → Сотрудники.

## Структура проекта

```
SheyKey_LMS/
├── backend/           FastAPI + SQLAlchemy + Celery
├── frontend/          Next.js 14 PWA
├── infra/             Docker Compose (прод) + Nginx
└── migration/         Импорт из Google Sheets
```

## Тесты

```bash
make test         # Unit тесты (калькуляторы, статус-машины, авторизация)
make test-all     # Все тесты
```

## Импорт данных из Google Sheets

В кабинете руководителя есть раздел **«Импорт данных»** — скачай таблицу как `.xlsx` и загрузи через интерфейс. Либо воспользуйся скриптами:

```bash
make install-migration
make migration-extract    # Выгрузить из Google Sheets
make migration-transform  # Нормализовать
make migration-load       # Загрузить в БД
make migration-verify     # Проверить
```

Подробнее: [`migration/README.md`](migration/README.md)

## Продакшн (reg.ru)

Деплой вручную на сервере (автодеплой из GitHub отключён):

```bash
cd /srv/lms
git pull origin main
docker compose -f infra/docker-compose.yml up -d --build
docker compose -f infra/docker-compose.yml exec -T api alembic upgrade head
```

## Лицензия

Закрытый внутренний проект. © SheyKey
