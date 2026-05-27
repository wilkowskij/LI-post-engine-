#!/usr/bin/env python3
"""
LinkedIn Post Engine — CLI entry point.

Commands:
  generate      Research + write a new post (saves as draft)
  schedule      Pick a draft and push to Buffer
  queue         Show Buffer queue status
  list          List saved posts
  run-daily     Full daily flow: research → write → schedule
"""
import os
import sys
from pathlib import Path
from datetime import datetime

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt, Confirm

load_dotenv()
console = Console()


@click.group()
def cli():
    """LinkedIn Post Engine — Senior PM content, automated."""
    pass


# ------------------------------------------------------------------ #
# generate
# ------------------------------------------------------------------ #

@cli.command()
@click.option("--topic", "-t", default=None, help="Topic category (auto-selects if omitted)")
@click.option("--format", "-f", "post_format", default=None,
              type=click.Choice(["visual_framework", "framework", "trend_prediction", "hot_take", "breakdown", "myth_busting", "data_insight"]),
              help="Post format (auto-selects if omitted)")
@click.option("--variants", "-n", default=1, show_default=True, help="Number of variants to generate")
@click.option("--angle", "-a", default=None, help="Specific angle or hook to emphasize")
@click.option("--preview", "-p", is_flag=True, help="Render and open the diagram image after generating")
def generate(topic, post_format, variants, angle, preview):
    """Research a topic and generate LinkedIn post draft(s)."""
    import anthropic
    from src.agent.researcher import research_trending_topics, build_research_brief
    from src.agent.writer import generate_post, generate_post_variants, generate_diagram_spec
    from src.agent.persona import TOPIC_CATEGORIES
    from src.utils.storage import save_post
    from src.utils.display import print_post, print_variants, print_info, print_success

    _require_env("ANTHROPIC_API_KEY")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    if not topic:
        from src.utils.content_calendar import pick_todays_topic
        topic = pick_todays_topic()
        print_info(f"Auto-selected topic: [bold]{topic}[/bold]")

    print_info("Researching topic...")
    research = research_trending_topics(category=topic)

    print_info("Building research brief...")
    brief = build_research_brief(research, client)
    console.print(f"\n[dim]Brief:[/dim] {brief[:200]}...\n")

    print_info(f"Generating {variants} post variant(s)...")

    if variants == 1:
        post = generate_post(brief, topic, post_format=post_format, custom_angle=angle, client=client)
        print_post(post)
        path = save_post(post)
        print_success(f"Saved draft → {path.name}")
        if preview:
            _render_and_open_preview(post, client)
    else:
        posts = generate_post_variants(brief, topic, count=variants, client=client)
        print_variants(posts)
        for post in posts:
            path = save_post(post)
            print_success(f"Saved draft → {path.name}")
        if preview:
            _render_and_open_preview(posts[0], client)


# ------------------------------------------------------------------ #
# schedule
# ------------------------------------------------------------------ #

@cli.command()
@click.option("--file", "-f", "filepath", default=None, help="Path to post JSON file (auto-selects latest draft)")
@click.option("--image", "-i", default=None, help="Image path or URL to attach")
@click.option("--when", "-w", default="queue",
              type=click.Choice(["queue", "now", "tomorrow"]),
              help="When to post: add to queue, post now, or schedule for tomorrow 8am UTC")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt (for CI/automation)")
