"""Budget estimation engine for Personalized Travel Itinerary Planner.

Provides deterministic, transparent cost modeling in Indian Rupees (INR)
with explicit assumptions for shared versus individual expenses,
night-based accommodation, and contingency reserves.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

# ==============================================================================
# BASELINE PRICING MODEL ASSUMPTIONS (INR)
# ==============================================================================

# Accommodation pricing per night
# Hostels are priced per bed per traveler.
# Hotels are priced per standard double room (shared by up to 2 travelers).
ACCOMMODATION_RATES_INR = {
    "Hostel": {"rate": 750.0, "unit": "per_traveler_bed"},
    "Budget Hotel": {"rate": 2000.0, "unit": "per_double_room"},
    "Standard Hotel": {"rate": 4200.0, "unit": "per_double_room"},
    "Luxury Hotel": {"rate": 11500.0, "unit": "per_double_room"},
}

# Food pricing per traveler per day by travel style
DAILY_FOOD_RATES_INR = {
    "Budget": 450.0,
    "Adventure": 650.0,
    "Cultural": 850.0,
    "Relaxation": 1000.0,
    "Family": 800.0,
    "Luxury": 2500.0,
}

# Local Transportation pricing per day
# Public transport and mixed are estimated per traveler per day.
# Rental vehicle and taxi are estimated per standard vehicle (up to 4 travelers per vehicle).
TRANSPORTATION_RATES_INR = {
    "Public Transport": {"rate": 180.0, "unit": "per_traveler"},
    "Rental Vehicle": {"rate": 2200.0, "unit": "per_vehicle"},
    "Taxi": {"rate": 1600.0, "unit": "per_vehicle"},
    "Mixed": {"rate": 450.0, "unit": "per_traveler"},
}

CONTINGENCY_PERCENTAGE = 0.07  # 7% emergency and buffer reserve


@dataclass
class ExpenseCategoryDetail:
    """Detail for a single expense category with explanatory breakdown."""
    category_name: str
    total_cost: float
    is_shared: bool
    explanation: str


@dataclass
class BudgetBreakdown:
    """Structured budget estimation breakdown."""
    total_budget: float
    estimated_total_cost: float
    remaining_budget: float
    is_over_budget: bool
    cost_per_traveler: float
    num_days: int
    num_nights: int
    num_travelers: int

    accommodation_cost: float
    food_cost: float
    transportation_cost: float
    activities_cost: float
    contingency_cost: float

    details: list[dict[str, Any]] = field(default_factory=list)
    cost_saving_suggestions: list[str] = field(default_factory=list)
    daily_expense_breakdown: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calculate_budget(
    total_budget: float,
    num_days: int,
    travelers: int,
    travel_style: str,
    accommodation_type: str,
    transportation_type: str,
    total_activity_cost_per_traveler: float = 0.0,
    daily_activity_costs_per_traveler: list[float] | None = None,
) -> BudgetBreakdown:
    """Calculates comprehensive trip budget breakdown based on explicit rules.

    Args:
        total_budget: Total budget specified by user in INR.
        num_days: Total number of itinerary days (inclusive).
        travelers: Number of travelers (1 to 20).
        travel_style: Selected travel style.
        accommodation_type: Selected accommodation category.
        transportation_type: Selected local transportation mode.
        total_activity_cost_per_traveler: Total estimated activity admission costs per traveler.
        daily_activity_costs_per_traveler: Optional list of activity costs per traveler for each day.

    Returns:
        Structured BudgetBreakdown instance.
    """
    if num_days <= 0:
        raise ValueError("Number of days must be at least 1.")
    if travelers <= 0:
        raise ValueError("Traveler count must be at least 1.")
    if total_budget <= 0:
        raise ValueError("Total budget must be greater than zero.")

    # 1. Number of nights: 1-day trips do NOT incur overnight stay
    num_nights = max(0, num_days - 1)

    # 2. Accommodation calculation
    accom_config = ACCOMMODATION_RATES_INR.get(
        accommodation_type, ACCOMMODATION_RATES_INR["Standard Hotel"]
    )
    if num_nights == 0:
        accommodation_cost = 0.0
        accom_explanation = "Same-day trip (0 nights): no overnight accommodation required."
        is_accom_shared = False
    elif accom_config["unit"] == "per_traveler_bed":
        accommodation_cost = round(accom_config["rate"] * travelers * num_nights, 2)
        accom_explanation = (
            f"{travelers} traveler(s) × ₹{accom_config['rate']:,.0f}/bed × {num_nights} night(s) in {accommodation_type}."
        )
        is_accom_shared = False
    else:
        # Standard double room (up to 2 travelers per room)
        rooms_needed = math.ceil(travelers / 2)
        accommodation_cost = round(rooms_needed * accom_config["rate"] * num_nights, 2)
        accom_explanation = (
            f"{rooms_needed} room(s) [shared 2 travelers/room] × ₹{accom_config['rate']:,.0f}/night "
            f"× {num_nights} night(s) in {accommodation_type}."
        )
        is_accom_shared = True

    # 3. Food calculation
    daily_food_rate = DAILY_FOOD_RATES_INR.get(
        travel_style, DAILY_FOOD_RATES_INR["Cultural"]
    )
    food_cost = round(daily_food_rate * travelers * num_days, 2)
    food_explanation = (
        f"{travelers} traveler(s) × ₹{daily_food_rate:,.0f}/day × {num_days} day(s) based on {travel_style} travel style."
    )

    # 4. Transportation calculation
    trans_config = TRANSPORTATION_RATES_INR.get(
        transportation_type, TRANSPORTATION_RATES_INR["Mixed"]
    )
    if trans_config["unit"] == "per_vehicle":
        vehicles_needed = math.ceil(travelers / 4)
        transportation_cost = round(vehicles_needed * trans_config["rate"] * num_days, 2)
        trans_explanation = (
            f"{vehicles_needed} vehicle(s) [shared up to 4 travelers/vehicle] × ₹{trans_config['rate']:,.0f}/day "
            f"× {num_days} day(s) for {transportation_type}."
        )
        is_trans_shared = True
    else:
        transportation_cost = round(travelers * trans_config["rate"] * num_days, 2)
        trans_explanation = (
            f"{travelers} traveler(s) × ₹{trans_config['rate']:,.0f}/day × {num_days} day(s) for {transportation_type}."
        )
        is_trans_shared = False

    # 5. Activities calculation
    activities_cost = round(total_activity_cost_per_traveler * travelers, 2)
    activities_explanation = (
        f"{travelers} traveler(s) × ₹{total_activity_cost_per_traveler:,.0f} estimated activity admissions across the itinerary."
    )

    # 6. Contingency calculation
    base_subtotal = accommodation_cost + food_cost + transportation_cost + activities_cost
    contingency_cost = round(base_subtotal * CONTINGENCY_PERCENTAGE, 2)
    contingency_explanation = (
        f"7% buffer (₹{contingency_cost:,.0f}) reserved for local taxes, unexpected transfers, and tips."
    )

    # 7. Total estimated cost and comparison
    estimated_total_cost = round(base_subtotal + contingency_cost, 2)
    remaining_budget = round(total_budget - estimated_total_cost, 2)
    is_over_budget = remaining_budget < 0
    cost_per_traveler = round(estimated_total_cost / travelers, 2)

    # 8. Category details
    details = [
        ExpenseCategoryDetail("Accommodation", accommodation_cost, is_accom_shared, accom_explanation),
        ExpenseCategoryDetail("Food & Dining", food_cost, False, food_explanation),
        ExpenseCategoryDetail("Local Transportation", transportation_cost, is_trans_config_shared(transportation_type), trans_explanation),
        ExpenseCategoryDetail("Activities & Admissions", activities_cost, False, activities_explanation),
        ExpenseCategoryDetail("Contingency & Reserves", contingency_cost, True, contingency_explanation),
    ]

    # 9. Cost-saving suggestions if over budget
    cost_saving_suggestions: list[str] = []
    if is_over_budget:
        overspend_amount = abs(remaining_budget)
        cost_saving_suggestions.append(
            f"Current estimate exceeds budget by ₹{overspend_amount:,.0f} (₹{round(overspend_amount/travelers, 2):,.0f} per traveler)."
        )
        if accommodation_type in ["Luxury Hotel", "Standard Hotel"]:
            downgrade_target = "Standard Hotel" if accommodation_type == "Luxury Hotel" else "Budget Hotel"
            cost_saving_suggestions.append(
                f"Consider switching accommodation from '{accommodation_type}' to '{downgrade_target}' to reduce lodging expenses significantly."
            )
        if transportation_type in ["Taxi", "Rental Vehicle"]:
            cost_saving_suggestions.append(
                "Utilize Public Transport (Metro / local buses) or mixed transit instead of dedicated private vehicles."
            )
        if travel_style in ["Luxury", "Relaxation"]:
            cost_saving_suggestions.append(
                "Blend local casual dining and street culinary specialties to moderate daily food expenditure."
            )
        if activities_cost > 0.25 * total_budget:
            cost_saving_suggestions.append(
                "Prioritize free cultural sights, viewpoints, public gardens, and heritage promenades."
            )

    # 10. Day-by-day expense summary
    daily_expense_breakdown: list[dict[str, Any]] = []
    daily_accom = (accommodation_cost / num_days) if num_days > 0 else 0.0
    daily_trans = (transportation_cost / num_days) if num_days > 0 else 0.0
    daily_food = (food_cost / num_days) if num_days > 0 else 0.0

    for day_idx in range(num_days):
        day_act_per_person = (
            daily_activity_costs_per_traveler[day_idx]
            if daily_activity_costs_per_traveler and day_idx < len(daily_activity_costs_per_traveler)
            else (total_activity_cost_per_traveler / num_days if num_days > 0 else 0.0)
        )
        day_act_total = day_act_per_person * travelers
        day_subtotal = daily_accom + daily_trans + daily_food + day_act_total
        day_contingency = day_subtotal * CONTINGENCY_PERCENTAGE
        day_total = round(day_subtotal + day_contingency, 2)

        daily_expense_breakdown.append({
            "day": day_idx + 1,
            "accommodation": round(daily_accom, 2),
            "transportation": round(daily_trans, 2),
            "food": round(daily_food, 2),
            "activities": round(day_act_total, 2),
            "contingency": round(day_contingency, 2),
            "total": day_total,
        })

    # Adjust rounding in daily total sum if necessary to ensure exact equality with estimated_total_cost
    daily_sum = sum(d["total"] for d in daily_expense_breakdown)
    diff = round(estimated_total_cost - daily_sum, 2)
    if daily_expense_breakdown and diff != 0:
        daily_expense_breakdown[-1]["total"] = round(daily_expense_breakdown[-1]["total"] + diff, 2)
        daily_expense_breakdown[-1]["contingency"] = round(daily_expense_breakdown[-1]["contingency"] + diff, 2)

    return BudgetBreakdown(
        total_budget=round(total_budget, 2),
        estimated_total_cost=estimated_total_cost,
        remaining_budget=remaining_budget,
        is_over_budget=is_over_budget,
        cost_per_traveler=cost_per_traveler,
        num_days=num_days,
        num_nights=num_nights,
        num_travelers=travelers,
        accommodation_cost=accommodation_cost,
        food_cost=food_cost,
        transportation_cost=transportation_cost,
        activities_cost=activities_cost,
        contingency_cost=contingency_cost,
        details=[asdict(d) for d in details],
        cost_saving_suggestions=cost_saving_suggestions,
        daily_expense_breakdown=daily_expense_breakdown,
    )


def is_trans_config_shared(transportation_type: str) -> bool:
    """Helper to determine if a transport mode uses shared vehicle pricing."""
    cfg = TRANSPORTATION_RATES_INR.get(transportation_type, {})
    return cfg.get("unit") == "per_vehicle"
