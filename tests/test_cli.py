"""
CLI smoke tests — verify commands are wired correctly and reject bad inputs.
Uses Click's test runner; no real API calls are made.
"""
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from main import cli


runner = CliRunner()


def test_cli_help():
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "generate" in result.output


def test_generate_help():
    result = runner.invoke(cli, ["generate", "--help"])
    assert result.exit_code == 0
    # Old removed formats must not appear
    assert "story" not in result.output
    assert "trend_analysis" not in result.output
    # Current formats must appear
    assert "trend_prediction" in result.output
    assert "framework" in result.output
    assert "breakdown" in result.output


def test_generate_rejects_old_format_story():
    result = runner.invoke(cli, ["generate", "--format", "story"])
    assert result.exit_code != 0


def test_generate_rejects_old_format_trend_analysis():
    result = runner.invoke(cli, ["generate", "--format", "trend_analysis"])
    assert result.exit_code != 0


def test_list_command_no_posts():
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["list"])
    # Should exit cleanly even with no posts
    assert result.exit_code == 0


def test_calendar_command_runs():
    result = runner.invoke(cli, ["calendar", "--days", "7"])
    assert result.exit_code == 0
    assert "Mon" in result.output or "Wed" in result.output or "Fri" in result.output


def test_weekly_report_command_runs():
    result = runner.invoke(cli, ["weekly-report"])
    assert result.exit_code == 0


def test_generate_uses_content_calendar_topic():
    """generate with no --topic should call pick_todays_topic, not random.choice."""
    with patch("src.utils.content_calendar.pick_todays_topic", return_value="Pricing and packaging strategy") as mock_pick:
        with patch("src.agent.researcher.research_trending_topics", return_value={"topic": "Pricing and packaging strategy", "summary": "", "sources": [], "researched_at": "2026-01-01", "fallback": True}):
            with patch("src.agent.researcher.build_research_brief", return_value="brief text"):
                with patch("src.agent.writer.generate_post", return_value={"text": "post", "topic": "Pricing and packaging strategy", "format": "framework", "hashtags": ["#SaaS"], "word_count": 1, "char_count": 4}):
                    with patch("src.utils.storage.save_post", return_value=MagicMock(name="2026-01-01_draft.json")):
                        with patch("src.utils.display.print_post"):
                            with patch("src.utils.display.print_info"):
                                with patch("src.utils.display.print_success"):
                                    with patch("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
                                        runner.invoke(cli, ["generate"])
        mock_pick.assert_called_once()
