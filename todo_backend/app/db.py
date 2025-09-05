"""
Database initialization and session management using SQLAlchemy.

This module builds a SQLAlchemy engine using environment variables and provides
a scoped session factory for use throughout the application.
"""
from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

# Base class for all ORM models to inherit from
Base = declarative_base()

# Module-level engine and session factory
_engine = None
_SessionFactory = None
Session = None  # scoped_session


def _build_mysql_uri(
    host: str,
    user: str,
    password: str,
    db: str,
    port: int,
) -> str:
    """
    Construct a SQLAlchemy MySQL connection URI using the PyMySQL driver.

    Example: mysql+pymysql://user:password@host:3306/dbname
    """
    # URL-encode is handled by SQLAlchemy if provided as URL object; for string, assume sane values.
    pw = f":{password}" if password else ""
    return f"mysql+pymysql://{user}{pw}@{host}:{port}/{db}"


# PUBLIC_INTERFACE
def get_database_uri() -> str:
    """Build the SQLAlchemy database URI from environment variables.

    Environment variables:
      - MYSQL_URL (optional): if provided, used as a full SQLAlchemy URL directly.
      - MYSQL_USER (default: 'root')
      - MYSQL_PASSWORD (default: '')
      - MYSQL_DB (default: 'todo_db')
      - MYSQL_PORT (default: 3306)
      - Hostname is taken from MYSQL_URL if present; otherwise MYSQL_HOST (default: 'localhost').

    Note: These defaults aim to match typical local MySQL scripts. If the database
    container provides different defaults, set them in the environment.
    """
    # If MYSQL_URL is provided, prefer it as a complete URL
    mysql_url = os.getenv("MYSQL_URL")
    if mysql_url:
        return mysql_url

    # Otherwise compose from discrete parts
    host = os.getenv("MYSQL_HOST", "localhost")
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    db = os.getenv("MYSQL_DB", "todo_db")

    # Port may come as str; default to 3306
    try:
        port = int(os.getenv("MYSQL_PORT", "3306"))
    except ValueError:
        port = 3306

    return _build_mysql_uri(host=host, user=user, password=password, db=db, port=port)


# PUBLIC_INTERFACE
def init_engine(database_uri: Optional[str] = None):
    """Initialize the SQLAlchemy engine and scoped session.

    This should be called once during application startup.

    Args:
        database_uri: Optional full database URI. If not provided, it will be
                      derived from environment variables by get_database_uri().
    """
    global _engine, _SessionFactory, Session
    if database_uri is None:
        database_uri = get_database_uri()

    # Create engine with sensible defaults
    _engine = create_engine(
        database_uri,
        pool_pre_ping=True,  # Validate connections before using them
        future=True,
    )

    # Create a session factory and a scoped_session for thread safety
    _SessionFactory = sessionmaker(
        bind=_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )
    Session = scoped_session(_SessionFactory)


# PUBLIC_INTERFACE
def get_engine():
    """Return the initialized SQLAlchemy engine."""
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call init_engine() first.")
    return _engine


# PUBLIC_INTERFACE
def get_session():
    """Provide a new SQLAlchemy session bound to the engine."""
    if Session is None:
        raise RuntimeError("Session factory not initialized. Call init_engine() first.")
    return Session()


# PUBLIC_INTERFACE
def remove_session():
    """Remove the current scoped session (to be called on app context teardown)."""
    if Session is not None:
        Session.remove()