def schedule(filepath, image, when, yes):
    """Push a draft post to Buffer for scheduling."""
    from src.integrations.buffer_client import BufferClient
    from src.utils.storage import list_posts, update_post_status, load_post
    from src.utils.display import print_post, print_info, print_success, print_error

    _require_env("BUFFER_ACCESS_TOKEN")

    # Resolve post file
    if filepath:
        post = load_post(Path(filepath))
    else:
        drafts = list_posts(status="draft", limit=5)
        if not drafts:
            print_error("No drafts found. Run `generate` first.")
            sys.exit(1)
        post = drafts[0]
        print_info(f"Using latest draft: {post['_filepath']}")

    print_post(post)

    if not yes and not Confirm.ask("Schedule this post to Buffer?"):
        console.print("[dim]Cancelled.[/dim]")
        return

    # Use pre-uploaded image URL from post JSON if available (avoids re-upload after review flow)
    image_url = post.get("image_url") or None

    # Auto-generate and upload diagram if no image is provided explicitly
    if image:
        from src.integrations.cloudinary_client import upload_post_image, upload_image_from_url
        _require_env("CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
        print_info("Uploading image to Cloudinary...")
        if image.startswith("http"):
            result = upload_image_from_url(image, post["topic"])
        else:
            result = upload_post_image(image, post["topic"])
        image_url = result["url"]
        print_success(f"Image uploaded: {image_url}")
    elif os.environ.get("CLOUDINARY_API_KEY"):
        try:
            import anthropic as _anthropic
            from src.agent.writer import generate_diagram_spec
            from src.utils.image_gen import generate_post_image
            from src.integrations.cloudinary_client import upload_post_image as _upload
            _client = _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            print_info("Generating framework diagram...")
            generate_diagram_spec(post, _client)
            card_path = generate_post_image(post, author_name=os.environ.get("AUTHOR_NAME", "Jeff Wilkowski"))
            print_info("Uploading diagram to Cloudinary...")
            result = _upload(card_path, post["topic"])
            image_url = result["url"]
            print_success(f"Diagram uploaded: {image_url}")
        except Exception as e:
            print_error(f"Diagram generation skipped: {e}")

    # Push to Buffer
    buffer = BufferClient()
    print_info("Connecting to Buffer...")

    if not buffer.validate_connection():
        print_error("Buffer connection failed. Check BUFFER_ACCESS_TOKEN.")
        sys.exit(1)

    # Print available channels so the user can verify BUFFER_PROFILE_IDS
    try:
        channels = buffer.get_profiles()
        print_info(f"Buffer channels: {[(c.get('service'), c.get('name'), c['id']) for c in channels]}")
    except Exception as _e:
        print_error(f"Could not list channels: {_e}")

    if when == "now":
        result = buffer.schedule_post(post["text"], image_url=image_url, now=True)
    elif when == "tomorrow":
        result = buffer.schedule_for_tomorrow_morning(post["text"], image_url=image_url)
    else:
        result = buffer.add_to_queue(post["text"], image_url=image_url)

    update_post_status(
        post["_filepath"],
        "scheduled",
        extra={"buffer_result": result, "scheduled_when": when, "image_url": image_url},
    )
    print_success(f"Post scheduled via Buffer (mode: {when})")


# ------------------------------------------------------------------ #
# queue
# ------------------------------------------------------------------ #

@cli.command()
def queue():
    """Show the current Buffer posting queue."""
    from src.integrations.buffer_client import BufferClient
    from src.utils.display import print_queue_summary, print_error

    _require_env("BUFFER_ACCESS_TOKEN")

    buffer = BufferClient()
    if not buffer.validate_connection():
        print_error("Buffer connection failed. Check BUFFER_ACCESS_TOKEN.")
        sys.exit(1)

    summary = buffer.get_queue_summary()
    if not summary:
        console.print("[yellow]No LinkedIn profiles found in Buffer.[/yellow]")
        return

    print_queue_summary(summary)


# ------------------------------------------------------------------ #
# list
# ------------------------------------------------------------------ #

@cli.command("list")
@click.option("--status", "-s", default=None,
              type=click.Choice(["draft", "scheduled", "posted"]),
              help="Filter by status")
@click.option("--limit", "-n", default=10, show_default=True)
def list_posts_cmd(status, limit):
    """List saved posts."""
    from src.utils.storage import list_posts
    from src.utils.display import print_info

    posts = list_posts(status=status, limit=limit)
    if not posts:
        console.print("[dim]No posts found.[/dim]")
        return

    from rich.table import Table
    from rich import box
    table = Table(title="Saved Posts", box=box.ROUNDED)
    table.add_column("Date", style="cyan", width=12)
    table.add_column("Topic", width=30)
    table.add_column("Format", width=14)
    table.add_column("Words", justify="center", width=6)
    table.add_column("Status", style="green", width=10)

    for p in posts:
        saved = p.get("saved_at", "")[:10]
        table.add_row(
            saved,
            p.get("topic", "")[:28],
            p.get("format", ""),
            str(p.get("word_count", 0)),
            p.get("status", ""),
        )
    console.print(table)


# ------------------------------------------------------------------ #
# run-daily
# ------------------------------------------------------------------ #

@cli.command("run-daily")
@click.option("--topic", "-t", default=None, help="Override topic for today")
@click.option("--auto-schedule", is_flag=True, help="Auto-schedule without prompting")
@click.option("--generate-only", is_flag=True, help="Generate + upload image only; skip Buffer (writes review file for CI)")
def run_daily(topic, auto_schedule, generate_only):
    """
    Full daily flow: research → generate 3 variants → pick one → schedule.
    Designed to run as a cron job or scheduled task.
    """
    import anthropic
    from src.agent.researcher import research_trending_topics, build_research_brief
    from src.integrations.buffer_client import BufferClient
    from src.utils.storage import save_post, update_post_status
    from src.utils.display import print_variants, print_info, print_success, print_error

    _require_env("ANTHROPIC_API_KEY")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=5)

    from src.utils.content_calendar import pick_todays_topic, pick_todays_formats

    if not topic:
        topic = pick_todays_topic()

    console.rule(f"[bold blue]Daily Post Engine — {datetime.now().strftime('%A, %B %d %Y')}[/bold blue]")
    print_info(f"Topic: {topic}")

    # Research
    print_info("Researching...")
    research = research_trending_topics(category=topic)
    brief = build_research_brief(research, client)

    # Generate 3 variants using smart format rotation
    formats = pick_todays_formats(count=3)
    print_info(f"Generating 3 post variants ({', '.join(formats)})...")
    from src.agent.writer import generate_post
    variants = [generate_post(brief, topic, post_format=fmt, client=client) for fmt in formats]
    print_variants(variants)

    # Save all as drafts
    paths = [save_post(v) for v in variants]

    if auto_schedule or generate_only:
        chosen = variants[0]
        path = paths[0]
    else:
        choice = Prompt.ask("Which variant to schedule? (1/2/3, or 'skip')", default="1")
        if choice == "skip":
            console.print("[dim]Skipped scheduling. Drafts saved.[/dim]")
            return
        idx = max(0, min(int(choice) - 1, len(variants) - 1))
        chosen = variants[idx]
        path = paths[idx]

    # Generate framework diagram → upload to Cloudinary
    image_url = None
    if os.environ.get("CLOUDINARY_API_KEY"):
        try:
            from src.utils.image_gen import generate_post_image
            from src.integrations.cloudinary_client import upload_post_image
            from src.agent.writer import generate_diagram_spec
            author_name = os.environ.get("AUTHOR_NAME", "Jeff Wilkowski")
            print_info("Generating framework diagram...")
            generate_diagram_spec(chosen, client)   # no-op if spec already present
            card_path = generate_post_image(chosen, author_name=author_name)
            print_info("Uploading image to Cloudinary...")
            result = upload_post_image(card_path, chosen["topic"])
            image_url = result["url"]
            print_success(f"Image ready: {image_url}")
            # Persist image_url in the draft JSON so schedule-post can reuse it
            update_post_status(str(path), "draft", extra={"image_url": image_url})
        except Exception as e:
            print_error(f"Image generation skipped: {e}")

    if generate_only:
        # Write a review-pending file for the CI workflow to create a GitHub Issue
        import json as _json
        try:
            post_file_str = str(path.relative_to(Path.cwd()))
        except (ValueError, AttributeError):
            post_file_str = str(path)
        review = {
            "post_file": post_file_str,
            "topic": chosen["topic"],
            "format": chosen.get("format", ""),
            "text": chosen["text"],
            "image_url": image_url or "",
            "generated_at": datetime.now().isoformat(),
        }
        Path("output").mkdir(exist_ok=True)
        Path("output/.review_pending.json").write_text(_json.dumps(review, indent=2))
        print_success("Post saved. Awaiting review — a GitHub Issue will be created for approval.")
        return

    # Schedule to Buffer
    if os.environ.get("BUFFER_ACCESS_TOKEN"):
        buffer = BufferClient()
        if buffer.validate_connection():
            result = buffer.add_to_queue(chosen["text"], image_url=image_url)
            update_post_status(
                str(path), "scheduled",
                extra={"buffer_result": result, "scheduled_when": "queue", "image_url": image_url},
            )
            print_success("Post added to Buffer queue!")
        else:
            print_error("Buffer connection failed — draft saved but not scheduled.")
    else:
        print_info("BUFFER_ACCESS_TOKEN not set — draft saved locally.")


