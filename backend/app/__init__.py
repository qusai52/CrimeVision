import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from .db import init_db
from .routes.api import api

def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "development-only-change-me")
    app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "0") == "1"
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("UPLOAD_MAX_MB", "250")) * 1024 * 1024
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    init_db()
    app.register_blueprint(api, url_prefix="/api")
    @app.errorhandler(413)
    def too_large(_):
        return {"error": "File exceeds configured upload limit."}, 413
    return app
