import os
from valet.config import config_manager
from valet.monitor import get_system_stats

def handle_git() -> str:
    """Check git status in current directory."""
    try:
        from git import Repo
        from git.exc import InvalidGitRepositoryError
        try:
            repo = Repo(os.getcwd(), search_parent_directories=True)
            branch = repo.active_branch.name
            is_dirty = repo.is_dirty()
            status = "dirty ✗" if is_dirty else "clean ✓"
            return f"Git Status:\nRepository: {repo.working_dir}\nBranch: [cyan]{branch}[/cyan]\nState: [yellow]{status}[/yellow]"
        except InvalidGitRepositoryError:
            return "Current directory is not a Git repository. I suggest initializing one before you break something."
    except ImportError:
        return "GitPython is not installed. Please install it to use Git features."

def handle_todo(action: str, item: str = "") -> str:
    """Manage todos."""
    todos = config_manager.todos
    if action == "list":
        if not todos:
            return "Your todo list is empty. Remarkable efficiency or sheer laziness?"
        return "Tasks:\n" + "\n".join([f"• {t}" for t in todos])
    elif action == "add" and item:
        todos.append(item)
        config_manager.save_todos()
        return f"Added: '{item}'. Try not to procrastinate on this one."
    elif action == "clear":
        config_manager.todos = []
        config_manager.save_todos()
        return "Cleared all tasks. A clean slate, or giving up entirely?"
    return "Usage: todo [list|add <item>|clear]"
