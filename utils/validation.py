"""Validation module for Personalized Travel Itinerary Planner.

Provides rigorous, reusable validation for trip inputs, destination catalog
schemas, budget constraints, and generated itinerary integrity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Sequence

# Configure privacy-safe module logger
logger = logging.getLogger("travel_planner.validation")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Allowed option sets matching application design
VALID_TRAVEL_STYLES = frozenset([
    "Budget", "Adventure", "Cultural", "Relaxation", "Family", "Luxury"
])

VALID_ACCOMMODATIONS = frozenset([
    "Hostel", "Budget Hotel", "Standard Hotel", "Luxury Hotel"
])

VALID_TRANSPORTATIONS = frozenset([
    "Public Transport", "Rental Vehicle", "Taxi", "Mixed"
])

VALID_DIETARY_PREFERENCES = frozenset([
    "Vegetarian", "Vegan", "No Preference", "Other"
])

VALID_DAILY_PACES = frozenset([
    "Relaxed", "Balanced", "Packed"
])

VALID_ACTIVITY_CATEGORIES = frozenset([
    "Sightseeing", "Nature", "Museums", "Shopping", "Food", "Adventure", "Historical Landmarks"
])

MIN_TRAVELERS = 1
MAX_TRAVELERS = 20
MIN_BUDGET_INR = 100.0
MAX_TRIP_DAYS = 60


class ValidationError(ValueError):
    """Custom exception raised when trip input parameters fail validation."""
    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or [message]


@dataclass
class ValidationResult:
    """Encapsulates validation outcome with detailed errors and warnings."""
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.is_valid = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


def validate_trip_inputs(
    destination: str | None,
    start_date: date | None,
    end_date: date | None,
    travelers: int | None,
    budget: float | int | None,
    travel_style: str | None,
    activities: Sequence[str] | None,
    accommodation: str | None,
    transportation: str | None,
    dietary: str | None,
    pace: str | None,
) -> ValidationResult:
    """Validates user-submitted trip planning form parameters.

    Returns:
        ValidationResult containing validation status, list of errors, and warnings.
    """
    result = ValidationResult(is_valid=True)

    # 1. Destination validation
    if destination is None or not str(destination).strip():
        result.add_error("Destination cannot be blank. Please enter or select a destination.")
    else:
        cleaned_dest = str(destination).strip()
        if len(cleaned_dest) < 2:
            result.add_error("Destination name is too short. Please enter a valid city or region name.")
        elif len(cleaned_dest) > 100:
            result.add_error("Destination name exceeds maximum length (100 characters).")

    # 2. Date validation
    if start_date is None or end_date is None:
        result.add_error("Both start date and end date must be provided.")
    elif not isinstance(start_date, date) or not isinstance(end_date, date):
        result.add_error("Start date and end date must be valid date objects.")
    else:
        if start_date > end_date:
            result.add_error(
                f"Start date ({start_date.isoformat()}) cannot be after end date ({end_date.isoformat()})."
            )
        else:
            trip_days = (end_date - start_date).days + 1
            if trip_days > MAX_TRIP_DAYS:
                result.add_error(
                    f"Trip duration is {trip_days} days. Maximum supported trip duration is {MAX_TRIP_DAYS} days."
                )

    # 3. Traveler count validation
    if travelers is None:
        result.add_error("Traveler count must be specified.")
    else:
        try:
            travelers_int = int(travelers)
            if travelers_int < MIN_TRAVELERS:
                result.add_error(f"Traveler count must be at least {MIN_TRAVELERS}.")
            elif travelers_int > MAX_TRAVELERS:
                result.add_error(f"Traveler count cannot exceed {MAX_TRAVELERS}.")
        except (ValueError, TypeError):
            result.add_error(f"Traveler count must be an integer between {MIN_TRAVELERS} and {MAX_TRAVELERS}.")

    # 4. Budget validation
    if budget is None:
        result.add_error("Total budget must be provided.")
    else:
        try:
            budget_val = float(budget)
            if budget_val <= 0:
                result.add_error("Total budget must be a positive amount greater than zero.")
            elif budget_val < MIN_BUDGET_INR:
                result.add_error(f"Total budget must be at least ₹{int(MIN_BUDGET_INR):,}.")
            elif budget_val > 100_000_000:
                result.add_error("Budget exceeds realistic limits for standard itinerary calculations.")
        except (ValueError, TypeError):
            result.add_error("Total budget must be a valid numeric amount.")

    # 5. Travel Style validation
    if not travel_style or travel_style not in VALID_TRAVEL_STYLES:
        result.add_error(
            f"Invalid travel style '{travel_style}'. Allowed styles: {', '.join(sorted(VALID_TRAVEL_STYLES))}."
        )

    # 6. Accommodation validation
    if not accommodation or accommodation not in VALID_ACCOMMODATIONS:
        result.add_error(
            f"Invalid accommodation preference '{accommodation}'. Allowed options: {', '.join(sorted(VALID_ACCOMMODATIONS))}."
        )

    # 7. Transportation validation
    if not transportation or transportation not in VALID_TRANSPORTATIONS:
        result.add_error(
            f"Invalid transportation preference '{transportation}'. Allowed options: {', '.join(sorted(VALID_TRANSPORTATIONS))}."
        )

    # 8. Dietary preference validation
    if not dietary or dietary not in VALID_DIETARY_PREFERENCES:
        result.add_error(
            f"Invalid dietary preference '{dietary}'. Allowed options: {', '.join(sorted(VALID_DIETARY_PREFERENCES))}."
        )

    # 9. Daily Pace validation
    if not pace or pace not in VALID_DAILY_PACES:
        result.add_error(
            f"Invalid daily pace '{pace}'. Allowed paces: {', '.join(sorted(VALID_DAILY_PACES))}."
        )

    # 10. Preferred activities validation
    if activities is None or len(activities) == 0:
        result.add_warning("No specific activities were selected; an all-around balanced mix will be recommended.")
    else:
        invalid_activities = [act for act in activities if act not in VALID_ACTIVITY_CATEGORIES]
        if invalid_activities:
            result.add_warning(
                f"Some custom activities ({', '.join(invalid_activities)}) are not in the standard catalog categories."
            )

    # Log safe summary without user identity
    if result.is_valid:
        logger.info(
            "Trip input validation succeeded (travelers=%s, pace=%s, style=%s)",
            travelers,
            pace,
            travel_style,
        )
    else:
        logger.warning(
            "Trip input validation failed with %d error(s)",
            len(result.errors),
        )

    return result


def validate_catalog_data(catalog_data: Any) -> bool:
    """Validates the structural integrity and schema of loaded destination catalog data."""
    if not isinstance(catalog_data, dict):
        logger.error("Destination catalog root is not a dictionary.")
        return False

    destinations = catalog_data.get("destinations")
    if not isinstance(destinations, list) or len(destinations) == 0:
        logger.error("Destination catalog is missing non-empty 'destinations' list.")
        return False

    required_dest_fields = {"id", "name", "description", "attractions", "meals"}
    for idx, dest in enumerate(destinations):
        if not isinstance(dest, dict):
            logger.error("Destination at index %d is not an object.", idx)
            return False

        missing = required_dest_fields - dest.keys()
        if missing:
            logger.error("Destination '%s' missing fields: %s", dest.get("name", f"index_{idx}"), missing)
            return False

        attractions = dest.get("attractions")
        if not isinstance(attractions, list) or len(attractions) == 0:
            logger.error("Destination '%s' has no valid attractions list.", dest.get("name"))
            return False

        for a_idx, attr in enumerate(attractions):
            if not isinstance(attr, dict) or "name" not in attr or "duration_hours" not in attr:
                logger.error("Attraction %d in '%s' is malformed.", a_idx, dest.get("name"))
                return False
            if float(attr.get("duration_hours", 0)) <= 0:
                logger.error("Attraction '%s' in '%s' has non-positive duration.", attr.get("name"), dest.get("name"))
                return False

    return True


def validate_budget_breakdown(budget_dict: dict[str, Any]) -> ValidationResult:
    """Validates that a calculated budget breakdown is internally consistent and non-negative."""
    result = ValidationResult(is_valid=True)

    required_keys = [
        "total_budget", "estimated_total_cost", "remaining_budget",
        "cost_per_traveler", "accommodation_cost", "food_cost",
        "transportation_cost", "activities_cost", "contingency_cost"
    ]

    for key in required_keys:
        if key not in budget_dict:
            result.add_error(f"Missing required budget field: '{key}'.")
            return result

        val = budget_dict[key]
        if not isinstance(val, (int, float)):
            result.add_error(f"Budget field '{key}' must be numeric.")
        elif val < 0 and key != "remaining_budget":
            # remaining_budget can be negative if overspent
            result.add_error(f"Budget expense '{key}' cannot be negative: {val}.")

    if not result.is_valid:
        return result

    # Check sum consistency subject to small rounding tolerance
    sum_components = (
        budget_dict["accommodation_cost"]
        + budget_dict["food_cost"]
        + budget_dict["transportation_cost"]
        + budget_dict["activities_cost"]
        + budget_dict["contingency_cost"]
    )

    diff = abs(sum_components - budget_dict["estimated_total_cost"])
    if diff > 1.0:  # Allow max ₹1 rounding variance
        result.add_error(
            f"Budget sum mismatch: sum of parts ({sum_components:.2f}) does not match total ({budget_dict['estimated_total_cost']:.2f})."
        )

    return result