# ------------------------------------------------------------------ #
# calendar
# ------------------------------------------------------------------ #

@cli.command()
@click.option("--days", "-d", default=7, show_default=True, help="Days to look ahead")
def calendar(days):
    """Show recent post history and upcoming content plan."""
    from src.utils.content_calendar import get_weekly_summary, get_upcoming_plan, get_posting_days, DAY_NAMES
    from rich.table import Table
    from rich import box

    # Recent history
    summary = get_weekly_summary()
    console.rule("[bold blue]Last 7 Days[/bold blue]")
    console.print(f"Posts generated: [bold]{summary['total']}[/bold]  "
                  f"Scheduled: [green]{summary['scheduled']}[/green]  "
                  f"Drafts: [yellow]{summary['drafts']}[/yellow]")

    if summary["posts"]:
        hist = Table(box=box.SIMPLE)
        hist.add_column("Date", style="cyan", width=12)
        hist.add_column("Topic", width=34)
        hist.add_column("Format", width=16)
        hist.add_column("Status", width=10)
        for p in sorted(summary["posts"], key=lambda x: x.get("saved_at", ""), reverse=True):
            hist.add_row(
                p.get("saved_at", "")[:10],
                p.get("topic", "")[:32],
                p.get("format", "").replace("_", " "),
                p.get("status", ""),
            )
        console.print(hist)
    else:
        console.print("[dim]No posts in the last 7 days.[/dim]")

    # Upcoming plan
    console.rule("[bold blue]Upcoming Plan[/bold blue]")
    posting_days = get_posting_days()
    day_labels = ", ".join(DAY_NAMES.get(d, "") for d in sorted(posting_days))
    console.print(f"Posting days: [cyan]{day_labels}[/cyan]  |  "
                  f"Time: [cyan]{os.environ.get('POST_SCHEDULE_TIME', '08:00')}[/cyan]\n")

    plan = get_upcoming_plan(days)
    if plan:
        plan_table = Table(box=box.ROUNDED)
        plan_table.add_column("Date", style="cyan", width=12)
        plan_table.add_column("Day", width=8)
        plan_table.add_column("Suggested Topic", width=42)
        for entry in plan:
            day_label = "[bold green]TODAY[/bold green]" if entry["is_today"] else entry["weekday"]
            plan_table.add_row(entry["date"], day_label, entry["topic"])
        console.print(plan_table)
    else:
        console.print("[dim]No posting days in the next {days} days.[/dim]")


