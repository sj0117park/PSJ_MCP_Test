"""Practical MCP v2 server demonstrating explicit cross-call state handles.

The 2026-07-28 MCP specification is stateless at the protocol layer. This
server therefore mints an opaque workspace handle and requires callers to pass
that handle to later tool calls.

State is intentionally kept in process memory for a small, database-free
example. It is lost when the process restarts and is not shared across replicas.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from mcp.server import MCPServer

LOGGER = logging.getLogger(__name__)

WORKSPACE_TTL_SECONDS = 60 * 60
MAX_WORKSPACES = 1_000


@dataclass(slots=True)
class TaskItem:
    id: int
    title: str
    completed: bool = False


@dataclass(slots=True)
class Workspace:
    name: str
    created_at: float
    last_accessed_at: float
    next_task_id: int = 1
    tasks: list[TaskItem] = field(default_factory=list)


# Process-local state. The opaque key is the explicit cross-call state handle.
_workspaces: dict[str, Workspace] = {}
_state_lock = threading.RLock()

mcp = MCPServer(
    "task-workspace",
    description=(
        "A database-free task workspace that demonstrates MCP v2 cross-call "
        "state with explicit server-minted handles."
    ),
    version="1.0.0",
)


def _now() -> float:
    return time.time()


def _remove_expired_workspaces(now: float) -> None:
    expired_handles = [
        handle
        for handle, workspace in _workspaces.items()
        if now - workspace.last_accessed_at > WORKSPACE_TTL_SECONDS
    ]
    for handle in expired_handles:
        del _workspaces[handle]


def _get_workspace(workspace_handle: str) -> Workspace:
    """Resolve and refresh an explicit state handle."""
    now = _now()
    with _state_lock:
        _remove_expired_workspaces(now)
        workspace = _workspaces.get(workspace_handle)
        if workspace is None:
            raise ValueError(
                "Unknown or expired workspace_handle. "
                "Call create_workspace to obtain a new handle."
            )
        workspace.last_accessed_at = now
        return workspace


def _task_to_dict(task: TaskItem) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "completed": task.completed,
    }


def _workspace_summary(workspace_handle: str, workspace: Workspace) -> dict[str, Any]:
    completed_count = sum(task.completed for task in workspace.tasks)
    return {
        "workspace_handle": workspace_handle,
        "name": workspace.name,
        "task_count": len(workspace.tasks),
        "completed_count": completed_count,
        "open_count": len(workspace.tasks) - completed_count,
        "expires_after_idle_seconds": WORKSPACE_TTL_SECONDS,
    }


@mcp.tool()
def create_workspace(name: str) -> dict[str, Any]:
    """Create an in-memory task workspace and return its opaque state handle.

    Keep the returned workspace_handle and pass it to subsequent tool calls.
    """
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("name must not be empty")
    if len(normalized_name) > 100:
        raise ValueError("name must be 100 characters or fewer")

    now = _now()
    with _state_lock:
        _remove_expired_workspaces(now)
        if len(_workspaces) >= MAX_WORKSPACES:
            raise RuntimeError("Workspace capacity reached. Try again later.")

        workspace_handle = f"ws_{uuid4().hex}"
        workspace = Workspace(
            name=normalized_name,
            created_at=now,
            last_accessed_at=now,
        )
        _workspaces[workspace_handle] = workspace

    LOGGER.info("Created workspace %s", workspace_handle)
    return {
        **_workspace_summary(workspace_handle, workspace),
        "message": "Workspace created. Reuse workspace_handle in later calls.",
    }


@mcp.tool()
def add_task(workspace_handle: str, title: str) -> dict[str, Any]:
    """Add a task to an existing workspace identified by workspace_handle."""
    normalized_title = title.strip()
    if not normalized_title:
        raise ValueError("title must not be empty")
    if len(normalized_title) > 200:
        raise ValueError("title must be 200 characters or fewer")

    with _state_lock:
        workspace = _get_workspace(workspace_handle)
        task = TaskItem(id=workspace.next_task_id, title=normalized_title)
        workspace.next_task_id += 1
        workspace.tasks.append(task)

        return {
            "workspace": _workspace_summary(workspace_handle, workspace),
            "added_task": _task_to_dict(task),
        }


@mcp.tool()
def list_tasks(
    workspace_handle: str,
    include_completed: bool = True,
) -> dict[str, Any]:
    """List tasks stored by an earlier call using the same workspace handle."""
    with _state_lock:
        workspace = _get_workspace(workspace_handle)
        tasks = [
            _task_to_dict(task)
            for task in workspace.tasks
            if include_completed or not task.completed
        ]
        return {
            "workspace": _workspace_summary(workspace_handle, workspace),
            "tasks": tasks,
        }


@mcp.tool()
def complete_task(workspace_handle: str, task_id: int) -> dict[str, Any]:
    """Mark one task complete in the workspace referenced by the handle."""
    with _state_lock:
        workspace = _get_workspace(workspace_handle)
        task = next((item for item in workspace.tasks if item.id == task_id), None)
        if task is None:
            raise ValueError(f"No task with id={task_id} exists in this workspace")

        task.completed = True
        return {
            "workspace": _workspace_summary(workspace_handle, workspace),
            "completed_task": _task_to_dict(task),
        }


@mcp.tool()
def delete_workspace(workspace_handle: str) -> dict[str, Any]:
    """Delete a workspace and invalidate its cross-call state handle."""
    with _state_lock:
        workspace = _get_workspace(workspace_handle)
        summary = _workspace_summary(workspace_handle, workspace)
        del _workspaces[workspace_handle]

    LOGGER.info("Deleted workspace %s", workspace_handle)
    return {
        "deleted": True,
        "workspace": summary,
        "message": "The workspace_handle is now invalid.",
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8888,
        streamable_http_path="/mcp",
    )
