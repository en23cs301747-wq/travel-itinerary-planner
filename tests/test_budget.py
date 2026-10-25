"""Tests for budget estimation engine."""

import pytest
from utils.budget import calculate_budget


def test_budget_categories_sum_correctly():
    budget = calculate_budget(
        total_budget=50000.0,
        num_days=4,
        travelers=2,
        travel_style="Cultural",
        accommodation_type="Standard Hotel",
        transportation_type="Public Transport",
        total_activity_cost_per_traveler=800.0,
    )

    component_sum = (
        budget.accommodation_cost
        + budget.food_cost
        + budget.transportation_cost
        + budget.activities_cost
        + budget.contingency_cost
    )

    assert round(component_sum, 2) == round(budget.estimated_total_cost, 2)


def test_accommodation_based_on_nights_and_same_day_trip():
    # 1-day trip = 0 nights -> 0 accommodation
    day_trip_budget = calculate_budget(
        total_budget=10000.0,
        num_days=1,
        travelers=2,
        travel_style="Cultural",
        accommodation_type="Luxury Hotel",
        transportation_type="Taxi",
        total_activity_cost_per_traveler=500.0,
    )
    assert day_trip_budget.num_nights == 0
    assert day_trip_budget.accommodation_cost == 0.0

    # 3-day trip = 2 nights -> 2 nights of accommodation
    multi_day_budget = calculate_budget(
        total_budget=40000.0,
        num_days=3,
        travelers=2,
        travel_style="Cultural",
        accommodation_type="Budget Hotel",  # 2000 per room
        transportation_type="Public Transport",
    )
    assert multi_day_budget.num_nights == 2
    # 2 travelers share 1 double room: 1 room * 2000 * 2 nights = 4000
    assert multi_day_budget.accommodation_cost == 4000.0


def test_costs_scale_with_traveler_count():
    b_solo = calculate_budget(
        total_budget=20000.0,
        num_days=2,
        travelers=1,
        travel_style="Budget",
        accommodation_type="Hostel",
        transportation_type="Public Transport",
        total_activity_cost_per_traveler=400.0,
    )

    b_duo = calculate_budget(
        total_budget=40000.0,
        num_days=2,
        travelers=2,
        travel_style="Budget",
        accommodation_type="Hostel",
        transportation_type="Public Transport",
        total_activity_cost_per_traveler=400.0,
    )

    # Food & activities should double exactly
    assert b_duo.food_cost == b_solo.food_cost * 2
    assert b_duo.activities_cost == b_solo.activities_cost * 2
    assert b_duo.transportation_cost == b_solo.transportation_cost * 2


def test_remaining_budget_and_overspending_detection():
    # Plenty of budget
    b_under = calculate_budget(
        total_budget=80000.0,
        num_days=3,
        travelers=2,
        travel_style="Budget",
        accommodation_type="Budget Hotel",
        transportation_type="Public Transport",
    )
    assert b_under.is_over_budget is False
    assert b_under.remaining_budget > 0
    assert len(b_under.cost_saving_suggestions) == 0

    # Underfunded trip
    b_over = calculate_budget(
        total_budget=5000.0,
        num_days=5,
        travelers=4,
        travel_style="Luxury",
        accommodation_type="Luxury Hotel",
        transportation_type="Taxi",
    )
    assert b_over.is_over_budget is True
    assert b_over.remaining_budget < 0
    assert len(b_over.cost_saving_suggestions) > 0


def test_invalid_budget_inputs_rejected():
    with pytest.raises(ValueError):
        calculate_budget(
            total_budget=-500,
            num_days=3,
            travelers=2,
            travel_style="Cultural",
            accommodation_type="Standard Hotel",
            transportation_type="Taxi",
        )

    with pytest.raises(ValueError):
        calculate_budget(
            total_budget=20000,
            num_days=0,
            travelers=2,
            travel_style="Cultural",
            accommodation_type="Standard Hotel",
            transportation_type="Taxi",
        )

    with pytest.raises(ValueError):
        calculate_budget(
            total_budget=20000,
            num_days=3,
            travelers=0,
            travel_style="Cultural",
            accommodation_type="Standard Hotel",
            transportation_type="Taxi",
        )
