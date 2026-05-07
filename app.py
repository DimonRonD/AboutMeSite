import logging
import os
import re
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

from flask import Flask, flash, g, jsonify, redirect, render_template, request, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from openai import BadRequestError, OpenAI
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import EmailField, PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp

from config import Config
from rag_service import RagService

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=[])


class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class ContactRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    subject = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ChatMemory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    question = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class ChatLogSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_key = db.Column(db.String(320), nullable=False, unique=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    email_masked = db.Column(db.String(255), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class ChatLogMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_key = db.Column(db.String(320), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
    text = db.Column(db.Text, nullable=False)
    order_idx = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class ContactForm(FlaskForm):
    name = StringField("Имя", validators=[DataRequired(), Length(min=2, max=120)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField(
        "Телефон",
        validators=[
            Optional(),
            Length(max=30),
            Regexp(r"^[0-9+\-() ]*$", message="Телефон содержит недопустимые символы."),
        ],
    )
    subject = StringField("Тема сообщения", validators=[DataRequired(), Length(min=3, max=255)])
    message = TextAreaField("Сообщение", validators=[DataRequired(), Length(min=10, max=2000)])
    submit = SubmitField("Отправить заявку")


class AdminLoginForm(FlaskForm):
    username = StringField("Логин", validators=[DataRequired(), Length(min=3, max=100)])
    password = PasswordField("Пароль", validators=[DataRequired(), Length(min=6, max=128)])
    submit = SubmitField("Войти")


class EmptyForm(FlaskForm):
    submit = SubmitField("Подтвердить")


CASES = [
    {
        "id": 1,
        "title": "Разработка Telegram-бота для бизнеса",
        "short_description": (
            "Nutribot — интеллектуальный Telegram-бот на базе n8n для персональных "
            "рекомендаций по питанию и тренировкам."
        ),
        "full_description": (
            "Nutribot — это интеллектуальный Telegram-бот на базе n8n, который "
            "автоматизирует персональные рекомендации по питанию и тренировкам, "
            "помогает удерживать клиентов и снижает операционные расходы фитнес- "
            "и wellness-бизнеса."
        ),
        "tangible_benefit": [
            "Сокращение времени первичного ответа клиенту: в среднем на 8-12 минут.",
            "Снижение операционной нагрузки на команду: ориентировочно на 0.5-1.5 штатных единицы.",
            "Рост удержания и удовлетворенности клиентов: в среднем на 10-18%.",
        ],
        "business_benefits": [
            "Снижение затрат на рутину: бот берет на себя первичный опрос, сбор параметров клиента и выдачу базовых персональных рекомендаций.",
            "Масштабирование без роста штата: один бот может одновременно обслуживать сотни и тысячи пользователей 24/7.",
            "Быстрый запуск новых услуг: через n8n легко добавлять программы питания, тренировочные планы, челленджи, подписки и рассылки.",
            "Рост вовлеченности и удержания: клиент получает рекомендации в привычном канале Telegram и чаще возвращается к диалогу.",
            "Персонализация как конкурентное преимущество: ответы формируются с учетом данных пользователя, а не по шаблону для всех.",
            "Гибкая интеграция в текущие процессы: бот связывается с Google Sheets, CRM, AI-сервисами и внутренней аналитикой.",
        ],
        "economy_effect": [
            "Меньше ручной нагрузки на специалистов.",
            "Ниже стоимость обработки одного клиента.",
            "Выше конверсия из интереса в регулярное взаимодействие.",
            "Быстрее окупаемость digital-каналов за счет автоматизации и персонализации.",
        ],
        "image": "images/Nutribot/Nutribot_1.jpg",
        "gallery": [
            "images/Nutribot/Nutribot_1.jpg",
            "images/Nutribot/Nutribot_2.jpg",
        ],
    },
    {
        "id": 2,
        "title": "Создание интернет-магазина",
        "short_description": (
            "Шмавито — готовая онлайн-платформа для аренды и продажи вещей "
            "в стиле Avito/eBay без разработки с нуля."
        ),
        "full_description": (
            "Шмавито — это готовая онлайн-платформа для аренды и продажи вещей, "
            "которая помогает бизнесу быстро запустить собственный маркетплейс "
            "в стиле Avito/eBay без затрат на разработку с нуля."
        ),
        "tangible_benefit": [
            "Экономия времени запуска продукта: в среднем на 2-4 месяца относительно разработки с нуля.",
            "Снижение затрат на запуск и поддержку MVP: ориентировочно на 25-40%.",
            "Рост конверсии в целевые действия за счет готовых пользовательских сценариев: в среднем на 8-15%.",
        ],
        "business_benefits": [
            "Быстрый запуск сервиса объявлений и сделок на собственной инфраструктуре.",
            "Новый источник выручки за счет комиссий, платного размещения и дополнительных услуг.",
            "Рост клиентской базы: продавцы и покупатели собираются в одной экосистеме.",
            "Прозрачные процессы: каталог, модерация, статусы, история заказов.",
            "Гибкая модель монетизации под ваш рынок и нишу.",
        ],
        "economy_efficiency": [
            "Экономия бюджета: не нужно инвестировать в долгую custom-разработку.",
            "Экономия времени: ключевые сценарии уже реализованы — регистрация, размещение объявлений, поиск, оформление заказа.",
            "Снижение операционных расходов: автоматизация модерации и обработки заявок.",
            "Быстрее выход на рынок: можно запустить MVP и начать тестировать спрос в короткие сроки.",
        ],
        "competitive_advantages": [
            "Гибкая архитектура: легко адаптировать под B2C, C2C и нишевые вертикали.",
            "Масштабируемая основа для роста ассортимента и аудитории.",
            "Удобный путь пользователя: от публикации товара до сделки.",
            "Инструменты доверия: профили, рейтинги, отзывы, модерация.",
            "Возможность поэтапного развития: от MVP до полноценной торговой платформы.",
        ],
        "image": "images/Shmavito/shmavito_white.jpg",
        "gallery": ["images/Shmavito/shmavito_white.jpg"],
    },
    {
        "id": 3,
        "title": "Платформа для автоматизации",
        "short_description": (
            "Pusplexity — AI-платформа для автоматизации работы с изображениями "
            "и документами в Telegram и веб-интерфейсе."
        ),
        "full_description": (
            "Pusplexity — это AI-платформа для автоматизации работы с изображениями "
            "и документами в Telegram и через веб-интерфейс. Сервис помогает бизнесу "
            "быстрее создавать визуальный контент, обрабатывать фото и получать ответы "
            "из внутренних документов без сложных инструментов и долгого обучения команды."
        ),
        "tangible_benefit": [
            "Сокращение времени выполнения типовых задач с изображениями и документами: в среднем на 30-55%.",
            "Снижение затрат на ручную обработку контента: ориентировочно на 20-35%.",
            "Ускорение доступа к внутренним знаниям компании: ответы по документам в 2-4 раза быстрее.",
        ],
        "business_benefits": [
            "Экономия времени сотрудников: рутинные задачи по изображениям и документам выполняются в чате за минуты.",
            "Снижение затрат на производство контента: меньше ручной работы дизайнеров и подрядчиков на типовые задачи.",
            "Быстрый доступ к знаниям компании: загрузка PDF/Word/Excel и ответы по базе документов в формате вопрос-ответ.",
            "Рост скорости запуска маркетинговых материалов: генерация и редактирование изображений по текстовому запросу.",
            "Удобное внедрение: работа через привычные каналы (Telegram + Web), без сложного интерфейса.",
            "Контроль и безопасность: авторизация пользователей, лимиты, защита сессий и стабильная серверная архитектура.",
        ],
        "key_advantage": (
            "Pusplexity превращает долгие и технически сложные процессы в простой диалог: "
            "пишете задачу обычным языком — получаете готовый результат, сокращая операционные "
            "издержки и ускоряя бизнес-процессы."
        ),
        "image": "images/Pusplexity/Pusplexity_1.jpg",
        "gallery": [
            "images/Pusplexity/Pusplexity_1.jpg",
            "images/Pusplexity/Pusplexity_2.jpg",
        ],
    },
    {
        "id": 4,
        "title": "Разработка корпоративного сайта",
        "short_description": (
            "AboutMeSite — корпоративный сайт-витрина с кейсами, понятной структурой "
            "услуг и быстрым входом в коммуникацию с клиентом."
        ),
        "full_description": (
            "AboutMeSite собран как корпоративная digital-витрина: на главной странице "
            "сформулировано ценностное предложение, в кейсах показаны реальные проекты, "
            "а на странице обратной связи клиент может быстро оставить заявку. "
            "Сайт помогает презентовать экспертизу и конвертировать интерес в диалог. "
            "Отдельно на сайте также представлен другой проект — онлайн-консультант "
            "ПетлиБот."
        ),
        "tangible_benefit": [
            "Сокращение времени до первого контакта с потенциальным клиентом: в среднем на 20-35%.",
            "Рост конверсии посетителя в заявку за счет четкой структуры оффера и кейсов: ориентировочно на 12-22%.",
            "Снижение объема повторных уточнений со стороны клиентов: в среднем на 15-25%.",
        ],
        "image": "images/AboutMeSite/AboutMeSite.jpg",
        "gallery": ["images/AboutMeSite/AboutMeSite.jpg"],
    },
    {
        "id": 5,
        "title": "AI-ассистент для поддержки клиентов",
        "short_description": (
            "ПетлиБот — AI-ассистент поддержки для консультаций по проектам сайта "
            "с памятью диалога и RAG-базой."
        ),
        "full_description": (
            "ПетлиБот — это AI-ассистент поддержки, встроенный в сайт для быстрых "
            "консультаций по кейсам и услугам. Он просит пользователя представиться, "
            "сохраняет контекст по email и отвечает на основе RAG-базы. "
            "Безопасность обеспечивается серверной валидацией запросов, ограничением "
            "длины сообщений, маскированием email в публичных логах и фильтрацией "
            "вопросов только в рамках проекта. "
            "Для базы знаний можно загружать собственные данные через папку `rag_source`, "
            "после чего они автоматически индексируются в ChromaDB и используются в ответах. "
            "Для генерации используется экономичная модель OpenAI, что помогает держать "
            "стоимость эксплуатации под контролем при ежедневных консультациях. "
            "Преимущества для бизнеса: снижение нагрузки на первую линию коммуникации, "
            "ускорение обработки типовых вопросов, рост конверсии из посетителя в заявку "
            "и более стабильное качество первичной консультации."
        ),
        "tangible_benefit": [
            "Сокращение среднего времени ответа клиенту: в среднем на 6-15 минут.",
            "Снижение нагрузки на первую линию поддержки: ориентировочно на 1-2 штатные единицы при потоке типовых запросов.",
            "Рост удовлетворенности пользователей за счет скорости и доступности 24/7: в среднем на 12-20%.",
        ],
        "image": "images/AboutMeSite/Petlibot.jpg",
        "gallery": ["images/AboutMeSite/Petlibot.jpg"],
    },
]


def setup_logging(app: Flask) -> None:
    # Reset handlers to avoid duplicated logs on app reloads.
    app.logger.handlers.clear()
    app.logger.setLevel(getattr(logging, app.config["LOG_LEVEL"], logging.INFO))
    app.logger.propagate = False

    log_format = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console_handler = None
    if app.config["LOG_TO_CONSOLE"]:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        console_handler.setLevel(app.logger.level)
        app.logger.addHandler(console_handler)

    log_file = app.config["LOG_FILE"]
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    file_handler = None
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=app.config["LOG_MAX_BYTES"],
            backupCount=app.config["LOG_BACKUP_COUNT"],
            encoding="utf-8",
        )
        file_handler.setFormatter(log_format)
        file_handler.setLevel(app.logger.level)
        app.logger.addHandler(file_handler)
    except (PermissionError, OSError):
        app.logger.warning(
            "Не удалось инициализировать файловый лог '%s'. Логи будут писатьcя только в консоль.",
            log_file,
        )

    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(app.logger.level)
    werkzeug_logger.handlers.clear()
    if console_handler:
        werkzeug_logger.addHandler(console_handler)
    if file_handler:
        werkzeug_logger.addHandler(file_handler)

    app.logger.info("Логирование инициализировано. Уровень: %s", app.config["LOG_LEVEL"])


def _mask_email(value: str) -> str:
    if not value:
        return "***"
    if "@" not in value:
        return "***"
    name, domain = value.split("@", 1)
    return f"{name[:1]}***@{domain}"


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _chat_session_key(email: str) -> str:
    return f"{email}_{datetime.utcnow().strftime('%Y%m%d')}"


def _is_memory_clear_command(text: str) -> bool:
    normalized = (text or "").strip().lower()
    return normalized in {"очистить память", "сбросить память", "/clear_memory", "/clear"}


def _is_in_site_scope(text: str) -> bool:
    if not text:
        return False
    normalized = text.lower()
    scope_synonyms = {
        "site": ["сайт", "aboutme", "about me", "петлин", "дмитрий", "услуг", "кейс", "проект"],
        "chat": ["чат", "консультант", "памят", "очист", "petlibot", "петлибот"],
        "telegram": ["telegram", "телеграм", "телега", "тг", "бот"],
        "nutribot": ["nutribot", "нутрибот", "нутрибoт"],
        "shmavito": ["shmavito", "шмавито", "шм авито", "авито-подоб", "маркетплейс"],
        "pusplexity": [
            "pusplexity",
            "пусплексити",
            "пусплекси",
            "пусплек",
            "пусплексити",
            "пусплекс",
            "пусплекстити",
        ],
    }
    markers = [item for group in scope_synonyms.values() for item in group]
    return any(marker in normalized for marker in markers)


def _is_in_site_scope_with_history(current_text: str, history_questions: list[str]) -> bool:
    if _is_in_site_scope(current_text):
        return True
    if not history_questions:
        return False
    # Use recent context so short follow-up questions keep conversation topic.
    recent_history = " ".join((question or "") for question in history_questions[-3:])
    return _is_in_site_scope(f"{recent_history} {current_text}".strip())


def _is_project_list_request(text: str) -> bool:
    normalized = (text or "").lower()
    list_markers = [
        "какие",
        "каких",
        "в каких",
        "перечисли",
        "список",
        "проекты",
        "проектах",
        "кейсы",
    ]
    return any(marker in normalized for marker in list_markers)


def _is_project_overview_request(text: str) -> bool:
    normalized = (text or "").lower()
    overview_markers = ["что делают", "чем полез", "могут помочь", "подойдут", "расскажи про проекты"]
    return any(marker in normalized for marker in overview_markers)


def _is_openai_version_request(text: str) -> bool:
    normalized = (text or "").lower()
    version_markers = ["верси", "модел", "openai", "gpt", "какая"]
    return any(marker in normalized for marker in version_markers)


def _extract_models_from_rag_context(context_chunks: list[str]) -> dict[str, str]:
    model_patterns = [
        r"gpt-[a-z0-9.-]+",
        r"text-embedding-[a-z0-9.-]+",
    ]
    found: list[str] = []
    for chunk in context_chunks:
        chunk_lower = (chunk or "").lower()
        for pattern in model_patterns:
            for match in re.findall(pattern, chunk_lower):
                if match not in found:
                    found.append(match)

    categories = {
        "Текст/чат": "",
        "Эмбеддинги": "",
    }
    for model in found:
        if model.startswith("text-embedding-") and not categories["Эмбеддинги"]:
            categories["Эмбеддинги"] = model
        if model.startswith("gpt-") and not categories["Текст/чат"]:
            categories["Текст/чат"] = model
    return categories


def _build_openai_versions_answer(user_question: str, rag_context: list[str]) -> str:
    categories = _extract_models_from_rag_context(rag_context)
    if any(categories.values()):
        lines = ["По Pusplexity в базе знаний указаны такие модели OpenAI:"]
        for label, value in categories.items():
            if value:
                lines.append(f"- {label}: `{value}`")
        return "\n".join(lines)
    return (
        "По Pusplexity в текущем контексте нет точного списка моделей OpenAI. "
        "Добавьте в `rag_source` файл с явными значениями (например, OPENAI_TEXT_MODEL, "
        "OPENAI_EMBEDDING_MODEL), и я буду отвечать точным коротким списком."
    )


def _case_text(case: dict) -> str:
    parts = [
        case.get("title", ""),
        case.get("short_description", ""),
        case.get("full_description", ""),
        " ".join(case.get("business_benefits", []) if isinstance(case.get("business_benefits"), list) else []),
    ]
    return " ".join(part.lower() for part in parts if isinstance(part, str))


def _projects_for_topic(text: str) -> list[dict]:
    normalized = (text or "").lower()
    if any(marker in normalized for marker in ["телега", "телеграм", "telegram", "тг"]):
        return [case for case in CASES if "telegram" in _case_text(case) or "телеграм" in _case_text(case)]
    if any(marker in normalized for marker in ["трениров", "питани", "фитнес", "wellness", "здоров"]):
        return [
            case
            for case in CASES
            if any(marker in _case_text(case) for marker in ["трениров", "питани", "фитнес", "wellness"])
        ]
    if "проек" in normalized or "кейс" in normalized:
        return CASES
    return []


def _project_brief(case: dict) -> str:
    short_description = (case.get("short_description") or "").strip()
    if short_description:
        return short_description
    full_description = (case.get("full_description") or "").strip()
    if not full_description:
        return "Решение под бизнес-задачи клиента."
    return full_description[:180].rstrip() + ("..." if len(full_description) > 180 else "")


def _is_multi_project_interest_request(text: str) -> bool:
    normalized = (text or "").lower()
    interest_markers = ["интерес", "заинтерес", "хочу", "расскажи", "подробн", "сравни"]
    project_markers = [
        "pusplexity",
        "пусплекс",
        "petlibot",
        "петлибот",
        "nutribot",
        "нутрибот",
        "шмавито",
        "aboutmesite",
    ]
    has_interest = any(marker in normalized for marker in interest_markers)
    project_hits = sum(1 for marker in project_markers if marker in normalized)
    return has_interest and project_hits >= 2


def _build_multi_project_interest_answer(text: str) -> str:
    normalized = (text or "").lower()
    selected = []
    marker_map = [
        ("pusplexity", ["pusplexity", "пусплекс"]),
        ("petlibot", ["petlibot", "петлибот"]),
        ("nutribot", ["nutribot", "нутрибот"]),
        ("шмавито", ["шмавито"]),
        ("aboutmesite", ["aboutmesite"]),
    ]

    for case in CASES:
        case_text = _case_text(case)
        for _, markers in marker_map:
            if any(marker in normalized for marker in markers) and any(
                marker in case_text for marker in markers
            ):
                if case not in selected:
                    selected.append(case)
                break

    if len(selected) < 2:
        return ""

    lines = ["Отличный выбор. Коротко по этим проектам:"]
    for case in selected:
        lines.append(f"- {case['title']}: {_project_brief(case)}")
    lines.append("Если хотите, сравню их по срокам запуска, бюджету и бизнес-эффекту.")
    return "\n".join(lines)


def _is_petlibot_features_request(text: str) -> bool:
    normalized = (text or "").lower()
    petlibot_markers = ["петлибот", "petlibot"]
    feature_markers = ["функционал", "возможност", "умеет", "что делает", "расскажи о"]
    return any(marker in normalized for marker in petlibot_markers) and any(
        marker in normalized for marker in feature_markers
    )


def _build_petlibot_features_answer() -> str:
    return (
        "ПетлиБот на сайте умеет:\n"
        "- Консультировать по проектам и кейсам сайта.\n"
        "- Работать с контекстом через RAG-базу (данные из `rag_source`).\n"
        "- Запоминать последние 10 вопросов пользователя по email.\n"
        "- Напоминать, на каком вопросе остановились в прошлой беседе.\n"
        "- Очищать память по кнопке или командой «очистить память».\n"
        "- Ограничивать длину сообщения пользователя до 250 символов.\n"
        "- Вести лог диалога с отображением на публичной странице логов (email маскируется).\n"
        "- Показывать индикатор «Подготавливаю ответ...» во время генерации."
    )


def _is_pusplexity_overview_request(text: str) -> bool:
    normalized = (text or "").lower()
    project_markers = ["pusplexity", "пусплекс", "пусплекси", "пусплексити"]
    intent_markers = ["что", "скажи", "расскажи", "о ", "функционал", "возможност", "для чего"]
    return any(marker in normalized for marker in project_markers) and any(
        marker in normalized for marker in intent_markers
    )


def _build_pusplexity_overview_answer() -> str:
    return (
        "Pusplexity — это AI-платформа для автоматизации работы с изображениями и документами "
        "через Telegram и веб-интерфейс.\n"
        "Ключевые возможности:\n"
        "- Генерация и обработка изображений по текстовым запросам.\n"
        "- Быстрый поиск ответов по базе документов (RAG-сценарии).\n"
        "- Работа в удобных каналах: Telegram и Web.\n"
        "- Ускорение типовых задач команды и снижение ручной нагрузки.\n"
        "Если хотите, могу сравнить Pusplexity с ПетлиБотом по задачам, стоимости и срокам запуска."
    )


def _is_case_overview_request(text: str) -> bool:
    normalized = (text or "").lower()
    intent_markers = [
        "что у вас за",
        "что скажешь",
        "расскажи",
        "что за",
        "что это",
        "что такое",
        "какой",
        "о проекте",
        "о кейсе",
        "какие возможности",
        "для чего",
    ]
    return any(marker in normalized for marker in intent_markers)


def _case_markers(case: dict) -> list[str]:
    title = (case.get("title") or "").lower()
    markers = [title]
    if "nutribot" in title:
        markers.extend(
            [
                "nutribot",
                "nutrib",
                "нутрибот",
                "нутриб",
                "нутрибoт",
                "нутрибot",
            ]
        )
    if "шмавито" in title:
        markers.extend(["шмавито", "шмавит", "shmavito", "shmavit"])
    if "платформа для автоматизации" in title or "pusplexity" in _case_text(case):
        markers.extend(
            [
                "pusplexity",
                "pusplex",
                "пусплекс",
                "пусплекси",
                "пусплексити",
                "пусплекст",
            ]
        )
    if "корпоративного сайта" in title:
        markers.extend(
            ["aboutmesite", "about me site", "aboutme", "корпоративный сайт", "сайт-витрина"]
        )
    if "ai-ассистент" in title:
        markers.extend(["петлибот", "петлибота", "petlibot", "ai-ассистент", "ассистент"])
    return markers


def _match_case_for_request(text: str) -> dict | None:
    normalized = (text or "").lower()
    for case in CASES:
        if any(marker and marker in normalized for marker in _case_markers(case)):
            return case
    return None


def _build_case_overview_answer(case: dict) -> str:
    lines = [f"{case['title']} — {_project_brief(case)}"]
    tangible = case.get("tangible_benefit") or []
    if tangible:
        lines.append("Ощутимая выгода:")
        for item in tangible[:3]:
            lines.append(f"- {item}")
    lines.append("Если хотите, могу дать сравнение с другими кейсами под вашу задачу.")
    return "\n".join(lines)


def _find_mentioned_cases(text: str) -> list[dict]:
    normalized = (text or "").lower()
    matched = []
    for case in CASES:
        if any(marker and marker in normalized for marker in _case_markers(case)):
            matched.append(case)
    return matched


def _is_unclear_project_question(text: str) -> bool:
    normalized = (text or "").lower().strip()
    if not normalized:
        return True
    clear_markers = [
        "что",
        "как",
        "зачем",
        "какие",
        "какой",
        "возможност",
        "функционал",
        "цена",
        "стоим",
        "срок",
        "интеграц",
        "внедр",
        "поможет",
    ]
    if any(marker in normalized for marker in clear_markers):
        return False
    return len(normalized.split()) <= 5


def _mask_ip(value: str) -> str:
    if not value:
        return "unknown"
    if ":" in value:
        return re.sub(r":[0-9a-fA-F]{1,4}$", ":****", value)
    parts = value.split(".")
    if len(parts) == 4:
        return ".".join(parts[:3] + ["***"])
    return "***"


def validate_security_config(app: Flask) -> None:
    if app.config["DEBUG"]:
        app.logger.warning("DEBUG mode is enabled. Disable in production.")
        return

    secret_key = app.config.get("SECRET_KEY") or ""
    default_username = (app.config.get("DEFAULT_ADMIN_USERNAME") or "").lower()
    default_password = app.config.get("DEFAULT_ADMIN_PASSWORD") or ""

    if len(secret_key) < 32 or "change-me" in secret_key.lower():
        raise RuntimeError("Insecure SECRET_KEY for production.")
    if default_username == "admin" and default_password == "admin123":
        raise RuntimeError("Default admin credentials are forbidden in production.")
    if len(default_password) < 12:
        raise RuntimeError("Admin password must be at least 12 characters in production.")


def register_request_logging(app: Flask) -> None:
    @app.before_request
    def log_request_start():
        g.request_started_at = datetime.utcnow()
        app.logger.info(
            "Request started: method=%s path=%s ip=%s",
            request.method,
            request.path,
            _mask_ip(request.remote_addr),
        )

    @app.after_request
    def log_request_end(response):
        started_at = getattr(g, "request_started_at", datetime.utcnow())
        duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)
        app.logger.info(
            "Request finished: method=%s path=%s status=%s duration_ms=%s",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )
        return response


def register_security_headers(app: Flask) -> None:
    if not app.config["SECURITY_HEADERS_ENABLED"]:
        return

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' data:; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        )
        if request.headers.get("X-Forwarded-Proto", "").lower() == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        return response


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def handle_404(error):
        app.logger.warning("404 Not Found: path=%s ip=%s", request.path, _mask_ip(request.remote_addr))
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def handle_500(error):
        app.logger.exception("500 Internal Server Error: path=%s", request.path)
        return render_template("500.html"), 500


def create_default_admin(app: Flask) -> None:
    with app.app_context():
        db.create_all()
        default_admin = Admin.query.filter_by(
            username=app.config["DEFAULT_ADMIN_USERNAME"]
        ).first()
        if not default_admin:
            default_admin = Admin(username=app.config["DEFAULT_ADMIN_USERNAME"])
            default_admin.set_password(app.config["DEFAULT_ADMIN_PASSWORD"])
            db.session.add(default_admin)
            db.session.commit()
            app.logger.info("Создан дефолтный администратор из переменных окружения.")


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.login_view = "admin_login"
    login_manager.login_message = "Для доступа к админ-панели выполните вход."
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "strong"

    setup_logging(app)
    validate_security_config(app)
    register_request_logging(app)
    register_security_headers(app)
    register_error_handlers(app)
    create_default_admin(app)
    rag_service = None
    openai_client = None

    if app.config["OPENAI_API_KEY"]:
        openai_client = OpenAI(api_key=app.config["OPENAI_API_KEY"])
        try:
            rag_service = RagService(app.config)
            indexed_count = rag_service.index_source_documents()
            if indexed_count:
                app.logger.info("RAG auto-sync: добавлено новых документов: %s", indexed_count)
            else:
                app.logger.info("RAG auto-sync: новых документов не найдено.")
        except Exception as error:
            app.logger.exception("Ошибка инициализации RAG-сервиса: %s", error)
            rag_service = None

    @login_manager.user_loader
    def load_user(user_id: str):
        return Admin.query.get(int(user_id))

    @app.context_processor
    def inject_globals():
        return {"cases_preview": CASES[:5], "current_year": datetime.utcnow().year}

    @app.route("/")
    def home():
        return render_template("index.html", cases=CASES[:5])

    @app.route("/cases")
    def cases():
        return render_template("cases.html", cases=CASES)

    @app.route("/cases/<int:case_id>")
    def case_detail(case_id: int):
        case = next((item for item in CASES if item["id"] == case_id), None)
        if not case:
            flash("Кейс не найден.", "danger")
            return redirect(url_for("cases"))
        return render_template("case_detail.html", case=case)

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        form = ContactForm()
        if form.validate_on_submit():
            new_request = ContactRequest(
                name=form.name.data,
                email=form.email.data,
                phone=form.phone.data,
                subject=form.subject.data,
                message=form.message.data,
            )
            db.session.add(new_request)
            db.session.commit()
            app.logger.info(
                "Новая заявка: name=%s, email=%s, ip=%s",
                form.name.data,
                form.email.data if app.config["PII_LOGGING_ENABLED"] else _mask_email(form.email.data),
                request.remote_addr if app.config["PII_LOGGING_ENABLED"] else _mask_ip(request.remote_addr),
            )
            flash("Спасибо! Заявка успешно отправлена.", "success")
            return redirect(url_for("contact"))
        return render_template("contact.html", form=form)

    @app.route("/api/chat/history-status")
    @csrf.exempt
    def chat_history_status():
        email = _normalize_email(request.args.get("email", ""))
        if not email:
            return jsonify({"has_history": False})

        last_question = (
            ChatMemory.query.filter_by(email=email)
            .order_by(ChatMemory.created_at.desc())
            .first()
        )
        if not last_question:
            return jsonify({"has_history": False})

        return jsonify(
            {
                "has_history": True,
                "last_question": last_question.question,
                "message": (
                    "В прошлой беседе мы остановились на вопросе: "
                    f"\"{last_question.question}\". Продолжим по этой теме "
                    "или хотите очистить память?"
                ),
            }
        )

    @app.route("/api/chat/clear-memory", methods=["POST"])
    @csrf.exempt
    def chat_clear_memory():
        payload = request.get_json(silent=True) or {}
        email = _normalize_email(payload.get("email", ""))
        if not email:
            return jsonify({"ok": False, "error": "Укажите email."}), 400

        ChatMemory.query.filter_by(email=email).delete()
        db.session.commit()
        return jsonify({"ok": True, "message": "Память чата очищена."})

    @app.route("/api/chat", methods=["POST"])
    @csrf.exempt
    def chat():
        payload = request.get_json(silent=True) or {}
        name = (payload.get("name") or "").strip()
        email = _normalize_email(payload.get("email", ""))
        message = (payload.get("message") or "").strip()

        if not name or not email:
            return jsonify({"ok": False, "error": "Введите имя и email."}), 400

        if len(message) > app.config["CHAT_MAX_MESSAGE_LENGTH"]:
            return jsonify(
                {
                    "ok": False,
                    "error": (
                        f"Превышен размер сообщения. Допустимо не более "
                        f"{app.config['CHAT_MAX_MESSAGE_LENGTH']} символов."
                    ),
                }
            ), 400

        if _is_memory_clear_command(message):
            ChatMemory.query.filter_by(email=email).delete()
            db.session.commit()
            return jsonify({"ok": True, "answer": "Память очищена. Можем начать заново."})

        memory_rows = (
            ChatMemory.query.filter_by(email=email)
            .order_by(ChatMemory.created_at.desc())
            .limit(app.config["CHAT_MEMORY_LIMIT"])
            .all()
        )
        memory_questions = [row.question for row in reversed(memory_rows)]

        mentioned_cases = _find_mentioned_cases(message)
        has_project_context = bool(mentioned_cases) or _is_in_site_scope_with_history(
            message, memory_questions
        )

        if not has_project_context:
            return jsonify(
                {
                    "ok": True,
                    "answer": (
                        "Я могу проконсультировать вас только по проектам с этого сайта. "
                        "Уточните, пожалуйста, свой запрос."
                    ),
                }
            )

        if mentioned_cases and _is_unclear_project_question(message):
            case_titles = ", ".join(case["title"] for case in mentioned_cases[:3])
            fallback_answer = (
                f"Уточните, пожалуйста, что именно по проекту(ам) {case_titles} вам важно: "
                "функционал, сроки запуска, стоимость, интеграции или ожидаемый бизнес-эффект?"
            )
            if openai_client:
                try:
                    clarify_response = openai_client.responses.create(
                        model=app.config["OPENAI_CHAT_MODEL"],
                        max_output_tokens=160,
                        reasoning={"effort": app.config["OPENAI_REASONING_EFFORT"]},
                        input=[
                            {
                                "role": "system",
                                "content": (
                                    "Ты консультант по проектам сайта. Пользователь упомянул проект(ы), "
                                    "но вопрос неясен. Сформулируй один короткий уточняющий вопрос, "
                                    "вежливо и по-деловому, без лишних деталей."
                                ),
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"Проекты: {case_titles}. "
                                    f"Фраза пользователя: {message}"
                                ),
                            },
                        ],
                    )
                    clarify_text = (clarify_response.output_text or "").strip()
                    return jsonify({"ok": True, "answer": clarify_text or fallback_answer})
                except Exception:
                    return jsonify({"ok": True, "answer": fallback_answer})
            return jsonify({"ok": True, "answer": fallback_answer})

        if len(mentioned_cases) == 1:
            return jsonify({"ok": True, "answer": _build_case_overview_answer(mentioned_cases[0])})

        if _is_project_list_request(message) and any(
            marker in message.lower() for marker in ["телега", "телеграм", "telegram", "тг"]
        ):
            matched_projects = _projects_for_topic(message)
            if matched_projects:
                answer_lines = ["Проекты с интеграцией Telegram на этом сайте:"]
                for item in matched_projects:
                    answer_lines.append(f"- {item['title']}")
                answer_lines.append("Если хотите, кратко сравню их по задачам и результатам.")
                return jsonify({"ok": True, "answer": "\n".join(answer_lines)})

        if _is_project_overview_request(message) or _is_project_list_request(message):
            matched_projects = _projects_for_topic(message)
            if len(matched_projects) > 1:
                answer_lines = ["Вот проекты, которые подходят под ваш запрос:"]
                for item in matched_projects:
                    answer_lines.append(f"- {item['title']}: {_project_brief(item)}")
                answer_lines.append("Могу сузить до 1-2 лучших вариантов под вашу конкретную задачу.")
                return jsonify({"ok": True, "answer": "\n".join(answer_lines)})

        if _is_multi_project_interest_request(message):
            instant_answer = _build_multi_project_interest_answer(message)
            if instant_answer:
                return jsonify({"ok": True, "answer": instant_answer})

        if _is_petlibot_features_request(message):
            return jsonify({"ok": True, "answer": _build_petlibot_features_answer()})

        if _is_pusplexity_overview_request(message):
            return jsonify({"ok": True, "answer": _build_pusplexity_overview_answer()})

        if _is_case_overview_request(message):
            matched_case = _match_case_for_request(message)
            if matched_case:
                return jsonify({"ok": True, "answer": _build_case_overview_answer(matched_case)})

        rag_context = []
        if rag_service:
            try:
                rag_context = rag_service.search(message)
            except Exception as error:
                app.logger.exception("Ошибка поиска в RAG: %s", error)

        if _is_openai_version_request(message):
            return jsonify({"ok": True, "answer": _build_openai_versions_answer(message, rag_context)})

        system_prompt = (
            "Ты ПетлиБот, консультант сайта с кейсами и услугами по разработке, AI и автоматизации. "
            "Отвечай вежливо, корректно, по делу и с легким акцентом на пользу услуг сайта. "
            "Если контекста недостаточно, мягко предложи уточнить детали проекта. "
            "Не упоминай внутреннюю архитектуру (RAG, ChromaDB, индексацию, документы, базы знаний) "
            "и не предлагай сценарии, которых нет в интерфейсе этого чат-бота."
        )

        user_prompt_parts = [
            f"Пользователь: {name} ({email})",
            f"Текущий вопрос: {message}",
        ]
        if memory_questions:
            user_prompt_parts.append(
                "Последние вопросы пользователя:\n- " + "\n- ".join(memory_questions)
            )
        if rag_context:
            user_prompt_parts.append("RAG-контекст:\n- " + "\n- ".join(rag_context))
        user_prompt = "\n\n".join(user_prompt_parts)

        answer_text = "Сейчас не удалось получить ответ. Попробуйте еще раз через минуту."
        if openai_client:
            try:
                request_payload = dict(
                    model=app.config["OPENAI_CHAT_MODEL"],
                    max_output_tokens=app.config["OPENAI_MAX_OUTPUT_TOKENS"],
                    reasoning={"effort": app.config["OPENAI_REASONING_EFFORT"]},
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                # request_payload["temperature"] = app.config["OPENAI_TEMPERATURE"]
                response = openai_client.responses.create(**request_payload)
                answer_text = (response.output_text or "").strip() or answer_text
            except BadRequestError as error:
                error_text = str(error)
                if "Unsupported parameter: 'temperature'" in error_text:
                    app.logger.warning(
                        "Модель %s не поддерживает temperature, повтор без параметра.",
                        app.config["OPENAI_CHAT_MODEL"],
                    )
                    request_payload.pop("temperature", None)
                    response = openai_client.responses.create(**request_payload)
                    answer_text = (response.output_text or "").strip() or answer_text
                else:
                    app.logger.exception("Ошибка OpenAI API: %s", error)
            except Exception as error:
                app.logger.exception("Ошибка OpenAI API: %s", error)

        memory_entry = ChatMemory(email=email, question=message)
        db.session.add(memory_entry)
        db.session.flush()

        memory_count = ChatMemory.query.filter_by(email=email).count()
        max_memory = app.config["CHAT_MEMORY_LIMIT"]
        if memory_count > max_memory:
            obsolete = (
                ChatMemory.query.filter_by(email=email)
                .order_by(ChatMemory.created_at.asc())
                .limit(memory_count - max_memory)
                .all()
            )
            for row in obsolete:
                db.session.delete(row)

        session_key = _chat_session_key(email)
        session = ChatLogSession.query.filter_by(session_key=session_key).first()
        if not session:
            session = ChatLogSession(
                session_key=session_key,
                name=name,
                email_masked=_mask_email(email),
            )
            db.session.add(session)
            db.session.flush()

        last_order = (
            db.session.query(db.func.max(ChatLogMessage.order_idx))
            .filter_by(session_key=session_key)
            .scalar()
        ) or 0
        db.session.add(
            ChatLogMessage(
                session_key=session_key,
                role="user",
                text=message,
                order_idx=last_order + 1,
            )
        )
        db.session.add(
            ChatLogMessage(
                session_key=session_key,
                role="assistant",
                text=answer_text,
                order_idx=last_order + 2,
            )
        )
        db.session.commit()

        return jsonify({"ok": True, "answer": answer_text})

    @app.route("/logs")
    def logs():
        selected_date_raw = (request.args.get("date") or "").strip()
        try:
            selected_date = (
                datetime.strptime(selected_date_raw, "%Y-%m-%d").date()
                if selected_date_raw
                else datetime.utcnow().date()
            )
        except ValueError:
            selected_date = datetime.utcnow().date()

        day_start = datetime.combine(selected_date, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        all_sessions = ChatLogSession.query.order_by(ChatLogSession.created_at.desc()).all()
        available_dates = []
        seen_dates = set()
        for session in all_sessions:
            day_label = session.created_at.date().isoformat()
            if day_label not in seen_dates:
                seen_dates.add(day_label)
                available_dates.append(day_label)

        sessions = (
            ChatLogSession.query.filter(
                ChatLogSession.created_at >= day_start,
                ChatLogSession.created_at < day_end,
            )
            .order_by(ChatLogSession.created_at.desc())
            .all()
        )
        session_keys = [session.session_key for session in sessions]
        messages = []
        if session_keys:
            messages = (
                ChatLogMessage.query.filter(ChatLogMessage.session_key.in_(session_keys))
                .order_by(ChatLogMessage.session_key.desc(), ChatLogMessage.order_idx.asc())
                .all()
            )
        grouped_messages = {}
        for message in messages:
            grouped_messages.setdefault(message.session_key, []).append(message)

        user_blocks = {}
        for session in sessions:
            block_key = session.email_masked
            if block_key not in user_blocks:
                user_blocks[block_key] = {
                    "name": session.name,
                    "email_masked": session.email_masked,
                    "sessions": [],
                }
            user_blocks[block_key]["sessions"].append(session)

        return render_template(
            "logs.html",
            sessions=sessions,
            grouped_messages=grouped_messages,
            selected_date=selected_date.isoformat(),
            available_dates=available_dates,
            user_blocks=list(user_blocks.values()),
        )

    @app.route("/admin/login", methods=["GET", "POST"])
    @limiter.limit("5 per minute; 20 per hour")
    def admin_login():
        if current_user.is_authenticated:
            return redirect(url_for("admin_dashboard"))

        form = AdminLoginForm()
        if form.validate_on_submit():
            admin = Admin.query.filter_by(username=form.username.data).first()
            if admin and admin.check_password(form.password.data):
                login_user(admin)
                app.logger.info("Администратор %s вошёл в систему.", admin.username)
                flash("Вход выполнен успешно.", "success")
                return redirect(url_for("admin_dashboard"))
            flash("Неверный логин или пароль.", "danger")
        return render_template("admin_login.html", form=form)

    @app.route("/admin/logout")
    @login_required
    def admin_logout():
        app.logger.info("Администратор %s вышел из системы.", current_user.username)
        logout_user()
        flash("Вы вышли из админ-панели.", "info")
        return redirect(url_for("home"))

    @app.route("/admin")
    @login_required
    def admin_dashboard():
        requests_data = ContactRequest.query.order_by(ContactRequest.created_at.desc()).all()
        mark_form = EmptyForm()
        delete_form = EmptyForm()
        return render_template(
            "admin_dashboard.html",
            requests_data=requests_data,
            mark_form=mark_form,
            delete_form=delete_form,
        )

    @app.route("/admin/mark-read/<int:request_id>", methods=["POST"])
    @login_required
    def mark_read(request_id: int):
        form = EmptyForm()
        if form.validate_on_submit():
            item = ContactRequest.query.get_or_404(request_id)
            item.is_read = True
            db.session.commit()
            app.logger.info("Заявка #%s отмечена как прочитанная.", request_id)
            flash("Заявка отмечена как прочитанная.", "success")
        else:
            flash("Некорректный запрос.", "danger")
        return redirect(url_for("admin_dashboard"))

    @app.route("/admin/delete/<int:request_id>", methods=["POST"])
    @login_required
    def delete_request(request_id: int):
        form = EmptyForm()
        if form.validate_on_submit():
            item = ContactRequest.query.get_or_404(request_id)
            db.session.delete(item)
            db.session.commit()
            app.logger.info("Заявка #%s удалена.", request_id)
            flash("Заявка удалена.", "info")
        else:
            flash("Некорректный запрос.", "danger")
        return redirect(url_for("admin_dashboard"))

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(
        debug=application.config["DEBUG"],
        host=application.config["HOST"],
        port=application.config["PORT"],
    )
