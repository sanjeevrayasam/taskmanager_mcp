
# Task Manager (FastMCP + SQLite)

A simple task management server built with** **[FastMCP](https://github.com/modelcontextprotocol/python-sdk) and SQLite. Provides CRUD operations on tasks, exposed as tools and resources for LLM-powered workflows.

## Features

* **Add Task** : Create a new task with a description.
* **Update Task** : Set progress (0–100%) on existing tasks.
* **Delete Task** : Remove tasks by ID.
* **List Tasks** : List all tasks and their progress.
* **Resources** :
* `tasks://all` returns all tasks as JSON.
* `tasks://{task_id}` returns one task or an error JSON.
* `config://task-priorities` returns static priority mappings.

## Getting Started

### Prerequisites

* Python 3.10+
* uv

### Installation

```bash
# Clone the repo
git clone https://github.com/sanjeevrayasam/taskmanager_mcp.git
cd taskmanager

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

If using macOS/Linux:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

if windows:

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Running in Development

Start the FastMCP server in dev mode (auto-reloads on changes):

```bash
mcp dev main.py
```

### Running in Production

```bash
mcp run main.py --transport stdio
```

## Usage

Interact via HTTP or CLI through the FastMCP client. Example with Python HTTP client:

```python
from mcp.client import Client

client = Client(transport="http://localhost:8000")

# Add a task
print(client.call("add_task", description="Write tests"))

# List tasks
print(client.call("list_tasks"))

# Get tasks JSON
print(client.request("tasks://all"))
```

## Project Structure

```
├── main.py            # Server and tool/resource definitions
├── tasks.db           # SQLite database (created at runtime)
├── README.md          # This file
├── requirements.txt   # Python dependencies
└── .gitignore
```

This is an open-source project. Feel free to open issues or submit PRs.

## License

* [ ] This project is licensed under the MIT License. See** **[LICENSE](LICENSE) for details.
