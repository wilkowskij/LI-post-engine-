#!/usr/bin/env python3
"""
Daily post scheduler — runs the full pipeline at a configured time each day.

Usage:
  python scheduler.py            # Run continuously (use with screen/tmux/systemd)
  python scheduler.py --now      # Run the job immediately (for testing)

Config (via .env):
  POST_SCHEDULE_TIME=08:00       # Time to post (24h, local timezone)
  POSTING_DAYS=Mon,Tue,Wed,Thu,Fri   # Days to post (default weekdays)
  POST_TIMEZONE=America/Chicago  # For display only; job runs in local system time
"""
import argparse
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import schedule
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import box

load_dotenv()
console = Console()

LOG_DIR = Path(__file__).parent / "output" / "logs"
POST_TIME = os.environ.get("POST_SCHEDULE_TIME", "08:00")
MAX_RETRIES = 3
RETRY_WAIT_SECONDS = 300  # 5 minutes between retries


def _setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"scheduler_{datetime.now().strftime('%Y-%m')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)s  %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("scheduler")


logger = _setup_logging()


def run_daily_job(force: bool = False) -> None:
    from src.utils.content_calendar import is_posting_day

    if not force and not is_posting_day():
        day_name = datetime.now().strftime("%A")
        logger.info(f"Skipping — {day_name} is not a scheduled posting day.")
        return

    logger.info("Starting daily post generation...")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = subprocess.run(
                [sys.executable, "main.py", "run-daily", "--auto-schedule"],
                capture_output=False,
            )
            if result.returncode == 0:
                logger.info("Daily job completed successfully.")
                return
            logger.warning(f"Attempt {attempt}/{MAX_RETRIES} failed (exit code {result.returncode}).")
        except Exception as e:
            logger.warning(f"Attempt {attempt}/{MAX_RETRIES} raised exception: {e}")

        if attempt < MAX_RETRIES:
            logger.info(f"Retrying in {RETRY_WAIT_SECONDS // 60} minutes...")
            time.sleep(RETRY_WAIT_SECONDS)

    logger.error("All retry attempts failed. Check logs and re-run manually.")


def _print_status() -> None:
    from src.utils.content_calendar import get_posting_days, get_weekly_summary, get_upcoming_plan, DAY_NAMES

    console.rule("[bold blue]LinkedIn Post Engine Scheduler[/bold blue]")
    console.print(f"  Daily run time : [cyan]{POST_TIME}[/cyan] (local system time)")
    posting_days = get_posting_days()
    day_labels = ", ".join(DAY_NAMES.get(d, "") for d in sorted(posting_days))
    console.print(f"  Posting days   : [cyan]{day_labels}[/cyan]")
    console.print(f"  Log directory  : [dim]{LOG_DIR}[/dim]")
    console.print()

    # Weekly summary
    summary = get_weekly_summary()
    console.print(f"[bold]Last 7 days:[/bold] {summary['total']} posts generated "
                  f"({summary['scheduled']} scheduled, {summary['drafts']} drafts)")
    if summary["topics_used"]:
        console.print(f"  Topics covered : {', '.join(summary['topics_used'])}")
    console.print()

    # Upcoming plan
    plan = get_upcoming_plan(7)
    if plan:
        table = Table(title="Upcoming Content Plan", box=box.ROUNDED)
        table.add_column("Date", style="cyan", width=12)
        table.add_column("Day", width=6)
        table.add_column("Suggested Topic", width=42)
        for entry in plan:
            day_label = "[bold green]TODAY[/bold green]" if entry["is_today"] else entry["weekday"]
            table.add_row(entry["date"], day_label, entry["topic"])
        console.print(table)
        console.print()


def main() -> None:
    parser = argparse.ArgumentParser(description="LinkedIn Post Engine Scheduler")
    parser.add_argument("--now", action="store_true", help="Run the job immediately and exit")
    args = parser.parse_args()

    if args.now:
        console.print("[bold yellow]Running job immediately (--now flag)...[/bold yellow]")
        run_daily_job(force=True)
        return

    _print_status()
    console.print(f"[bold]Scheduler running.[/bold] Next run at [cyan]{POST_TIME}[/cyan] on posting days.")
    console.print("Press Ctrl+C to stop.\n")

    schedule.every().day.at(POST_TIME).do(run_daily_job)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
