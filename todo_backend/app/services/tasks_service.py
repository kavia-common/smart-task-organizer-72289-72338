from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..models import Task, Subtask, User


# PUBLIC_INTERFACE
def require_user(db: Session, user_id: Optional[int]) -> User:
    """Ensure a valid user exists for the given user_id, or raise ValueError.

    Args:
        db: SQLAlchemy session
        user_id: The current session user_id

    Returns:
        The User model

    Raises:
        ValueError: if user_id is not provided or the user is not found
    """
    if not user_id:
        raise ValueError("Not authenticated")
    user = db.get(User, user_id)
    if not user:
        raise ValueError("User not found")
    return user


def _serialize_task(task: Task, include_subtasks: bool = True) -> Dict[str, Any]:
    """Serialize a Task to a dictionary representation."""
    payload: Dict[str, Any] = {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "estimated_minutes": task.estimated_minutes,
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "is_completed": task.is_completed,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }
    if include_subtasks:
        payload["subtasks"] = [_serialize_subtask(st, task) for st in task.subtasks]
    return payload


def _serialize_subtask(subtask: Subtask, parent_task_for_inheritance: Optional[Task] = None) -> Dict[str, Any]:
    """Serialize a Subtask, including effective values inherited from parent task.

    Since Subtask does not have priority/due/estimated fields, we expose effective_*
    derived from the parent Task for UI convenience.
    """
    parent_task = parent_task_for_inheritance or subtask.task
    return {
        "id": subtask.id,
        "task_id": subtask.task_id,
        "parent_subtask_id": subtask.parent_subtask_id,
        "title": subtask.title,
        "description": subtask.description,
        "is_completed": subtask.is_completed,
        "order_index": subtask.order_index,
        "created_at": subtask.created_at.isoformat() if subtask.created_at else None,
        "updated_at": subtask.updated_at.isoformat() if subtask.updated_at else None,
        # inherited attributes from parent task for convenience
        "effective_priority": parent_task.priority if parent_task else None,
        "effective_estimated_minutes": parent_task.estimated_minutes if parent_task else None,
        "effective_due_at": parent_task.due_at.isoformat() if (parent_task and parent_task.due_at) else None,
    }


