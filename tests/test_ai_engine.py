import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_engine import _generate_fallback_report, generate_weekly_report


SAMPLE_REPORT_DATA = {
    "period": "Week 1 (March 1-7)",
    "total_revenue": 85000,
    "total_cost": 25000,
    "total_profit": 60000,
    "top_sellers": [
        {"name": "Masala Chai", "total_sold": 200, "revenue": 12000, "cost": 3000, "profit": 9000},
        {"name": "Cappuccino", "total_sold": 170, "revenue": 30600, "cost": 8500, "profit": 22100},
    ],
    "daily_summary": [
        {"date": "2026-03-01", "day": "Sunday", "revenue": 15000, "total_items": 180},
        {"date": "2026-03-02", "day": "Monday", "revenue": 10000, "total_items": 120},
        {"date": "2026-03-03", "day": "Tuesday", "revenue": 11000, "total_items": 130},
        {"date": "2026-03-04", "day": "Wednesday", "revenue": 10500, "total_items": 125},
        {"date": "2026-03-05", "day": "Thursday", "revenue": 11500, "total_items": 135},
        {"date": "2026-03-06", "day": "Friday", "revenue": 12000, "total_items": 140},
        {"date": "2026-03-07", "day": "Saturday", "revenue": 15000, "total_items": 175},
    ],
    "expiring_items": [
        {"name": "Milk", "expiry_date": "2026-03-10", "quantity": 8.0, "unit": "liters"},
    ],
    "expired_items": [
        {"name": "Lettuce", "quantity": 1.5, "unit": "kg"},
    ],
    "waste_log": [
        {"ingredient": "Lettuce", "total_wasted": 1.5},
    ],
    "low_stock": [
        {"name": "Paneer", "quantity": 1.2, "unit": "kg"},
    ],
}


def test_fallback_report_generates_content():
    """Test that the fallback report generator produces meaningful content."""
    report = _generate_fallback_report(SAMPLE_REPORT_DATA)

    assert "Week 1" in report
    assert "85,000" in report or "85000" in report
    assert "Masala Chai" in report
    assert "Cappuccino" in report


def test_fallback_report_detects_weekend_spike():
    """Test that fallback report detects weekend vs weekday patterns."""
    report = _generate_fallback_report(SAMPLE_REPORT_DATA)

    # Should mention weekend spike since Sunday and Saturday have higher revenue
    assert "weekend" in report.lower() or "Weekend" in report


def test_fallback_report_includes_expiry_alerts():
    """Test that fallback report includes expiring and expired items."""
    report = _generate_fallback_report(SAMPLE_REPORT_DATA)

    assert "Milk" in report
    assert "Lettuce" in report
    assert "expir" in report.lower()


def test_fallback_report_shows_low_stock():
    """Test that fallback report includes low stock warnings."""
    report = _generate_fallback_report(SAMPLE_REPORT_DATA)

    assert "Paneer" in report
    assert "Low Stock" in report or "low stock" in report.lower() or "Reorder" in report


def test_generate_report_falls_back_without_api_key():
    """Test that generate_weekly_report uses fallback when no API key is set."""
    # Ensure no API key is set
    original_key = os.environ.get("OPENROUTER_API_KEY", "")
    os.environ["OPENROUTER_API_KEY"] = ""

    # Reload to pick up empty key
    import ai_engine
    ai_engine.OPENROUTER_API_KEY = ""

    result = generate_weekly_report(SAMPLE_REPORT_DATA)

    assert result["source"] == "fallback"
    assert len(result["report"]) > 100  # Should have meaningful content
    assert "Week 1" in result["report"]

    # Restore
    os.environ["OPENROUTER_API_KEY"] = original_key
    ai_engine.OPENROUTER_API_KEY = original_key
