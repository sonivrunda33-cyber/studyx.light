import os
import secrets
from pathlib import Path

from flask import Flask

from .database import init_db
from .extensions import db, migrate
from . import models  # Register ORM models before table creation and migrations.
from .routes.api import api
from .routes.studyx_api import studyx
from .routes.web import web


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("LUMA_SECRET_KEY") or secrets.token_hex(32),
        DATABASE=str(Path(app.instance_path) / "luma_study.sqlite3"),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{Path(app.config['DATABASE']).as_posix()}"
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db, directory=str(Path(__file__).resolve().parent.parent / "migrations"))
    init_db(app)
    app.register_blueprint(web)
    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(studyx, url_prefix="/api/studyx")

    @app.errorhandler(404)
    def not_found(_error):
        return "Page not found", 404

    @app.errorhandler(500)
    def server_error(_error):
        return {"error": "Something went wrong. Please try again."}, 500

    return app
