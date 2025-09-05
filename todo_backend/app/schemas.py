"""
Centralized Marshmallow schemas for request/response validation and OpenAPI.

This module defines the public schemas used by the Flask application and
flask-smorest to produce the OpenAPI specification. Keeping all schemas in a
single module ensures consistency across endpoints and makes it easier to
maintain API documentation.
"""
from __future__ import annotations

from marshmallow import Schema, fields, validate, EXCLUDE


# PUBLIC_INTERFACE
class UserResponseSchema(Schema):
    """User representation returned by auth endpoints."""

    id = fields.Integer(required=True, metadata={"description": "User ID"})
    username = fields.String(required=True, metadata={"description": "Username"})
    created_at = fields.String(
        required=False,
        allow_none=True,
        metadata={"description": "User creation timestamp in ISO8601"},
    )


# PUBLIC_INTERFACE
class LoginRequestSchema(Schema):
    """Login request payload with a username field.

    Unknown fields are excluded to avoid accidental acceptance of extra input.
    """

    class Meta:
        unknown = EXCLUDE

    username = fields.String(
        required=True,
        validate=validate.Length(min=1, max=150),
        metadata={
            "description": "The username to log in with (created if not existing)."
        },
    )


# PUBLIC_INTERFACE
class MeResponseSchema(Schema):
    """Response for /auth/me returning the current user or null."""

    user = fields.Nested(
        UserResponseSchema,
        allow_none=True,
        metadata={"description": "The current user or null if not logged in"},
    )


# PUBLIC_INTERFACE
class LoginResponseSchema(Schema):
    """Response for successful login returning the user object."""

    user = fields.Nested(
        UserResponseSchema,
        required=True,
        metadata={"description": "The logged in user"},
    )


# PUBLIC_INTERFACE
class LogoutResponseSchema(Schema):
    """Response for logout action."""

    success = fields.Boolean(required=True, metadata={"description": "True if logout succeeded"})


# PUBLIC_INTERFACE
class TaskBaseSchema(Schema):
    """Base fields for Task create/update payloads."""

    class Meta:
        unknown = EXCLUDE

    title = fields.String(required=True, validate=validate.Length(min=1, max=255))
    description = fields.String(required=False, allow_none=True)
    priority = fields.Integer(required=False, validate=validate.Range(min=0))
    estimated_minutes = fields.Integer(required=False, validate=validate.Range(min=0))
    due_at = fields.DateTime(required=False, allow_none=True)


# PUBLIC_INTERFACE
class TaskCreateSchema(TaskBaseSchema):
    """Schema for creating a task."""

    title = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255),
        metadata={"description": "Task title"},
    )


# PUBLIC_INTERFACE
class TaskUpdateSchema(Schema):
    """Schema for updating a task (all fields optional)."""

    class Meta:
        unknown = EXCLUDE

    title = fields.String(required=False, allow_none=True, validate=validate.Length(min=1, max=255))
    description = fields.String(required=False, allow_none=True)
    priority = fields.Integer(required=False, allow_none=True)
    estimated_minutes = fields.Integer(required=False, allow_none=True)
    due_at = fields.DateTime(required=False, allow_none=True)


# PUBLIC_INTERFACE
class TaskResponseSchema(Schema):
    """Task representation returned by list/get endpoints."""

    id = fields.Integer(required=True)
    title = fields.String(required=True)
    description = fields.String(allow_none=True)
    priority = fields.Integer(required=True)
    estimated_minutes = fields.Integer(required=True)
    due_at = fields.String(allow_none=True)
    is_completed = fields.Boolean(required=True)
    created_at = fields.String(allow_none=True)
    updated_at = fields.String(allow_none=True)


# PUBLIC_INTERFACE
class TaskDetailResponseSchema(TaskResponseSchema):
    """Task representation with nested subtasks."""

    subtasks = fields.List(fields.Dict(), required=True)


# PUBLIC_INTERFACE
class TasksListQuerySchema(Schema):
    """Query parameters available when listing tasks."""

    search = fields.String(required=False)
    priority = fields.Integer(required=False)
    due_within_days = fields.Integer(required=False)
    sort_by = fields.String(
        required=False,
        validate=validate.OneOf(["priority", "due_at", "estimated_minutes", "created_at"]),
    )


# PUBLIC_INTERFACE
class SuccessSchema(Schema):
    """Generic success response shape."""

    success = fields.Boolean(required=True)


# PUBLIC_INTERFACE
class CompleteActionSchema(Schema):
    """Payload for completion operations on tasks/subtasks."""

    class Meta:
        unknown = EXCLUDE

    complete = fields.Boolean(required=False, missing=True)
    cascade = fields.Boolean(required=False, missing=False)


# ---------- Subtasks ----------


# PUBLIC_INTERFACE
class SubtaskBaseSchema(Schema):
    """Base fields for subtask create/update payloads."""

    class Meta:
        unknown = EXCLUDE

    title = fields.String(required=True, validate=validate.Length(min=1, max=255))
    description = fields.String(required=False, allow_none=True)
    parent_subtask_id = fields.Integer(required=False, allow_none=True)
    order_index = fields.Integer(required=False, allow_none=True, validate=validate.Range(min=0))


# PUBLIC_INTERFACE
class SubtaskCreateSchema(SubtaskBaseSchema):
    """Create subtask payload schema."""

    pass


# PUBLIC_INTERFACE
class SubtaskUpdateSchema(Schema):
    """Update subtask payload schema (all fields optional)."""

    class Meta:
        unknown = EXCLUDE

    title = fields.String(required=False, allow_none=True, validate=validate.Length(min=1, max=255))
    description = fields.String(required=False, allow_none=True)
    parent_subtask_id = fields.Integer(required=False, allow_none=True)
    order_index = fields.Integer(required=False, allow_none=True, validate=validate.Range(min=0))


# PUBLIC_INTERFACE
class SubtaskResponseSchema(Schema):
    """Subtask representation with effective fields derived from the parent task."""

    id = fields.Integer(required=True)
    task_id = fields.Integer(required=True)
    parent_subtask_id = fields.Integer(allow_none=True)
    title = fields.String(required=True)
    description = fields.String(allow_none=True)
    is_completed = fields.Boolean(required=True)
    order_index = fields.Integer(required=True)
    created_at = fields.String(allow_none=True)
    updated_at = fields.String(allow_none=True)
    effective_priority = fields.Integer(allow_none=True)
    effective_estimated_minutes = fields.Integer(allow_none=True)
    effective_due_at = fields.String(allow_none=True)


# PUBLIC_INTERFACE
class HealthResponseSchema(Schema):
    """Simple health check response."""

    message = fields.String(required=True, metadata={"description": "Health status message"})
