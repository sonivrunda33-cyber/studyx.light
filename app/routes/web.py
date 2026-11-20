import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db as orm_db
from ..models import User, UserProfile
from ..database import get_db, seed_account_data

web = Blueprint("web", __name__)


@web.before_app_request
def require_signed_in_user():
    endpoint = request.endpoint or ""
    if endpoint == "static" or endpoint in {"web.login", "web.signup"}:
        return None
    if session.get("user_id"):
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "Please sign in to continue."}), 401
    return redirect(url_for("web.login", next=request.path))


def _safe_next(candidate):
    if not candidate:
        return url_for("web.dashboard")
    target = urlparse(urljoin(request.host_url, candidate))
    if target.scheme in {"http", "https"} and target.netloc == request.host:
        return target.path or url_for("web.dashboard")
    return url_for("web.dashboard")


def _auth_page(mode, error=None):
    return render_template("auth.html", mode=mode, error=error, next_path=request.values.get("next", ""))


@web.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("web.dashboard"))
        return _auth_page("login")
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = User.query.filter(orm_db.func.lower(User.email) == email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return _auth_page("login", "Email or password is incorrect."), 401
    if user.profile is None:
        user.profile = UserProfile(full_name=user.display_name)
        orm_db.session.commit()
    session.clear()
    session["user_id"] = user.id
    session["display_name"] = user.profile.full_name
    return redirect(_safe_next(request.form.get("next") or request.args.get("next")))


@web.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("web.dashboard"))
        return _auth_page("signup")
    display_name = request.form.get("display_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirmation = request.form.get("confirm_password", "")
    if len(display_name) < 2 or len(display_name) > 60:
        return _auth_page("signup", "Enter a name between 2 and 60 characters."), 400
    if len(email) > 160 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return _auth_page("signup", "Enter a valid email address."), 400
    if len(password) < 8:
        return _auth_page("signup", "Use a password with at least 8 characters."), 400
    if password != confirmation:
        return _auth_page("signup", "The passwords do not match."), 400
    legacy_db = get_db()
    first_account = User.query.count() == 0
    try:
        user = User(display_name=display_name, email=email,
                    password_hash=generate_password_hash(password),
                    created_at=datetime.now().astimezone().isoformat(timespec="seconds"))
        user.profile = UserProfile(full_name=display_name)
        orm_db.session.add(user)
        orm_db.session.commit()
    except IntegrityError:
        orm_db.session.rollback()
        return _auth_page("signup", "An account with that email already exists."), 409
    seed_account_data(legacy_db, user.id, claim_legacy=first_account)
    session.clear()
    session["user_id"] = user.id
    session["display_name"] = display_name
    return redirect(url_for("web.dashboard"))


@web.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("web.login"))


def page(template, page_name, title):
    return render_template(template, page=page_name, page_title=title)


@web.get("/")
def dashboard():
    return page("pages/dashboard.html", "dashboard", "Overview")


@web.get("/planner")
def planner():
    return page("pages/planner.html", "planner", "Study planner")


@web.get("/assignments")
def assignments():
    return page("pages/assignments.html", "assignments", "Assignments")


@web.get("/exams")
def exams():
    return page("pages/exams.html", "exams", "Exams & courses")


@web.get("/focus")
def focus():
    return page("pages/focus.html", "focus", "Focus room")


@web.get("/insights")
def insights():
    return page("pages/insights.html", "insights", "My progress")


@web.get("/research")
def research():
    return page("pages/research.html", "research", "Research lab")


@web.get("/settings")
def settings():
    return page("pages/settings.html", "settings", "Settings")