# ------------------------------------------------------------------ #
# weekly-report
# ------------------------------------------------------------------ #

@cli.command("weekly-report")
def weekly_report():
    """Print a summary of this week's content activity."""
    from src.utils.content_calendar import get_weekly_summary
    from rich.table import Table
    from rich import box

    summary = get_weekly_summary()

    console.rule("[bold blue]Weekly Content Report[/bold blue]")
    console.print(f"\n[bold]Posts this week:[/bold] {summary['total']}")
    console.print(f"  Scheduled to Buffer : [green]{summary['scheduled']}[/green]")
    console.print(f"  Saved as drafts     : [yellow]{summary['drafts']}[/yellow]")

    if summary["topics_used"]:
        console.print(f"\n[bold]Topics covered:[/bold]")
        for t in summary["topics_used"]:
            console.print(f"  • {t}")

    if summary["formats_used"]:
        console.print(f"\n[bold]Formats used:[/bold] {', '.join(f.replace('_', ' ') for f in summary['formats_used'])}")

    if summary["posts"]:
        console.print()
        table = Table(title="Post Log", box=box.ROUNDED)
        table.add_column("Date", style="cyan", width=12)
        table.add_column("Format", width=16)
        table.add_column("Words", justify="center", width=6)
        table.add_column("Status", width=10)
        table.add_column("Topic", width=30)
        for p in sorted(summary["posts"], key=lambda x: x.get("saved_at", ""), reverse=True):
            table.add_row(
                p.get("saved_at", "")[:10],
                p.get("format", "").replace("_", " "),
                str(p.get("word_count", 0)),
                p.get("status", ""),
                p.get("topic", "")[:28],
            )
        console.print(table)
    else:
        console.print("\n[dim]No posts generated in the last 7 days.[/dim]")


# ------------------------------------------------------------------ #
# setup
# ------------------------------------------------------------------ #