# PUBLIC_INTERFACE
def list_tasks(
    db: Session,
    user_id: int,
    search: Optional[str] = None,
    priority: Optional[int] = None,
    due_within_days: Optional[int] = None,
    sort_by: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List tasks for the current user with optional filter and sorting.

    Args:
        db: session
        user_id: current user id
        search: optional text search on title/description
        priority: optional filter by priority
        due_within_days: optional filter for tasks due within N days (>=0)
        sort_by: one of [priority, due_at, estimated_minutes, created_at] (default: created_at desc)

    Returns:
        List of serialized tasks (without nested subtasks by default)
    """
    require_user(db, user_id)

    stmt = select(Task).where(Task.user_id == user_id)

    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(Task.title.ilike(like), Task.description.ilike(like)))
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    if due_within_days is not None:
        try:
            days = int(due_within_days)
            if days >= 0:
                now = datetime.utcnow()
                until = now + timedelta(days=days)
                stmt = stmt.where(and_(Task.due_at.is_not(None), Task.due_at <= until))
        except Exception:
            pass

    # Sorting
    if sort_by == "priority":
        stmt = stmt.order_by(Task.priority.asc(), Task.created_at.desc())
    elif sort_by == "due_at":
        stmt = stmt.order_by(Task.due_at.is_(None), Task.due_at.asc())  # None last
    elif sort_by == "estimated_minutes":
        stmt = stmt.order_by(Task.estimated_minutes.asc(), Task.created_at.desc())
    else:
        # default
        stmt = stmt.order_by(Task.created_at.desc())

    tasks = list(db.scalars(stmt))
    return [_serialize_task(t, include_subtasks=False) for t in tasks]


# PUBLIC_INTERFACE
def create_task(
    db: Session,
    user_id: int,
    title: str,
    description: Optional[str],
    priority: Optional[int],
    estimated_minutes: Optional[int],
    due_at: Optional[datetime],
) -> Dict[str, Any]:
    """Create a new task for the current user."""
    user = require_user(db, user_id)

    task = Task(
        user_id=user.id,
        title=title.strip(),
        description=(description or None),
        priority=int(priority) if priority is not None else 3,
        estimated_minutes=int(estimated_minutes) if estimated_minutes is not None else 0,
        due_at=due_at,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _serialize_task(task)


# PUBLIC_INTERFACE
def get_task(db: Session, user_id: int, task_id: int, include_subtasks: bool = True) -> Dict[str, Any]:
    """Get a task by id for the current user."""
    require_user(db, user_id)
    task = db.get(Task, task_id)
    if not task or task.user_id != user_id:
        raise LookupError("Task not found")
    return _serialize_task(task, include_subtasks=include_subtasks)


# PUBLIC_INTERFACE
def update_task(
    db: Session,
    user_id: int,
    task_id: int,
    updates: Dict[str, Any],
) -> Dict[str, Any]:
    """Update fields on a task for the current user."""
    require_user(db, user_id)
    task = db.get(Task, task_id)
    if not task or task.user_id != user_id:
        raise LookupError("Task not found")

    if "title" in updates and updates["title"] is not None:
        task.title = str(updates["title"]).strip()
    if "description" in updates:
        task.description = updates["description"]
    if "priority" in updates and updates["priority"] is not None:
        task.priority = int(updates["priority"])
    if "estimated_minutes" in updates and updates["estimated_minutes"] is not None:
        task.estimated_minutes = int(updates["estimated_minutes"])
    if "due_at" in updates:
        task.due_at = updates["due_at"]

    db.add(task)
    db.commit()
    db.refresh(task)
    return _serialize_task(task)


# PUBLIC_INTERFACE
def delete_task(db: Session, user_id: int, task_id: int) -> bool:
    """Delete a task owned by the current user."""
    require_user(db, user_id)
    task = db.get(Task, task_id)
    if not task or task.user_id != user_id:
        raise LookupError("Task not found")
    db.delete(task)
    db.commit()
    return True


def _cascade_subtasks_completion(subtask: Subtask, complete: bool):
    """Recursively set completion on subtask children."""
    subtask.is_completed = complete
    for ch in subtask.children:
        _cascade_subtasks_completion(ch, complete)


# PUBLIC_INTERFACE
def mark_task_complete(db: Session, user_id: int, task_id: int, complete: bool = True, cascade: bool = False) -> Dict[str, Any]:
    """Mark a task complete/incomplete with optional cascade to all subtasks."""
    require_user(db, user_id)
    task = db.get(Task, task_id)
    if not task or task.user_id != user_id:
        raise LookupError("Task not found")

    task.is_completed = bool(complete)
    if cascade:
        for st in task.subtasks:
            _cascade_subtasks_completion(st, bool(complete))

    db.add(task)
    db.commit()
    db.refresh(task)
    return _serialize_task(task)


# PUBLIC_INTERFACE
def list_subtasks(db: Session, user_id: int, task_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """List subtasks for the current user.

    If task_id is provided, list subtasks for that task only.
    """
    require_user(db, user_id)

    if task_id is not None:
        # Ensure task belongs to user
        task = db.get(Task, task_id)
        if not task or task.user_id != user_id:
            raise LookupError("Task not found")
        subtasks = task.subtasks
        return [_serialize_subtask(st, parent_task_for_inheritance=task) for st in subtasks]

    # Otherwise, list all subtasks across user's tasks
    stmt = select(Subtask).join(Task, Task.id == Subtask.task_id).where(Task.user_id == user_id)
    subtasks = list(db.scalars(stmt))
    return [_serialize_subtask(st) for st in subtasks]


# PUBLIC_INTERFACE
def create_subtask(
    db: Session,
    user_id: int,
    task_id: int,
    title: str,
    description: Optional[str],
    parent_subtask_id: Optional[int],
    order_index: Optional[int],
) -> Dict[str, Any]:
    """Create a new subtask under a task (and optional parent_subtask)."""
    require_user(db, user_id)
    task = db.get(Task, task_id)
    if not task or task.user_id != user_id:
        raise LookupError("Task not found")

    parent_subtask: Optional[Subtask] = None
    if parent_subtask_id is not None:
        parent_subtask = db.get(Subtask, parent_subtask_id)
        if not parent_subtask or parent_subtask.task_id != task_id:
            raise LookupError("Parent subtask not found under this task")

    subtask = Subtask(
        task_id=task.id,
        parent_subtask_id=parent_subtask.id if parent_subtask else None,
        title=title.strip(),
        description=(description or None),
        order_index=int(order_index) if order_index is not None else 0,
    )
    db.add(subtask)
    db.commit()
    db.refresh(subtask)
    return _serialize_subtask(subtask, parent_task_for_inheritance=task)


# PUBLIC_INTERFACE
def get_subtask(db: Session, user_id: int, subtask_id: int) -> Dict[str, Any]:
    """Retrieve a subtask for the current user by id."""
    require_user(db, user_id)

    subtask = db.get(Subtask, subtask_id)
    if not subtask:
        raise LookupError("Subtask not found")
    # Verify ownership via the parent task
    task = db.get(Task, subtask.task_id)
    if not task or task.user_id != user_id:
        raise LookupError("Subtask not found")
    return _serialize_subtask(subtask, parent_task_for_inheritance=task)


# PUBLIC_INTERFACE
def update_subtask(
    db: Session,
    user_id: int,
    subtask_id: int,
    updates: Dict[str, Any],
) -> Dict[str, Any]:
    """Update a subtask fields."""
    require_user(db, user_id)

    subtask = db.get(Subtask, subtask_id)
    if not subtask:
        raise LookupError("Subtask not found")

    task = db.get(Task, subtask.task_id)
    if not task or task.user_id != user_id:
        raise LookupError("Subtask not found")

    if "title" in updates and updates["title"] is not None:
        subtask.title = str(updates["title"]).strip()
    if "description" in updates:
        subtask.description = updates["description"]
    if "order_index" in updates and updates["order_index"] is not None:
        subtask.order_index = int(updates["order_index"])
    if "parent_subtask_id" in updates:
        new_parent_id = updates["parent_subtask_id"]
        if new_parent_id is None:
            subtask.parent_subtask_id = None
        else:
            parent = db.get(Subtask, int(new_parent_id))
            if not parent or parent.task_id != task.id:
                raise LookupError("New parent subtask not found under this task")
            # Prevent setting parent to itself or its descendants
            if parent.id == subtask.id:
                raise ValueError("Cannot set subtask as its own parent")
            # Check not moving under a descendant
            if _is_descendant(parent, subtask):
                raise ValueError("Cannot set a descendant as parent")
            subtask.parent_subtask_id = parent.id

    db.add(subtask)
    db.commit()
    db.refresh(subtask)
    return _serialize_subtask(subtask, parent_task_for_inheritance=task)


def _is_descendant(candidate_parent: Subtask, potential_ancestor: Subtask) -> bool:
    """Return True if candidate_parent is a descendant of potential_ancestor."""
    node = candidate_parent
    while node is not None:
        if node.parent_subtask_id == potential_ancestor.id:
            return True
        node = node.parent
    return False


# PUBLIC_INTERFACE
def delete_subtask(db: Session, user_id: int, subtask_id: int) -> bool:
    """Delete a subtask by id for the current user."""
    require_user(db, user_id)
    subtask = db.get(Subtask, subtask_id)
    if not subtask:
        raise LookupError("Subtask not found")
    task = db.get(Task, subtask.task_id)
    if not task or task.user_id != user_id:
        raise LookupError("Subtask not found")
    db.delete(subtask)
    db.commit()
    return True


# PUBLIC_INTERFACE
def mark_subtask_complete(
    db: Session,
    user_id: int,
    subtask_id: int,
    complete: bool = True,
    cascade: bool = False,
) -> Dict[str, Any]:
    """Mark a subtask complete/incomplete with optional cascade to children."""
    require_user(db, user_id)
    subtask = db.get(Subtask, subtask_id)
    if not subtask:
        raise LookupError("Subtask not found")
    task = db.get(Task, subtask.task_id)
    if not task or task.user_id != user_id:
        raise LookupError("Subtask not found")

    subtask.is_completed = bool(complete)
    if cascade:
        for ch in subtask.children:
            _cascade_subtasks_completion(ch, bool(complete))

    db.add(subtask)
    db.commit()
    db.refresh(subtask)
    return _serialize_subtask(subtask, parent_task_for_inheritance=task)
