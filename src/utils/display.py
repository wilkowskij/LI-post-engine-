"""
Rich terminal display helpers.
"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()


def print_post(post: dict, title: str = "Generated LinkedIn Post") -> None:
    """Pretty-print a post to the terminal."""
    panel = Panel(
        post["text"],
        title=f"[bold blue]{title}[/bold blue]",
        subtitle=f"[dim]{post.get('format', '')} | {post.get('word_count', 0)} words | topic: {post.get('topic', '')}[/dim]",
        border_style="blue",
        padding=(1, 2),
    )
    console.print(panel)


def print_variants(variants: list[dict]) -> None:
    """Display multiple post variants with numbered labels."""
    for i, post in enumerate(variants, 1):
        print_post(post, title=f"Variant {i}: {post.get('format', '').replace('_', ' ').title()}")
        console.print()


def print_queue_summary(summary: list[dict]) -> None:
    """Display Buffer queue status."""
    table = Table(title="Buffer Queue Status", box=box.ROUNDED)
    table.add_column("Profile", style="cyan")
    table.add_column("Pending Posts", justify="center")
    table.add_column("Next Post", style="green")

    for item in summary:
        table.add_row(
            item["profile"],
            str(item["pending_count"]),
            item.get("next_post") or "—",
        )
    console.print(table)


def print_success(message: str) -> None:
    console.print(f"[bold green]✓[/bold green] {message}")


def print_error(message: str) -> None:
    console.print(f"[bold red]✗[/bold red] {message}")


def print_info(message: str) -> None:
    console.print(f"[bold yellow]→[/bold yellow] {message}")