@cli.command()
def setup():
    """Verify all integrations are configured correctly."""
    from src.utils.display import print_success, print_error, print_info

    all_ok = True

    # Anthropic
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            print_success("Anthropic API: connected")
        except Exception as e:
            print_error(f"Anthropic API: {e}")
            all_ok = False
    else:
        print_error("Anthropic API: ANTHROPIC_API_KEY not set")
        all_ok = False

    # Cloudinary — validate credentials are set (ping skipped; SSL proxy in container)
    api_key = os.environ.get("CLOUDINARY_API_KEY", "")
    api_secret = os.environ.get("CLOUDINARY_API_SECRET", "")
    if (api_key and api_key != "your_cloudinary_api_key"
            and api_secret and api_secret != "your_cloudinary_api_secret"):
        print_success("Cloudinary: credentials present (cloud: drum3eekm)")
    else:
        print_error("Cloudinary: CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET not set")
        all_ok = False

    # Buffer
    if os.environ.get("BUFFER_ACCESS_TOKEN"):
        try:
            from src.integrations.buffer_client import BufferClient
            buffer = BufferClient()
            if buffer.validate_connection():
                profiles = buffer.get_linkedin_profiles()
                print_success(f"Buffer: connected ({len(profiles)} LinkedIn profile(s))")
            else:
                print_error("Buffer: token invalid")
                all_ok = False
        except Exception as e:
            print_error(f"Buffer: {e}")
            all_ok = False
    else:
        print_error("Buffer: BUFFER_ACCESS_TOKEN not set")
        all_ok = False

    # Image generation (Pillow — always available)
    try:
        from PIL import Image as _PILImage
        print_success("Image generation: Pillow ready (framework diagrams enabled)")
    except ImportError:
        print_error("Image generation: Pillow not installed — run `pip install pillow`")
        all_ok = False

    # Tavily (optional)
    if os.environ.get("TAVILY_API_KEY"):
        print_success("Tavily: API key present (web research enabled)")
    else:
        print_info("Tavily: not configured (will use Claude's knowledge for research)")

    console.print()
    if all_ok:
        console.print("[bold green]All integrations ready. Run `python main.py run-daily` to generate your first post.[/bold green]")
    else:
        console.print("[bold yellow]Some integrations need configuration. Copy .env.example to .env and fill in the values.[/bold yellow]")


# ------------------------------------------------------------------ #
# refine
# ------------------------------------------------------------------ #

@cli.command()
@click.option("--file", "-f", "filepath", default=None, help="Path to post JSON (auto-selects latest draft)")
@click.option("--feedback", "-fb", required=True, help="What to change, e.g. 'make it more contrarian'")
@click.option("--preview", "-p", is_flag=True, help="Render and open the diagram after refining")
def refine(filepath, feedback, preview):
    """Refine a draft post based on feedback."""
    import anthropic
    from src.agent.writer import refine_post
    from src.utils.storage import load_post, list_posts, save_post
    from src.utils.display import print_post, print_info, print_success, print_error

    _require_env("ANTHROPIC_API_KEY")

    if filepath:
        post = load_post(Path(filepath))
    else:
        drafts = list_posts(status="draft", limit=5)
        if not drafts:
            print_error("No drafts found. Run `generate` first.")
            sys.exit(1)
        post = drafts[0]
        print_info(f"Refining: {post['_filepath']}")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    print_info(f"Applying feedback: {feedback}")
    new_text = refine_post(post["text"], feedback, client=client)

    post["text"] = new_text
    post["word_count"] = len(new_text.split())
    post["char_count"] = len(new_text)
    post.pop("diagram", None)  # diagram may no longer match; regenerate on next publish

    print_post(post)
    path = save_post(post)
    print_success(f"Saved refined draft → {path.name}")

    if preview:
        _render_and_open_preview(post, client)


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _render_and_open_preview(post: dict, client) -> None:
    """Render the diagram for a post and open it with the system viewer."""
    from src.agent.writer import generate_diagram_spec
    from src.utils.image_gen import generate_post_image
    from src.utils.display import print_info, print_success, print_error
    import subprocess

    try:
        print_info("Rendering diagram preview...")
        generate_diagram_spec(post, client)
        img_path = generate_post_image(
            post,
            author_name=os.environ.get("AUTHOR_NAME", "Jeff Wilkowski"),
        )
        print_success(f"Diagram saved → {img_path}")
        # Try to open with system viewer (works on macOS, Linux with xdg-open, Windows)
        for cmd in ["open", "xdg-open", "start"]:
            try:
                subprocess.Popen([cmd, str(img_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                break
            except FileNotFoundError:
                continue
    except Exception as e:
        print_error(f"Preview failed: {e}")


def _require_env(*keys: str) -> None:
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        console.print(f"[bold red]Missing env vars: {', '.join(missing)}[/bold red]")
        console.print("Copy .env.example to .env and fill in the values.")
        sys.exit(1)


if __name__ == "__main__":
    cli()
