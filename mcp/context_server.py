import os
import json
from typing import Dict, Any

try:
    from fastmcp import FastMCP
    mcp = FastMCP("project-context-server")
except ImportError:
    # Fallback structure if FastMCP not installed locally
    class FastMCP:
        def __init__(self, name: str):
            self.name = name
        def tool(self):
            def decorator(func):
                return func
            return decorator
    mcp = FastMCP("project-context-server")


@mcp.tool()
def get_project_context(repo_path: str = ".") -> Dict[str, Any]:
    """Expose codebase structure, conventions, and rules to agent fleet workers."""
    rules_path = os.path.join(repo_path, "RULES.md")
    rules_content = ""
    if os.path.exists(rules_path):
        with open(rules_path, "r", encoding="utf-8") as f:
            rules_content = f.read()
    else:
        rules_content = "# Project Rules\n1. Ensure strict defensive coding.\n2. Write unit tests for all features."

    return {
        "repo_path": os.path.abspath(repo_path),
        "rules": rules_content,
        "supported_adapters": ["aider", "claude_code", "cline", "mock_agent"],
        "coordination_mode": "file-based (/coordination)",
    }


@mcp.tool()
def list_coordination_logs(repo_path: str = ".") -> list:
    """Retrieve shared messages from the /coordination directory."""
    coord_dir = os.path.join(repo_path, "coordination")
    messages = []
    if os.path.exists(coord_dir):
        for fname in sorted(os.listdir(coord_dir)):
            if fname.endswith(".json"):
                fpath = os.path.join(coord_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        messages.append(json.load(f))
                except Exception:
                    pass
    return messages


if __name__ == "__main__":
    print("FastMCP Context Server ready.")
