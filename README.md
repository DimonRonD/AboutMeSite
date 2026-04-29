# AboutMeSite (Flask)

Полноценный веб-сайт на Flask с кейсами, формой обратной связи, защищенной админ-панелью и современным динамическим hero-блоком.

## Функционал

- Главная страница с hero-блоком, ротацией 3 текстов и блоком позиционирования "Почему выбирают нас".
- Раздел кейсов с отдельной детальной страницей для каждого кейса и расширенными контент-блоками.
- Форма обратной связи (имя, email, телефон, тема, сообщение) с валидацией.
- Админ-панель с авторизацией и управлением заявками:
  - просмотр всех обращений;
  - отметка как "прочитано";
  - удаление заявок.
- Полноценное логирование: консоль + файл с ротацией, HTTP-запросы, 404/500 ошибки.
- Усиленная безопасность: rate limit на вход в админку, безопасные cookie, security headers, маскирование PII в логах.

## Актуальные кейсы

- Nutribot (Telegram-бот для фитнес/wellness): персональные рекомендации, удержание пользователей, снижение операционных затрат.
- Шмавито (платформа объявлений/маркетплейс): быстрый запуск сервиса в стиле Avito/eBay и гибкая монетизация.
- Pusplexity (платформа автоматизации): работа с изображениями и документами через Telegram/Web, ускорение внутренних процессов.
- Корпоративный сайт.
- AI-ассистент для поддержки клиентов.

Для кейсов Nutribot, Шмавито и Pusplexity используются локальные иллюстрации из `static/images/...`.

## Технологии

- Flask
- Flask-Login
- Flask-SQLAlchemy
- Flask-WTF (CSRF + формы)
- Jinja2
- SQLite
- Bootstrap 5

## Структура проекта

```text
AboutMeSite/
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── database/
├── templates/
└── static/
    ├── css/
    ├── js/
    └── images/
```

## Настройка .env

Все ключи и константы конфигурации хранятся в `.env`.

Скопируйте пример и при необходимости измените значения:

```bash
cp .env.example .env
```

Для Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

## Быстрый запуск

1. Установите зависимости:

```bash
pip install -r requirements.txt
```

2. Запустите приложение:

```bash
python app.py
```

После запуска сайт будет доступен по адресу:

- [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Запуск через Docker

1. Подготовьте `.env`:

```bash
cp .env.example .env
```

Для Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

2. Соберите и запустите контейнер:

```bash
docker compose up --build -d
```

3. Откройте сайт:

- [http://127.0.0.1:5000](http://127.0.0.1:5000)

Полезные команды:

```bash
docker compose logs -f
docker compose down
```

SQLite-база хранится в локальной папке `database/` через volume `./database:/app/database`.

Важно: контейнер запускается от непривилегированного пользователя `appuser`, поэтому
на сервере у папок `database/` и `logs/` должны быть права на запись:

```bash
mkdir -p database logs
chmod 775 database logs
```

## Доступ в админ-панель

- URL: `/admin/login`
- Логин: `admin`
- Пароль: `admin123`

Рекомендуется сменить `DEFAULT_ADMIN_PASSWORD` и `SECRET_KEY` в `.env` перед production-запуском.

## Логирование

Приложение пишет логи в консоль и в файл (по умолчанию `logs/app.log`) с ротацией.

Параметры в `.env`:

- `LOG_LEVEL` — уровень логирования (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- `LOG_FILE` — путь к файлу логов
- `LOG_MAX_BYTES` — максимальный размер файла до ротации
- `LOG_BACKUP_COUNT` — количество архивных лог-файлов
- `PII_LOGGING_ENABLED` — включить/выключить логирование персональных данных (рекомендуется `false`)

## Security hardening

- Rate limit для `POST /admin/login` (ограничение попыток входа по IP).
- Fail-fast проверка production-конфига: слабый `SECRET_KEY` и дефолтные admin-учетные данные запрещены.
- Безопасные cookie-параметры с поддержкой HTTPS за reverse proxy.
- Security headers: CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy.

## Продакшен-домен

Для домена `aboutme.dimonrond.ru` используйте reverse proxy (например, Nginx/Caddy) перед контейнером, настройте SSL (Let's Encrypt) и укажите корректные DNS-записи.
