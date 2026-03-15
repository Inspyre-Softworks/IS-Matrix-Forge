"""
Shared Rich console and output helpers for IS-Matrix-Forge CLI.

All user-facing print calls should route through this module so that
colour and formatting are consistent across every sub-command.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

# Single global console – stderr=False so output goes to stdout, which is
# what plain print() does.  Use force_terminal=None so Rich auto-detects
# whether the target supports ANSI (falls back to plain text in pipes).
CONSOLE = Console()
ERR_CONSOLE = Console(stderr=True)


# ---------------------------------------------------------------------------
# Branded prefix
# ---------------------------------------------------------------------------

APP_TAG = "[bold cyan]\\[IS-Matrix-Forge][/bold cyan]"


def info(message: str) -> None:
    """Print a plain informational message with the app prefix."""
    CONSOLE.print(f"{APP_TAG} {message}")


def success(message: str) -> None:
    """Print a success (green) message with the app prefix."""
    CONSOLE.print(f"{APP_TAG} [bold green]{message}[/bold green]")


def warning(message: str) -> None:
    """Print a warning (yellow) message with the app prefix."""
    CONSOLE.print(f"{APP_TAG} [bold yellow]Warning:[/bold yellow] {message}")


def error(message: str) -> None:
    """Print an error (red) message with the app prefix."""
    CONSOLE.print(f"{APP_TAG} [bold red]Error:[/bold red] {message}")


def no_presets_panel(presets_dir: str) -> None:
    """Render a styled warning panel when no preset files are found."""
    body = Text.assemble(
        ("No preset files were found in:\n", "yellow"),
        (f"  {presets_dir}\n", "bold white"),
        ("Run  ", "dim"),
        ("led-matrix install-presets", "bold cyan"),
        ("  to download them.", "dim"),
    )
    CONSOLE.print(
        Panel(
            body,
            title="[bold yellow]IS-Matrix-Forge[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


__all__ = [
    "CONSOLE",
    "ERR_CONSOLE",
    "APP_TAG",
    "info",
    "success",
    "warning",
    "error",
    "no_presets_panel",
]
