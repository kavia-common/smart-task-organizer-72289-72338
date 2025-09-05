# Todo Backend (Flask + SQLAlchemy)

The Todo backend provides REST APIs for authentication, tasks, and subtasks. It uses Flask, flask-smorest for OpenAPI docs, SQLAlchemy for persistence, and session cookies for auth.

This service depends on a MySQL database (the `todo_database` container) and should be started after the database is running.

Contents:
- Environment variables
- How to connect to the database
- Local development setup
- API docs
- Troubleshooting connection issues

## Environment variables

All configuration is driven via environment variables. Create a `.env` file (or export variables) using `.env.example` as a template.

Backend service:
- FLASK_SECRET_KEY: Secret key for Flask sessions in production. Defaults to "dev-secret-change-me" for local dev.
- SESSION_COOKIE_NAME: Name of the session cookie. Default: "todo_session".
- SESSION_COOKIE_SAMESITE: SameSite attribute. Default: "Lax". For cross-site cookie usage with HTTPS frontends, you may need "None".
- SESSION_COOKIE_SECURE: Use secure cookie (HTTPS only). "True" or "False". Default: False.
- SESSION_COOKIE_HTTPONLY: HttpOnly cookie. "True" or "False". Default: True.
- PREFERRED_URL_SCHEME: http or https. Default: http.
- FRONTEND_ORIGIN: Comma-separated list of allowed frontend origins for CORS (when using credentials). Defaults to common local dev origins: http://localhost:3000, http://127.0.0.1:3000.

Database configuration (SQLAlchemy / PyMySQL):
- MYSQL_URL: Full SQLAlchemy URL. If set, takes precedence over other MYSQL_* vars. Example: mysql+pymysql://appuser:dbpass@localhost:5000/todo_db
- MYSQL_HOST: Database host. Default: localhost
- MYSQL_PORT: Database port. Default: 3306
- MYSQL_USER: Database user. Default: root
- MYSQL_PASSWORD: Database user password. Default: empty
- MYSQL_DB: Database name. Default: todo_db

Tip: When using the provided todo_database container/scripts, use the credentials/port they output (see smart-task-organizer-72289-72339/todo_database/startup.sh).

## Database connection details

The backend constructs a SQLAlchemy URL as follows if MYSQL_URL is not provided:
- mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}

Examples:
- Local dev with database started via provided scripts:
  - MYSQL_HOST=localhost
  - MYSQL_PORT=5000
  - MYSQL_USER=appuser
  - MYSQL_PASSWORD=dbuser123
  - MYSQL_DB=myapp
  - Result: mysql+pymysql://appuser:dbuser123@localhost:5000/myapp

If you already have a full URL, set MYSQL_URL directly, e.g.:
- MYSQL_URL=mysql+pymysql://appuser:dbuser123@localhost:5000/myapp

## Local development setup

Prerequisites:
- Python 3.11+
- Node.js (if you plan to run the frontend)
- MySQL server OR use the provided `todo_database` helper scripts

Recommended startup order:
1) Start the database first (todo_database)
   - From smart-task-organizer-72289-72339/todo_database:
     - Run: ./startup.sh
     - It initializes MySQL on a configurable port (default used by scripts is 5000), creates DB/user, applies schema, and outputs connection info to db_connection.txt.
     - It also writes env hints under todo_database/db_visualizer/mysql.env

   - Note the values for host/port/user/password/db for use in the backend .env.

2) Configure backend .env
   - Copy .env.example to .env and set values (especially MYSQL_*). Example:

     FLASK_SECRET_KEY=dev-secret-change-me
     FRONTEND_ORIGIN=http://localhost:3000
     MYSQL_HOST=localhost
     MYSQL_PORT=5000
     MYSQL_USER=appuser
     MYSQL_PASSWORD=dbuser123
     MYSQL_DB=myapp

   - Alternatively use MYSQL_URL directly.

3) Install backend dependencies and run
   - cd smart-task-organizer-72289-72338/todo_backend
   - python -m venv .venv && source .venv/bin/activate
   - pip install -r requirements.txt
   - export env vars from .env (or use a tool like direnv/forego)
   - python run.py
   - Server starts at http://localhost:5000 by default (Flask default); if you need a specific port, set FLASK_RUN_PORT or use a WSGI runner

4) Start the frontend (after backend is up)
   - See the todo_frontend/README.md for details.
   - Ensure REACT_APP_API_BASE (frontend) matches where the backend is served, e.g. http://localhost:5000

## API docs

OpenAPI docs are served via flask-smorest:
- Swagger UI path: /docs/
- Base: http://localhost:5000/docs/

You can generate and write a fresh OpenAPI JSON with:
- python generate_openapi.py
- Output goes to interfaces/openapi.json

## Troubleshooting

Database connection errors:
- "OperationalError: (pymysql.err.OperationalError) (2003, ...)" or engine not initialized:
  - Verify the DB is running and reachable at MYSQL_HOST:MYSQL_PORT.
  - Confirm credentials match (MYSQL_USER, MYSQL_PASSWORD).
  - Confirm database name exists (MYSQL_DB).
  - If using the helper scripts, check smart-task-organizer-72289-72339/todo_database/db_connection.txt.
  - Check MySQL auth plugin: our startup.sh configures mysql_native_password for compatibility.

- "Database engine not initialized. Call init_engine() first." on backend startup:
  - Ensure environment variables are set and visible to the process.
  - Confirm app imports call init_engine(get_database_uri()) (already done in app/__init__.py).
  - If running unit tests, make sure test env exports the required MYSQL_* or MYSQL_URL.

CORS or cookie/session issues:
- If accessing the backend from a different origin:
  - Ensure FRONTEND_ORIGIN includes the frontend origin(s).
  - When using HTTPS for frontend and HTTP for backend, browsers may block cookies. Align schemes or set SESSION_COOKIE_SAMESITE=None and SESSION_COOKIE_SECURE=True for secure cross-site cookies over HTTPS.
  - The frontend fetch client sends credentials: "include"; Access-Control-Allow-Origin cannot be "*", so set explicit origins.

Port conflicts:
- If MySQL or Flask port is in use, either stop the conflicting process or change the port (MYSQL_PORT for DB; run Flask on a different port or via a proxy).

## Project structure (backend)

- run.py: Flask entrypoint
- app/__init__.py: App factory, CORS, OpenAPI, DB init, blueprints
- app/db.py: SQLAlchemy engine/session setup; reads from env
- app/models.py: ORM models (User, Task, Subtask)
- app/routes/: Blueprints for health, auth, tasks/subtasks
- app/schemas.py: Marshmallow schemas
- app/services/tasks_service.py: Business logic
- requirements.txt: Python dependencies

## Notes

- Authentication is username-based with server-side sessions. Password is posted by the UI but not used/verified in this stub logic.
- For production, use a strong FLASK_SECRET_KEY, HTTPS, secure cookie settings, and a hardened DB user/password with limited privileges.
