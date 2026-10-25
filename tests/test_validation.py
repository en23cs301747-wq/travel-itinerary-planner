"""Tests for trip planning validation module."""

from datetime import date
import pytest

from utils.validation import (
    validate_trip_inputs,
    validate_catalog_data,
    validate_budget_breakdown,
)


def test_valid_trip_inputs_accepted():
    result = validate_trip_inputs(
        destination="Jaipur",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 13),
        travelers=2,
        budget=25000.0,
        travel_style="Cultural",
        activities=["Historical Landmarks", "Sightseeing"],
        accommodation="Standard Hotel",
        transportation="Public Transport",
        dietary="Vegetarian",
        pace="Balanced",
    )
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_blank_destination_rejected():
    result = validate_trip_inputs(
        destination="   ",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 12),
        travelers=2,
        budget=20000.0,
        travel_style="Cultural",
        activities=[],
        accommodation="Standard Hotel",
        transportation="Public Transport",
        dietary="Vegetarian",
        pace="Balanced",
    )
    assert result.is_valid is False
    assert any("Destination cannot be blank" in err for err in result.errors)


def test_zero_travelers_rejected():
    result = validate_trip_inputs(
        destination="Goa",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 12),
        travelers=0,
        budget=20000.0,
        travel_style="Relaxation",
        activities=["Nature"],
        accommodation="Budget Hotel",
        transportation="Taxi",
        dietary="No Preference",
        pace="Relaxed",
    )
    assert result.is_valid is False
    assert any("Traveler count must be at least 1" in err for err in result.errors)


def test_excessive_traveler_count_rejected():
    result = validate_trip_inputs(
        destination="Manali",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 12),
        travelers=25,
        budget=200000.0,
        travel_style="Adventure",
        activities=["Adventure"],
        accommodation="Standard Hotel",
        transportation="Rental Vehicle",
        dietary="Vegetarian",
        pace="Balanced",
    )
    assert result.is_valid is False
    assert any("Traveler count cannot exceed 20" in err for err in result.errors)


def test_invalid_dates_rejected_when_start_after_end():
    result = validate_trip_inputs(
        destination="Udaipur",
        start_date=date(2026, 11, 15),
        end_date=date(2026, 11, 10),
        travelers=2,
        budget=30000.0,
        travel_style="Cultural",
        activities=["Sightseeing"],
        accommodation="Standard Hotel",
        transportation="Public Transport",
        dietary="Vegetarian",
        pace="Balanced",
    )
    assert result.is_valid is False
    assert any("cannot be after end date" in err for err in result.errors)


def test_invalid_negative_or_zero_budget_rejected():
    for bad_budget in [0, -500, -1.0]:
        res = validate_trip_inputs(
            destination="Delhi",
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 12),
            travelers=1,
            budget=bad_budget,
            travel_style="Budget",
            activities=[],
            accommodation="Hostel",
            transportation="Public Transport",
            dietary="Vegetarian",
            pace="Balanced",
        )
        assert res.is_valid is False
        assert any("Total budget must be a positive amount" in err for err in res.errors)


def test_invalid_travel_style_or_pace_rejected():
    res = validate_trip_inputs(
        destination="Kochi",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 12),
        travelers=2,
        budget=15000,
        travel_style="Interplanetary",  # Invalid
        activities=[],
        accommodation="Standard Hotel",
        transportation="Public Transport",
        dietary="Vegetarian",
        pace="Hyperdrive",  # Invalid
    )
    assert res.is_valid is False
    assert any("Invalid travel style" in err for err in res.errors)
    assert any("Invalid daily pace" in err for err in res.errors)


def test_validate_catalog_data_schema():
    valid_data = {
        "destinations": [
            {
                "id": "test-dest",
                "name": "Test Destination",
                "description": "A sample description.",
                "attractions": [
                    {
                        "name": "Test Landmark",
                        "category": "Sightseeing",
                        "duration_hours": 2.0,
                        "indicative_cost_inr": 100,
                    }
                ],
                "meals": {"breakfast": []},
            }
        ]
    }
    assert validate_catalog_data(valid_data) is True

    # Malformed data missing required fields
    invalid_data = {"destinations": [{"name": "Incomplete"}]}
    assert validate_catalog_data(invalid_data) is False


def test_validate_budget_breakdown_consistency():
    valid_breakdown = {
        "total_budget": 50000.0,
        "estimated_total_cost": 21400.0,
        "remaining_budget": 28600.0,
        "cost_per_traveler": 10700.0,
        "accommodation_cost": 8400.0,
        "food_cost": 5100.0,
        "transportation_cost": 1080.0,
        "activities_cost": 5420.0,
        "contingency_cost": 1400.0,
    }
    res = validate_budget_breakdown(valid_breakdown)
    assert res.is_valid is True

    # Inconsistent sum
    inconsistent = dict(valid_breakdown)
    inconsistent["estimated_total_cost"] = 99999.0
    res_bad = validate_budget_breakdown(inconsistent)
    assert res_bad.is_valid is False
