# Сервис сокращения ссылок


## Стек

- **FastAPI** — фреймворк
- **PostgreSQL** — основное хранилище
- **Redis** — кэширование
- **Docker** — контейнеризация

## Запуск
**Требования:** установленный [Docker Desktop](https://www.docker.com/products/docker-desktop)
```bash
git clone https://github.com/o-avdienko/fastapi_project.git
cd fastapi_project
docker-compose up --build
```

После запуска:
- API: http://localhost:8000
- Документация: http://localhost:8000/docs

## Эндпоинты

### Пользователи

| Метод | URL | Описание | Авторизация |
|-------|-----|----------|-------------|
| POST | /users/register | Регистрация | Нет |
| POST | /users/login | Вход, возвращает JWT-токен | Нет |
| GET | /users/me | Информация о себе | Да |

### Ссылки

| Метод | URL | Описание | Авторизация |
|-------|-----|----------|-------------|
| POST | /links/shorten | Создать короткую ссылку | Нет |
| GET | /{short_code} | Редирект на оригинальный URL | Нет |
| GET | /links/{short_code}/stats | Статистика по ссылке | Нет |
| GET | /links/search?original_url= | Поиск по оригинальному URL | Нет |
| DELETE | /links/{short_code} | Удалить ссылку | Да |
| PUT | /links/{short_code} | Обновить ссылку | Да |
| GET | /links/expired | История истёкших ссылок | Нет |
| POST | /links/admin/cleanup | Ручная очистка истёкших ссылок | Да |
| PUT | /links/admin/unused-days | Задать порог неактивности (дней) | Да |

## Примеры запросов

### Регистрация
```bash
curl -X POST http://localhost:8000/users/register \
  -H "Content-Type: application/json" \
  -d '{"username": "oleg", "email": "oleg@example.com", "password": "secret123"}'
```

### Вход
```bash
curl -X POST http://localhost:8000/users/login \
  -d "username=oleg&password=secret123"
```

### Создать короткую ссылку
```bash
curl -X POST http://localhost:8000/links/shorten \
  -H "Content-Type: application/json" \
  -d '{"original_url": "https://example.com"}'
```

### Создать с кастомным псевдонимом и сроком жизни
```bash
curl -X POST http://localhost:8000/links/shorten \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"original_url": "https://example.com", "custom_alias": "mylink", "expires_at": "2026-12-31T23:59:00"}'
```

### Статистика
```bash
curl http://localhost:8000/links/mylink/stats
```

### Обновить ссылку
```bash
curl -X PUT http://localhost:8000/links/mylink \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"original_url": "https://new-url.com"}'
```

### Удалить ссылку
```bash
curl -X DELETE http://localhost:8000/links/mylink \
  -H "Authorization: Bearer <token>"
```

## База данных

### Таблица `users`
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | integer | Первичный ключ |
| username | varchar(50) | Уникальное имя пользователя |
| email | varchar(100) | Уникальный email |
| hashed_password | varchar(200) | bcrypt-хэш пароля |
| created_at | timestamp | Дата регистрации |

### Таблица `links`
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | integer | Первичный ключ |
| original_url | text | Оригинальный URL |
| short_code | varchar(20) | Уникальный короткий код |
| custom_alias | varchar(50) | Кастомный псевдоним (опционально) |
| created_at | timestamp | Дата создания |
| expires_at | timestamp | Дата истечения (опционально) |
| click_count | integer | Количество переходов |
| last_used_at | timestamp | Дата последнего перехода |
| owner_id | integer | ID пользователя (опционально) |

### Таблица `expired_links`
Архив истёкших ссылок. Те же поля что и в `links` + `expired_at` — дата истечения.

## Кэширование

Redis кэширует два типа данных:

- **URL ссылки** — ключ `link:{short_code}`, TTL 1 час. Используется при редиректе — позволяет не обращаться к PostgreSQL при каждом переходе.
- **Статистика** — ключ `stats:{short_code}`, TTL 5 минут. Используется в `/stats`.

При обновлении или удалении ссылки соответствующие ключи удаляются из Redis.

## Дополнительные функции

- **История истёкших ссылок** — `GET /links/expired` возвращает архив всех удалённых по таймауту ссылок.
- **Удаление неиспользуемых ссылок** — автоматически каждый час удаляются ссылки без переходов за N дней. Порог задаётся через `PUT /links/admin/unused-days`.