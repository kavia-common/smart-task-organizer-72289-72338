from __future__ import annotations

from typing import Optional, Dict, Any

from flask import g, session
from flask.views import MethodView
from flask_smorest import Blueprint
from marshmallow import Schema, fields, validate, EXCLUDE

from ..models import User

# Create a Blueprint for authentication-related routes
blp = Blueprint(
    "Auth",
    "auth",
    url_prefix="/auth",
    description="User authentication endpoints (session-based by username).",
)


def _serialize_user(user: User) -> Dict[str, Any]:
    """Serialize a User model to a safe dictionary."""
    return {
        "id": user.id,
        "username": user.username,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


class LoginRequestSchema(Schema):
    """Schema for login request payload: a simple username-only login."""
    class Meta:
        unknown = EXCLUDE

    username = fields.String(
        required=True,
        validate=validate.Length(min=1, max=150),
        metadata={"description": "The username to log in with (will be created if not existing)."},
    )


class UserResponseSchema(Schema):
    """Schema for the user response."""
    id = fields.Integer(required=True, metadata={"description": "User ID"})
    username = fields.String(required=True, metadata={"description": "Username"})
    created_at = fields.String(required=False, allow_none=True, metadata={"description": "User creation timestamp in ISO8601"})


class MeResponseSchema(Schema):
    """Schema for /auth/me response."""
    user = fields.Nested(UserResponseSchema, allow_none=True, metadata={"description": "The current user or null if not logged in"})


class LoginResponseSchema(Schema):
    """Schema for login response."""
    user = fields.Nested(UserResponseSchema, required=True, metadata={"description": "The logged in user"})


class LogoutResponseSchema(Schema):
    """Schema for logout response."""
    success = fields.Boolean(required=True, metadata={"description": "True if logout succeeded"})


@blp.route("/login")
class Login(MethodView):
    """Log in using a simple username-based session.

    If the username does not exist, it will be created.
    A session cookie will be set to maintain the login in subsequent requests.
    """
    @blp.arguments(LoginRequestSchema, location="json")
    @blp.response(200, LoginResponseSchema)
    @blp.doc(
        summary="Login with username",
        description="Accepts a username and logs the user in using server-side session. Creates the user if not found.",
        operationId="auth_login",
        tags=["Auth"],
        responses={
            400: {"description": "Invalid input"},
            500: {"description": "Server error"},
        },
    )
    def post(self, json_data):
        username = json_data["username"].strip()

        # Look up user or create
        db = g.db
        user: Optional[User] = db.query(User).filter(User.username == username).one_or_none()
        if user is None:
            user = User(username=username)
            db.add(user)
            db.commit()
            db.refresh(user)

        # Set session
        session["user_id"] = user.id

        return {"user": _serialize_user(user)}


@blp.route("/logout")
class Logout(MethodView):
    """Log out the current session."""
    @blp.response(200, LogoutResponseSchema)
    @blp.doc(
        summary="Logout",
        description="Clears the current session so the user is logged out.",
        operationId="auth_logout",
        tags=["Auth"],
        responses={
            200: {"description": "Logout successful"},
        },
    )
    def post(self):
        session.clear()
        return {"success": True}


@blp.route("/me")
class Me(MethodView):
    """Get the current user from the session."""
    @blp.response(200, MeResponseSchema)
    @blp.doc(
        summary="Get current user",
        description="Returns the current user based on session cookie. If not logged in, returns user: null.",
        operationId="auth_me",
        tags=["Auth"],
        responses={
            200: {"description": "Current user (or null if not logged in)"},
        },
    )
    def get(self):
        user_id = session.get("user_id")
        if not user_id:
            return {"user": None}

        db = g.db
        user: Optional[User] = db.get(User, user_id)
        if not user:
            # Session references a non-existent user; clear it.
            session.clear()
            return {"user": None}

        return {"user": _serialize_user(user)}
