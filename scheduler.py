#!/usr/bin/env python3
"""
Runs the daily post generation on a schedule (default: 7:00 AM local time).
Run this as a long-running process: python scheduler.py
"""
import os
import subprocess
import sys
from datetime import datetime

import schedule
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
console = Console()

POST_TIME = os.environ.get("POST_SCHEDULE_TIME", "07:00")


def run_daily_job():
    console.print(f"\n[bold blue][{datetime.now().strftime('%Y-%m-%d %H:%M')}] Running daily post generation...[/bold blue]")
    result = subprocess.run(
        [sys.executable, "main.py", "run-daily", "--auto-schedule"],
        capture_output=False,
    )
    if result.returncode != 0:
        console.print(f"[red]Daily job failed with exit code {result.returncode}[/red]")
    else:
        console.print("[green]Daily job completed successfully.[/green]")


def main():
    console.print(f"[bold]LinkedIn Post Engine Scheduler[/bold]")
    console.print(f"Daily post scheduled at: [cyan]{POST_TIME}[/cyan] (local time)")
    console.print("Press Ctrl+C to stop.\n")

    schedule.every().day.at(POST_TIME).do(run_daily_job)

    while True:
        schedule.run_pending()
        import time
        time.sleep(60)


if __name__ == "__main__":
    main()
