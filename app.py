import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

from flask import Flask, flash, g, redirect, render_template, request, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import EmailField, PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp

from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


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
        "short_description": "Имиджевый сайт компании с современным дизайном и CMS.",
        "full_description": (
            "Собрали корпоративный сайт с акцентом на бренд, SEO-структуру, "
            "удобную навигацию и быстрый доступ к контактам и услугам."
        ),
        "image": "images/case4.svg",
    },
    {
        "id": 5,
        "title": "AI-ассистент для поддержки клиентов",
        "short_description": "AI-помощник для ответов на частые вопросы 24/7.",
        "full_description": (
            "Внедрили AI-ассистента с базой знаний компании, эскалацией сложных кейсов "
            "оператору и аналитикой качества ответов."
        ),
        "image": "images/case5.svg",
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

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    console_handler.setLevel(app.logger.level)
    app.logger.addHandler(console_handler)

    log_file = app.config["LOG_FILE"]
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=app.config["LOG_MAX_BYTES"],
        backupCount=app.config["LOG_BACKUP_COUNT"],
        encoding="utf-8",
    )
    file_handler.setFormatter(log_format)
    file_handler.setLevel(app.logger.level)
    app.logger.addHandler(file_handler)

    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(app.logger.level)
    werkzeug_logger.handlers.clear()
    werkzeug_logger.addHandler(console_handler)
    werkzeug_logger.addHandler(file_handler)

    app.logger.info("Логирование инициализировано. Уровень: %s", app.config["LOG_LEVEL"])


def register_request_logging(app: Flask) -> None:
    @app.before_request
    def log_request_start():
        g.request_started_at = datetime.utcnow()
        app.logger.info(
            "Request started: method=%s path=%s ip=%s user_agent=%s",
            request.method,
            request.path,
            request.remote_addr,
            request.user_agent.string,
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


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def handle_404(error):
        app.logger.warning("404 Not Found: path=%s ip=%s", request.path, request.remote_addr)
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

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "admin_login"
    login_manager.login_message = "Для доступа к админ-панели выполните вход."
    login_manager.login_message_category = "warning"

    setup_logging(app)
    register_request_logging(app)
    register_error_handlers(app)
    create_default_admin(app)

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
                form.email.data,
                request.remote_addr,
            )
            flash("Спасибо! Заявка успешно отправлена.", "success")
            return redirect(url_for("contact"))
        return render_template("contact.html", form=form)

    @app.route("/admin/login", methods=["GET", "POST"])
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
