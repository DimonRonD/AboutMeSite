import logging
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, url_for
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
        "short_description": "Автоматизация заявок и поддержки клиентов через удобный бот.",
        "full_description": (
            "Создали Telegram-бота для малого бизнеса: обработка заявок, каталог услуг, "
            "уведомления менеджерам и базовая аналитика по диалогам."
        ),
        "image": "images/case1.svg",
    },
    {
        "id": 2,
        "title": "Создание интернет-магазина",
        "short_description": "E-commerce платформа с каталогом, корзиной и оплатой.",
        "full_description": (
            "Разработали интернет-магазин с адаптивным UI, фильтрацией товаров, "
            "интеграцией онлайн-оплаты и панелью управления заказами."
        ),
        "image": "images/case2.svg",
    },
    {
        "id": 3,
        "title": "Автоматизация CRM",
        "short_description": "Интеграция CRM и автоматизация рутинных процессов отдела продаж.",
        "full_description": (
            "Настроили автоматическое распределение лидов, отчётность, цепочки писем "
            "и интеграции с корпоративной почтой и телефонией."
        ),
        "image": "images/case3.svg",
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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app.logger.info("Логирование инициализировано.")


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
