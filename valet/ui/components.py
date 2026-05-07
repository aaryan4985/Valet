from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static
from textual.reactive import reactive

class Message(Static):
    """A single chat message."""
    
    def __init__(self, sender: str, text: str, is_user: bool = False):
        super().__init__()
        self.sender = sender
        self.text = text
        self.is_user = is_user
        
    def compose(self) -> ComposeResult:
        classes = "message message-user" if self.is_user else "message message-valet"
        yield Vertical(
            Static(self.sender, classes="message-header"),
            Static(self.text),
            classes=classes
        )

class SystemMonitor(Static):
    """Sidebar widget showing live system stats."""
    
    stats_text = reactive("")

    def on_mount(self) -> None:
        self.update_stats()
        self.set_interval(2.0, self.update_stats)

    def update_stats(self) -> None:
        from valet.monitor import get_system_stats
        try:
            stats = get_system_stats()
            self.stats_text = (
                f"[bold cyan]CPU:[/bold cyan] {stats['cpu_percent']}%\n\n"
                f"[bold cyan]RAM:[/bold cyan] {stats['ram_used']} / {stats['ram_total']}\n"
                f"({stats['ram_percent']}%)\n\n"
                f"[bold cyan]Disk Free:[/bold cyan] {stats['disk_free']}\n\n"
                f"[bold cyan]Uptime:[/bold cyan]\n{stats['uptime']}\n\n"
                f"[bold cyan]Weather:[/bold cyan]\n{stats['weather']}"
            )
        except Exception:
            self.stats_text = "Stats unavailable."

    def render(self) -> str:
        return f"[b]SYSTEM STATUS[/b]\n\n{self.stats_text}"
