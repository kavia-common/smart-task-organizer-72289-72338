from __future__ import annotations

import os

from flask import Flask, g
from flask_cors import CORS
from flask_smorest import Api

# Initialize Flask app first
app = Flask(__name__)
app.url_map.strict_slashes = False

# Session / Security configuration using environment variables for flexibility
# Do not hard-code secrets; use FLASK_SECRET_KEY in environment when possible.
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

# Session cookie settings suitable for development. These can be overridden by env vars.
# For cross-site cookies in development with HTTPS frontends, you may need:
#   SESSION_COOKIE_SAMESITE=None and SESSION_COOKIE_SECURE=True
# Defaults are chosen for local dev; override as needed.
app.config["SESSION_COOKIE_NAME"] = os.getenv("SESSION_COOKIE_NAME", "todo_session")
app.config["SESSION_COOKIE_SAMESITE"] = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
app.config["SESSION_COOKIE_HTTPONLY"] = os.getenv("SESSION_COOKIE_HTTPONLY", "True").lower() == "true"
app.config["PREFERRED_URL_SCHEME"] = os.getenv("PREFERRED_URL_SCHEME", "http")

# CORS configuration
# When using credentials (cookies), Access-Control-Allow-Origin cannot be "*".
# We default to common local dev origins and allow override with FRONTEND_ORIGIN (comma-separated list).
default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
extra_origins = [o.strip() for o in os.getenv("FRONTEND_ORIGIN", "").split(",") if o.strip()]
cors_origins = list({*default_origins, *extra_origins}) if extra_origins else default_origins

CORS(
    app,
    resources={r"/*": {"origins": cors_origins}},
    supports_credentials=True,
)

# OpenAPI / API docs config
app.config["API_TITLE"] = "My Flask API"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.3"
app.config["OPENAPI_URL_PREFIX"] = "/docs"
app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

# Database initialization (SQLAlchemy Core/ORM)
from .db import init_engine, get_database_uri, get_engine, get_session, remove_session, Base  # noqa: E402
from . import models  # noqa: F401,E402  # ensure models are imported so metadata is registered

# Initialize the database engine and session factory using environment variables
init_engine(get_database_uri())

# Create tables if they don't exist yet
with app.app_context():
    Base.metadata.create_all(bind=get_engine())

# Setup per-request session handling
@app.before_request
def _db_before_request():
    # Create a new session at the start of each request and store on g
    g.db = get_session()


@app.teardown_appcontext
def _db_teardown(exception):
    # Remove scoped session after request to avoid connection leaks
    remove_session()


# Register blueprints and API after DB init
from .routes.health import blp as health_blp  # noqa: E402
from .routes.auth import blp as auth_blp  # noqa: E402

api = Api(app, spec_kwargs={"servers": [{"url": "/"}]})
api.register_blueprint(health_blp)
api.register_blueprint(auth_blp)
