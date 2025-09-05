from __future__ import annotations

from datetime import datetime

from flask import g, session
from flask.views import MethodView
from flask_smorest import Blueprint
from marshmallow import Schema, fields, validate, EXCLUDE

from ..services import tasks_service


blp = Blueprint(
    "Tasks",
    "tasks",
    url_prefix="/tasks",
    description="Task and Subtask management endpoints.",
)


def _require_user_id() -> int:
    """Fetch current session user_id or raise a 401 error via flask-smorest abort."""
    user_id = session.get("user_id")
    if not user_id:
        blp.abort(401, message="Not authenticated")
    return int(user_id)


# ===== Schemas =====

class TaskBaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    title = fields.String(required=True, validate=validate.Length(min=1, max=255))
    description = fields.String(required=False, allow_none=True)
    priority = fields.Integer(required=False, validate=validate.Range(min=0))
    estimated_minutes = fields.Integer(required=False, validate=validate.Range(min=0))
    due_at = fields.DateTime(required=False, allow_none=True)


class TaskCreateSchema(TaskBaseSchema):
    """Schema for creating a task."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=255), metadata={"description": "Task title"})


class TaskUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    title = fields.String(required=False, allow_none=True, validate=validate.Length(min=1, max=255))
    description = fields.String(required=False, allow_none=True)
    priority = fields.Integer(required=False, allow_none=True)
    estimated_minutes = fields.Integer(required=False, allow_none=True)
    due_at = fields.DateTime(required=False, allow_none=True)


class TaskResponseSchema(Schema):
    id = fields.Integer(required=True)
    title = fields.String(required=True)
    description = fields.String(allow_none=True)
    priority = fields.Integer(required=True)
    estimated_minutes = fields.Integer(required=True)
    due_at = fields.String(allow_none=True)
    is_completed = fields.Boolean(required=True)
    created_at = fields.String(allow_none=True)
    updated_at = fields.String(allow_none=True)


class TaskDetailResponseSchema(TaskResponseSchema):
    subtasks = fields.List(fields.Dict(), required=True)


class TasksListQuerySchema(Schema):
    search = fields.String(required=False)
    priority = fields.Integer(required=False)
    due_within_days = fields.Integer(required=False)
    sort_by = fields.String(required=False, validate=validate.OneOf(["priority", "due_at", "estimated_minutes", "created_at"]))


class SuccessSchema(Schema):
    success = fields.Boolean(required=True)


class CompleteActionSchema(Schema):
    """Schema for completion action on tasks/subtasks."""
    class Meta:
        unknown = EXCLUDE

    complete = fields.Boolean(required=False, missing=True)
    cascade = fields.Boolean(required=False, missing=False)


# Subtask schemas

class SubtaskBaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    title = fields.String(required=True, validate=validate.Length(min=1, max=255))
    description = fields.String(required=False, allow_none=True)
    parent_subtask_id = fields.Integer(required=False, allow_none=True)
    order_index = fields.Integer(required=False, allow_none=True, validate=validate.Range(min=0))


class SubtaskCreateSchema(SubtaskBaseSchema):
    pass


class SubtaskUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    title = fields.String(required=False, allow_none=True, validate=validate.Length(min=1, max=255))
    description = fields.String(required=False, allow_none=True)
    parent_subtask_id = fields.Integer(required=False, allow_none=True)
    order_index = fields.Integer(required=False, allow_none=True, validate=validate.Range(min=0))


class SubtaskResponseSchema(Schema):
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


# ===== Routes =====

@blp.route("")
class TasksCollection(MethodView):
    """List and create tasks for the current user."""

    @blp.arguments(TasksListQuerySchema, location="query")
    @blp.response(200, TaskResponseSchema(many=True))
    @blp.doc(
        summary="List tasks",
        description="List tasks for the current session user with optional search, filter, and sorting.",
        operationId="tasks_list",
        tags=["Tasks"],
        responses={401: {"description": "Not authenticated"}, 200: {"description": "List of tasks"}},
    )
    def get(self, args):
        user_id = _require_user_id()
        tasks = tasks_service.list_tasks(
            g.db,
            user_id=user_id,
            search=args.get("search"),
            priority=args.get("priority"),
            due_within_days=args.get("due_within_days"),
            sort_by=args.get("sort_by"),
        )
        return tasks

    @blp.arguments(TaskCreateSchema)
    @blp.response(201, TaskDetailResponseSchema)
    @blp.doc(
        summary="Create task",
        description="Create a new task for the current session user.",
        operationId="tasks_create",
        tags=["Tasks"],
        responses={401: {"description": "Not authenticated"}, 201: {"description": "Task created"}},
    )
    def post(self, json_data):
        user_id = _require_user_id()
        due_at = json_data.get("due_at")
        if isinstance(due_at, str):
            due_at = datetime.fromisoformat(due_at) if due_at else None
        task = tasks_service.create_task(
            g.db,
            user_id=user_id,
            title=json_data["title"],
            description=json_data.get("description"),
            priority=json_data.get("priority"),
            estimated_minutes=json_data.get("estimated_minutes"),
            due_at=due_at,
        )
        return task


@blp.route("/<int:task_id>")
class TaskItem(MethodView):
    """Retrieve, update, or delete a task."""

    @blp.response(200, TaskDetailResponseSchema)
    @blp.doc(
        summary="Get task",
        description="Get a task by ID owned by the current session user.",
        operationId="tasks_get",
        tags=["Tasks"],
        responses={401: {"description": "Not authenticated"}, 404: {"description": "Task not found"}},
    )
    def get(self, task_id: int):
        user_id = _require_user_id()
        try:
            task = tasks_service.get_task(g.db, user_id=user_id, task_id=task_id, include_subtasks=True)
            return task
        except LookupError:
            blp.abort(404, message="Task not found")

    @blp.arguments(TaskUpdateSchema)
    @blp.response(200, TaskDetailResponseSchema)
    @blp.doc(
        summary="Update task",
        description="Update fields on a task owned by the current session user.",
        operationId="tasks_update",
        tags=["Tasks"],
        responses={401: {"description": "Not authenticated"}, 404: {"description": "Task not found"}},
    )
    def patch(self, json_data, task_id: int):
        user_id = _require_user_id()
        updates = dict(json_data)
        # due_at already parsed by marshmallow as datetime if provided
        try:
            task = tasks_service.update_task(g.db, user_id=user_id, task_id=task_id, updates=updates)
            return task
        except LookupError:
            blp.abort(404, message="Task not found")

    @blp.response(200, SuccessSchema)
    @blp.doc(
        summary="Delete task",
        description="Delete a task owned by the current session user.",
        operationId="tasks_delete",
        tags=["Tasks"],
        responses={401: {"description": "Not authenticated"}, 404: {"description": "Task not found"}},
    )
    def delete(self, task_id: int):
        user_id = _require_user_id()
        try:
            tasks_service.delete_task(g.db, user_id=user_id, task_id=task_id)
            return {"success": True}
        except LookupError:
            blp.abort(404, message="Task not found")


@blp.route("/<int:task_id>/complete")
class TaskComplete(MethodView):
    """Mark a task complete/incomplete; optionally cascade to all subtasks."""

    @blp.arguments(CompleteActionSchema)
    @blp.response(200, TaskDetailResponseSchema)
    @blp.doc(
        summary="Complete task",
        description="Mark a task complete or incomplete; can cascade to all subtasks.",
        operationId="tasks_complete",
        tags=["Tasks"],
        responses={401: {"description": "Not authenticated"}, 404: {"description": "Task not found"}},
    )
    def post(self, json_data, task_id: int):
        user_id = _require_user_id()
        try:
            result = tasks_service.mark_task_complete(
                g.db,
                user_id=user_id,
                task_id=task_id,
                complete=bool(json_data.get("complete", True)),
                cascade=bool(json_data.get("cascade", False)),
            )
            return result
        except LookupError:
            blp.abort(404, message="Task not found")


@blp.route("/<int:task_id>/subtasks")
class TaskSubtasksCollection(MethodView):
    """List or create subtasks under a given task."""

    @blp.response(200, SubtaskResponseSchema(many=True))
    @blp.doc(
        summary="List subtasks by task",
        description="List subtasks for a given task owned by the current session user.",
        operationId="subtasks_list_by_task",
        tags=["Subtasks"],
        responses={401: {"description": "Not authenticated"}, 404: {"description": "Task not found"}},
    )
    def get(self, task_id: int):
        user_id = _require_user_id()
        try:
            subtasks = tasks_service.list_subtasks(g.db, user_id=user_id, task_id=task_id)
            return subtasks
        except LookupError:
            blp.abort(404, message="Task not found")

    @blp.arguments(SubtaskCreateSchema)
    @blp.response(201, SubtaskResponseSchema)
    @blp.doc(
        summary="Create subtask",
        description="Create a subtask under the given task; parent_subtask_id can be provided for nesting.",
        operationId="subtasks_create",
        tags=["Subtasks"],
        responses={401: {"description": "Not authenticated"}, 404: {"description": "Task or parent subtask not found"}},
    )
    def post(self, json_data, task_id: int):
        user_id = _require_user_id()
        try:
            subtask = tasks_service.create_subtask(
                g.db,
                user_id=user_id,
                task_id=task_id,
                title=json_data["title"],
                description=json_data.get("description"),
                parent_subtask_id=json_data.get("parent_subtask_id"),
                order_index=json_data.get("order_index"),
            )
            return subtask
        except LookupError as e:
            blp.abort(404, message=str(e))


# Standalone subtask routes

subtasks_blp = Blueprint(
    "Subtasks",
    "subtasks",
    url_prefix="/subtasks",
    description="Standalone subtask operations.",
)


@subtasks_blp.route("/<int:subtask_id>")
class SubtaskItem(MethodView):
    """Get, update, or delete a subtask by id (scoped to current user)."""

    @subtasks_blp.response(200, SubtaskResponseSchema)
    @subtasks_blp.doc(
        summary="Get subtask",
        description="Get a subtask by ID owned by the current session user.",
        operationId="subtasks_get",
        tags=["Subtasks"],
        responses={401: {"description": "Not authenticated"}, 404: {"description": "Subtask not found"}},
    )
    def get(self, subtask_id: int):
        user_id = _require_user_id()
        try:
            subtask = tasks_service.get_subtask(g.db, user_id=user_id, subtask_id=subtask_id)
            return subtask
        except LookupError:
            subtasks_blp.abort(404, message="Subtask not found")

    @subtasks_blp.arguments(SubtaskUpdateSchema)
    @subtasks_blp.response(200, SubtaskResponseSchema)
    @subtasks_blp.doc(
        summary="Update subtask",
        description="Update a subtask's fields (title, description, order_index, parent_subtask_id).",
        operationId="subtasks_update",
        tags=["Subtasks"],
        responses={401: {"description": "Not authenticated"}, 404: {"description": "Subtask not found"}},
    )
    def patch(self, json_data, subtask_id: int):
        user_id = _require_user_id()
        try:
            subtask = tasks_service.update_subtask(g.db, user_id=user_id, subtask_id=subtask_id, updates=dict(json_data))
            return subtask
        except LookupError:
            subtasks_blp.abort(404, message="Subtask not found")
        except ValueError as e:
            subtasks_blp.abort(400, message=str(e))

    @subtasks_blp.response(200, SuccessSchema)
    @subtasks_blp.doc(
        summary="Delete subtask",
        description="Delete a subtask by ID (must be owned by current session user).",
        operationId="subtasks_delete",
        tags=["Subtasks"],
        responses={401: {"description": "Not authenticated"}, 404: {"description": "Subtask not found"}},
    )
    def delete(self, subtask_id: int):
        user_id = _require_user_id()
        try:
            tasks_service.delete_subtask(g.db, user_id=user_id, subtask_id=subtask_id)
            return {"success": True}
        except LookupError:
            subtasks_blp.abort(404, message="Subtask not found")


@subtasks_blp.route("/<int:subtask_id>/complete")
class SubtaskComplete(MethodView):
    """Mark subtask complete/incomplete, optional cascade to children."""

    @subtasks_blp.arguments(CompleteActionSchema)
    @subtasks_blp.response(200, SubtaskResponseSchema)
    @subtasks_blp.doc(
        summary="Complete subtask",
        description="Mark a subtask as complete or incomplete with optional cascade to children.",
        operationId="subtasks_complete",
        tags=["Subtasks"],
        responses={401: {"description": "Not authenticated"}, 404: {"description": "Subtask not found"}},
    )
    def post(self, json_data, subtask_id: int):
        user_id = _require_user_id()
        try:
            result = tasks_service.mark_subtask_complete(
                g.db,
                user_id=user_id,
                subtask_id=subtask_id,
                complete=bool(json_data.get("complete", True)),
                cascade=bool(json_data.get("cascade", False)),
            )
            return result
        except LookupError:
            subtasks_blp.abort(404, message="Subtask not found")
