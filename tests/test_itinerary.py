"""Tests for itinerary generation engine."""

from datetime import date
import pytest

from utils.itinerary import (
    generate_itinerary,
    format_itinerary_as_text,
    sanitize_filename,
)


def test_one_day_trip_produces_one_itinerary_day():
    itin = generate_itinerary(
        destination="Jaipur",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 1),
        travelers=2,
        budget=10000.0,
    )
    assert itin.num_days == 1
    assert len(itin.days) == 1
    assert itin.days[0].day_number == 1
    assert itin.days[0].date_str == "2026-12-01"
    assert itin.budget["num_nights"] == 0


def test_three_day_trip_produces_three_itinerary_days():
    itin = generate_itinerary(
        destination="Udaipur",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 12),
        travelers=2,
        budget=35000.0,
    )
    assert itin.num_days == 3
    assert len(itin.days) == 3
    assert [d.day_number for d in itin.days] == [1, 2, 3]
    assert [d.date_str for d in itin.days] == ["2026-11-10", "2026-11-11", "2026-11-12"]


def test_trip_crossing_month_boundary_uses_correct_dates():
    itin = generate_itinerary(
        destination="Goa",
        start_date=date(2026, 10, 30),
        end_date=date(2026, 11, 2),
        travelers=2,
        budget=40000.0,
    )
    assert itin.num_days == 4
    expected_dates = ["2026-10-30", "2026-10-31", "2026-11-01", "2026-11-02"]
    actual_dates = [d.date_str for d in itin.days]
    assert actual_dates == expected_dates


def test_unknown_destination_uses_fallback_workflow():
    itin = generate_itinerary(
        destination="Atlantis Island",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 2),
        travelers=2,
        budget=20000.0,
    )
    assert itin.is_catalog_destination is False
    assert "Custom Exploration" in itin.destination_tagline
    # Activities should be tagged as Generic Recommendation
    for day in itin.days:
        assert day.morning_activity.recommendation_type == "Generic Recommendation"


def test_invalid_date_range_rejected():
    with pytest.raises(ValueError):
        generate_itinerary(
            destination="Delhi",
            start_date=date(2026, 11, 15),
            end_date=date(2026, 11, 10),
            travelers=1,
            budget=15000.0,
        )


def test_activity_preferences_influence_recommendations():
    # If user prefers Museums, museum activities should rank high
    itin = generate_itinerary(
        destination="Jaipur",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 1),
        travelers=1,
        budget=10000.0,
        preferred_activities=["Museums"],
    )
    first_activity = itin.days[0].morning_activity
    # In Jaipur, City Palace is tagged as Museums
    assert first_activity.category in ["Museums", "Historical Landmarks"]


def test_empty_preferences_do_not_crash_generator():
    itin = generate_itinerary(
        destination="Mumbai",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 2),
        travelers=2,
        budget=25000.0,
        preferred_activities=[],
    )
    assert itin.num_days == 2
    assert len(itin.days) == 2


def test_format_itinerary_as_text_and_filename_sanitization():
    itin = generate_itinerary(
        destination="Kochi / Cochin @ Kerala!",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 2),
        travelers=2,
        budget=20000.0,
    )
    text_output = format_itinerary_as_text(itin)

    assert "PERSONALIZED TRAVEL ITINERARY PLANNER" in text_output
    assert "TRIP OVERVIEW" in text_output
    assert "BUDGET & EXPENSE SUMMARY" in text_output
    assert "DAY-BY-DAY ITINERARY" in text_output
    assert "DISCLAIMER" in text_output

    safe_name = sanitize_filename("Kochi / Cochin @ Kerala!")
    assert safe_name == "kochi_cochin_kerala"
    assert " " not in safe_name
    assert "@" not in safe_name


def test_relaxed_pace_includes_afternoon_leisure():
    itin = generate_itinerary(
        destination="Jaipur",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 1),
        travelers=2,
        budget=15000.0,
        pace="Relaxed",
    )
    afternoon = itin.days[0].afternoon_activity
    assert afternoon.category == "Relaxation"
    assert "Leisure" in afternoon.name


def test_dietary_preference_selection():
    itin_veg = generate_itinerary(
        destination="Jaipur",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 1),
        travelers=2,
        budget=15000.0,
        dietary="Vegetarian",
    )
    lunch = itin_veg.days[0].lunch_suggestion
    assert "Dal Baati" in lunch or "Vegetarian" in lunch or "Vegan" in lunch or "Thali" in lunch


def test_long_trip_generates_correct_days_without_crash():
    itin = generate_itinerary(
        destination="Agra",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 10),  # 10 days in Agra (catalog has 6 attractions)
        travelers=2,
        budget=80000.0,
    )
    assert itin.num_days == 10
    assert len(itin.days) == 10
    assert itin.budget["num_nights"] == 9

