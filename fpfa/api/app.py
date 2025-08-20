import os
from flask import Flask
from flask_cors import CORS

from ..config import load_config
from .routes import bp as main_bp


def create_app() -> Flask:
    cfg = load_config()
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

    app = Flask(
        __name__,
        template_folder=os.path.join(project_root, "templates"),
        static_folder=os.path.join(project_root, "static"),
    )
    CORS(app)

    # Register blueprints
    app.register_blueprint(main_bp)

    return app

