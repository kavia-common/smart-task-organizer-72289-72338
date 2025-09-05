from flask import Flask, g
from flask_cors import CORS
from flask_smorest import Api

# Initialize Flask app first
app = Flask(__name__)
app.url_map.strict_slashes = False

# CORS config
CORS(app, resources={r"/*": {"origins": "*"}})

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
from .routes.health import blp  # noqa: E402
api = Api(app)
api.register_blueprint(blp)
