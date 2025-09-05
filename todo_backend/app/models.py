"""
ORM models for the Todo application.

Includes:
- User: basic user model identified by username
- Task: tasks owned by a user
- Subtask: hierarchical subtasks associated with tasks (supports nested parent-child)
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    """User record, identified by username."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to tasks
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"


class Task(Base):
    """Tasks created by users, with metadata like priority and due date."""
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Priority: use small int 1..5 (1 highest) or 0..n
    priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Estimated time in minutes
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Store due date/time (UTC)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="tasks")

    subtasks: Mapped[List["Subtask"]] = relationship(
        "Subtask",
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title!r} user_id={self.user_id}>"


class Subtask(Base):
    """Subtasks that can be nested via parent_subtask_id under a Task."""
    __tablename__ = "subtasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional parent to enable nested subtasks
    parent_subtask_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("subtasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="subtasks")

    parent: Mapped[Optional["Subtask"]] = relationship(
        "Subtask",
        remote_side="Subtask.id",
        back_populates="children",
    )

    children: Mapped[List["Subtask"]] = relationship(
        "Subtask",
        cascade="all, delete-orphan",
        back_populates="parent",
    )

    def __repr__(self) -> str:
        return f"<Subtask id={self.id} title={self.title!r} task_id={self.task_id} parent_id={self.parent_subtask_id}>"
