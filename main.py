import os
import sqlite3
import aiosqlite
import asyncio
import json
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

from mcp.server.fastmcp import Context, FastMCP

# Global DB connection for resources
_db = None

# Create FastMCP server with dependencies
mcp = FastMCP("My App", dependencies=["pandas", "numpy", "aiosqlite"])

@dataclass
class AppContext:
    db: aiosqlite.Connection

async def ensure_db_exists(db_path: str = "tasks.db") -> None:
    """
    Ensure the SQLite database file and tasks table exist.

    Creates the file and the 'tasks' table if they do not already exist.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        None
    """
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        conn.commit()
        conn.close()

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """
    Manage application startup and shutdown.

    On startup ensures the database exists and connects asynchronously.
    On shutdown closes the database connection.

    Args:
        server: The FastMCP server instance.

    Yields:
        AppContext: Holds the async database connection.
    """
    await ensure_db_exists()
    db = await aiosqlite.connect("tasks.db")
    global _db
    _db = db
    try:
        yield AppContext(db=db)
    finally:
        await db.close()
        _db = None

# Pass lifespan to FastMCP server
mcp = FastMCP(
    "My App",
    dependencies=["pandas", "numpy", "aiosqlite"],
    lifespan=app_lifespan
)

# --- Core database functions (can be tested from main) ---
async def add_task_db(db: aiosqlite.Connection, description: str) -> int:
    """
    Insert a new task into the database.

    Args:
        db: Async SQLite connection.
        description: The task description text.

    Returns:
        The ID of the newly created task.
    """
    cursor = await db.execute(
        "INSERT INTO tasks(description) VALUES (?)",
        (description,)
    )
    await db.commit()
    return cursor.lastrowid

async def update_task_db(db: aiosqlite.Connection, task_id: int, progress: int) -> bool:
    """
    Update the progress of an existing task.

    Args:
        db: Async SQLite connection.
        task_id: ID of the task to update.
        progress: New progress percentage (0-100).

    Returns:
        True if the update affected a row, False otherwise.
    """
    cursor = await db.execute(
        "UPDATE tasks SET progress = ? WHERE id = ?",
        (progress, task_id)
    )
    await db.commit()
    return cursor.rowcount > 0

async def delete_task_db(db: aiosqlite.Connection, task_id: int) -> bool:
    """
    Delete a task by its ID.

    Args:
        db: Async SQLite connection.
        task_id: ID of the task to delete.

    Returns:
        True if a task was deleted, False otherwise.
    """
    cursor = await db.execute(
        "DELETE FROM tasks WHERE id = ?",
        (task_id,)
    )
    await db.commit()
    return cursor.rowcount > 0

async def list_tasks_db(db: aiosqlite.Connection) -> list[tuple[int, str, int]]:
    """
    Retrieve all tasks from the database.

    Args:
        db: Async SQLite connection.

    Returns:
        A list of tuples containing (id, description, progress).
    """
    cursor = await db.execute("SELECT id, description, progress FROM tasks")
    rows = await cursor.fetchall()
    return rows

# --- FastMCP tool wrappers ---
@mcp.tool()
async def add_task(ctx: Context, description: str) -> str:
    """
    Add a new task.

    Args:
        ctx: FastMCP request context with DB connection.
        description: Text description of the new task.

    Returns:
        Confirmation message with the new task ID and its description.
    """
    db = ctx.request_context.lifespan_context.db
    task_id = await add_task_db(db, description)
    return f"Added task {task_id}: '{description}'"

@mcp.tool()
async def update_task(ctx: Context, task_id: int, progress: int) -> str:
    """
    Update the progress of an existing task.

    Args:
        ctx: FastMCP request context with DB connection.
        task_id: ID of the task to update.
        progress: New progress percentage (0-100).

    Returns:
        Success message if updated, or not-found message.
    """
    db = ctx.request_context.lifespan_context.db
    success = await update_task_db(db, task_id, progress)
    if success:
        return f"Updated task {task_id} to progress {progress}%"
    return f"Task {task_id} not found."

@mcp.tool()
async def delete_task(ctx: Context, task_id: int) -> str:
    """
    Delete a task by ID.

    Args:
        ctx: FastMCP request context with DB connection.
        task_id: ID of the task to delete.

    Returns:
        Confirmation message if deleted, or not-found message.
    """
    db = ctx.request_context.lifespan_context.db
    success = await delete_task_db(db, task_id)
    if success:
        return f"Deleted task {task_id}."
    return f"Task {task_id} not found."

@mcp.tool()
async def list_tasks(ctx: Context) -> str:
    """
    List all tasks with their progress.

    Args:
        ctx: FastMCP request context with DB connection.

    Returns:
        A formatted string of all tasks, "id: description (progress%)" per line.
    """
    db = ctx.request_context.lifespan_context.db
    tasks = await list_tasks_db(db)
    if not tasks:
        return "No tasks found."
    lines = [f"{tid}: {desc} ({prog}%)" for tid, desc, prog in tasks]
    return "\n".join(lines)

# --- FastMCP resource wrappers ---
@mcp.resource("tasks://all")
async def get_all_tasks() -> str:
    """
    Return every task as a JSON list of objects.

    Returns:
        JSON string of a list of {id, description, progress}.
    """
    db = _db
    rows = await list_tasks_db(db)
    payload = [{"id": tid, "description": desc, "progress": prog} for tid, desc, prog in rows]
    return json.dumps(payload)

@mcp.resource("tasks://{task_id}")
async def get_task(task_id: int) -> str:
    """
    Return one task’s data or an error as JSON.

    Args:
        task_id: ID of the task to fetch.

    Returns:
        JSON string of {id, description, progress} or {error, id}.
    """
    db = _db
    cursor = await db.execute(
        "SELECT id, description, progress FROM tasks WHERE id = ?", (task_id,)
    )
    row = await cursor.fetchone()
    if not row:
        return json.dumps({"error": "Task not found", "id": task_id})
    tid, desc, prog = row
    return json.dumps({"id": tid, "description": desc, "progress": prog})

@mcp.resource("config://task-priorities")
def task_priorities() -> str:
    """
    Provide static mapping of task priority levels.

    Returns:
        JSON string of priority mappings {low, medium, high} -> int.
    """
    return json.dumps({"low": 0, "medium": 1, "high": 2})

# --- Main for testing ---
if __name__ == "__main__":
    mcp.run(transport="stdio")