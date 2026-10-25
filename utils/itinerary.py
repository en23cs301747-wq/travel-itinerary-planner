"""Itinerary generation engine for Personalized Travel Itinerary Planner.

Provides deterministic, preference-driven itinerary synthesis using either
the local curated destination catalog or an adaptive fallback model for
unlisted destinations.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Sequence

from utils.budget import calculate_budget

logger = logging.getLogger("travel_planner.itinerary")

# Generic activity templates used when a destination is not in the catalog,
# or when a catalog destination has fewer attractions than needed for a long trip.
GENERIC_ACTIVITY_TEMPLATES = [
    {
        "name": "Arrival & City Orientation Walk",
        "category": "Sightseeing",
        "description": "Familiarize with the central district, prominent public squares, and nearby landmarks.",
        "duration_hours": 2.0,
        "indicative_cost_inr": 0.0,
        "best_time_of_day": "Morning",
        "practical_tips": "Stop at a local tourist information kiosk or pick up a regional walking map."
    },
    {
        "name": "Local Heritage & Historical Monument Tour",
        "category": "Historical Landmarks",
        "description": "Explore the primary historic fortress, palace, or iconic monument of the destination.",
        "duration_hours": 2.5,
        "indicative_cost_inr": 200.0,
        "best_time_of_day": "Morning",
        "practical_tips": "Hire an authorized local guide to appreciate the regional architecture."
    },
    {
        "name": "Regional Arts & Cultural Museum Exploration",
        "category": "Museums",
        "description": "Discover regional artifacts, archaeological exhibits, and folk traditions in the municipal museum.",
        "duration_hours": 2.0,
        "indicative_cost_inr": 150.0,
        "best_time_of_day": "Afternoon",
        "practical_tips": "Inquire about photography permits at the admission counter."
    },
    {
        "name": "Traditional Crafts Bazaar & Souvenir Walk",
        "category": "Shopping",
        "description": "Stroll through the old market quarters to discover indigenous textiles, pottery, and spices.",
        "duration_hours": 2.0,
        "indicative_cost_inr": 0.0,
        "best_time_of_day": "Evening",
        "practical_tips": "Support independent local artisans and verify handloom marks."
    },
    {
        "name": "Scenic Public Botanical Garden & Nature Stroll",
        "category": "Nature",
        "description": "Relax amid indigenous flora, landscaped lawns, and tranquil nature walkways.",
        "duration_hours": 1.5,
        "indicative_cost_inr": 50.0,
        "best_time_of_day": "Morning",
        "practical_tips": "Ideal time for peaceful morning birdwatching and quiet walks."
    },
    {
        "name": "Panoramic Sunset Viewpoint & Photography",
        "category": "Sightseeing",
        "description": "Visit the highest regional hill, ridge, or promenade for golden hour horizon views.",
        "duration_hours": 1.5,
        "indicative_cost_inr": 50.0,
        "best_time_of_day": "Evening",
        "practical_tips": "Arrive 45 minutes before sunset for the best lighting and seating."
    },
    {
        "name": "Regional Culinary Street Food & Night Market Trail",
        "category": "Food",
        "description": "Sample acclaimed local snacks, savories, and traditional confectioneries.",
        "duration_hours": 2.0,
        "indicative_cost_inr": 250.0,
        "best_time_of_day": "Evening",
        "practical_tips": "Choose busy stalls with high customer turnover to ensure freshness."
    },
    {
        "name": "Suburban Nature Trek or Scenic Waterfront Excursion",
        "category": "Adventure",
        "description": "Take a short day trail to nearby lakes, waterfalls, or scenic foothill paths.",
        "duration_hours": 3.0,
        "indicative_cost_inr": 200.0,
        "best_time_of_day": "Morning",
        "practical_tips": "Carry hydration, sunscreen, and wear comfortable walking shoes."
    },
    {
        "name": "Leisure Cafe Stroll & Cultural Immersion",
        "category": "Relaxation",
        "description": "Unwind in a popular neighborhood cafe, enjoy regional tea/coffee, and observe everyday pace.",
        "duration_hours": 1.5,
        "indicative_cost_inr": 150.0,
        "best_time_of_day": "Afternoon",
        "practical_tips": "Great opportunity for travel journaling and itinerary review."
    }
]

GENERIC_MEAL_PLANS = {
    "Vegetarian": {
        "breakfast": "Regional vegetarian breakfast (e.g., fresh idli/poha/paratha with hot tea or coffee).",
        "lunch": "Wholesome seasonal vegetarian thali with lentils, seasonal vegetables, flatbreads, and rice.",
        "dinner": "Comforting regional vegetarian dinner (cottage cheese curry, dal tadka, steamed basmati rice, and roti)."
    },
    "Vegan": {
        "breakfast": "Fresh seasonal fruit bowl, vegetable poha / oats, and herbal infusion / black coffee.",
        "lunch": "Plant-based Indian thali: yellow dal, dry spiced potatoes, vegetable curry, phulkas, and fresh salad.",
        "dinner": "Stir-fried farm vegetables, steamed rice, spiced lentil soup, and roasted poppadums."
    },
    "No Preference": {
        "breakfast": "Hearty breakfast with eggs, local flatbreads or pancakes, fresh fruit, and hot beverage.",
        "lunch": "Signature regional specialty lunch (local poultry, coastal seafood, or rich aromatic curry with rice).",
        "dinner": "Multi-course dinner featuring regional grills, kebabs or curry specialties with artisanal breads."
    },
    "Other": {
        "breakfast": "Fresh fruit platter, toast or boiled grains, and mild breakfast tea.",
        "lunch": "Balanced balanced meal: steamed rice or breads, mild lentil broth, and choice of protein or vegetables.",
        "dinner": "Light freshly prepared dinner adhering to personal dietary guidelines."
    }
}


@dataclass
class ActivityItem:
    """Structured activity slot."""
    name: str
    category: str
    description: str
    duration_hours: float
    indicative_cost_inr: float
    best_time_of_day: str
    recommendation_type: str  # "Catalog Suggestion" or "Generic Recommendation"
    practical_tips: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DailyItinerary:
    """Itinerary plan for a single day."""
    day_number: int
    date_str: str
    theme: str
    morning_activity: ActivityItem
    afternoon_activity: ActivityItem
    evening_activity: ActivityItem
    breakfast_suggestion: str
    lunch_suggestion: str
    dinner_suggestion: str
    practical_notes: str
    day_estimated_activity_cost_inr: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "day_number": self.day_number,
            "date": self.date_str,
            "theme": self.theme,
            "morning": self.morning_activity.to_dict(),
            "afternoon": self.afternoon_activity.to_dict(),
            "evening": self.evening_activity.to_dict(),
            "meals": {
                "breakfast": self.breakfast_suggestion,
                "lunch": self.lunch_suggestion,
                "dinner": self.dinner_suggestion,
            },
            "practical_notes": self.practical_notes,
            "day_estimated_activity_cost_inr": self.day_estimated_activity_cost_inr,
        }


@dataclass
class GeneratedItinerary:
    """Complete generated itinerary including budget summary and metadata."""
    destination: str
    is_catalog_destination: bool
    destination_tagline: str
    destination_description: str
    start_date: str
    end_date: str
    num_days: int
    num_nights: int
    travelers: int
    travel_style: str
    daily_pace: str
    dietary_preference: str
    days: list[DailyItinerary] = field(default_factory=list)
    budget: dict[str, Any] = field(default_factory=dict)
    disclaimer: str = (
        "This itinerary was generated deterministically based on your preferences. "
        "All activity admissions, durations, and meal suggestions are illustrative estimates "
        "and subject to seasonal verification before traveling."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "destination": self.destination,
            "is_catalog_destination": self.is_catalog_destination,
            "destination_tagline": self.destination_tagline,
            "destination_description": self.destination_description,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "num_days": self.num_days,
            "num_nights": self.num_nights,
            "travelers": self.travelers,
            "travel_style": self.travel_style,
            "daily_pace": self.daily_pace,
            "dietary_preference": self.dietary_preference,
            "days": [d.to_dict() for d in self.days],
            "budget": self.budget,
            "disclaimer": self.disclaimer,
        }


def load_destination_catalog(catalog_path: str | Path | None = None) -> dict[str, Any]:
    """Loads and returns destination catalog from data/destinations.json."""
    if catalog_path is None:
        catalog_path = Path(__file__).resolve().parent.parent / "data" / "destinations.json"
    else:
        catalog_path = Path(catalog_path)

    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.error("Failed to load destination catalog from %s: %s", catalog_path, exc)
        return {"destinations": []}


def find_destination_in_catalog(
    destination_name: str,
    catalog: dict[str, Any],
) -> dict[str, Any] | None:
    """Finds matching destination object by name or alias (case-insensitive)."""
    if not destination_name or not catalog:
        return None

    cleaned = destination_name.strip().lower()
    for dest in catalog.get("destinations", []):
        if dest.get("name", "").strip().lower() == cleaned:
            return dest
        if dest.get("id", "").strip().lower() == cleaned:
            return dest
        # Also check partial match for common names
        if cleaned in dest.get("name", "").strip().lower():
            return dest
    return None


def filter_and_prioritize_attractions(
    attractions: list[dict[str, Any]],
    travel_style: str,
    preferred_activities: Sequence[str] | None,
) -> list[dict[str, Any]]:
    """Scores and orders attractions according to travel style and activity preferences."""
    preferred_set = set(preferred_activities or [])

    # Style affinity mapping
    style_affinities = {
        "Cultural": {"Historical Landmarks": 3.0, "Museums": 2.5, "Cultural": 3.0, "Shopping": 1.5},
        "Adventure": {"Adventure": 3.5, "Nature": 2.5, "Sightseeing": 1.5},
        "Relaxation": {"Nature": 3.0, "Relaxation": 3.5, "Sightseeing": 1.5, "Food": 1.5},
        "Family": {"Sightseeing": 2.5, "Historical Landmarks": 2.0, "Nature": 2.0, "Food": 1.5},
        "Budget": {"Sightseeing": 2.5, "Nature": 2.0, "Shopping": 1.5},
        "Luxury": {"Cultural": 2.5, "Sightseeing": 2.0, "Food": 2.5, "Relaxation": 2.0},
    }

    affinity_weights = style_affinities.get(travel_style, {})

    def score_attraction(attr: dict[str, Any]) -> float:
        cat = attr.get("category", "")
        score = 1.0

        # Preference match bonus
        if cat in preferred_set:
            score += 4.0

        # Style affinity bonus
        score += affinity_weights.get(cat, 0.0)

        # Cost penalty for Budget travel style
        if travel_style == "Budget" and attr.get("indicative_cost_inr", 0) > 300:
            score -= 1.0

        return score

    # Sort descending by score
    return sorted(attractions, key=score_attraction, reverse=True)


def build_activity_slot(
    attr_data: dict[str, Any],
    slot_time: str,
    pace: str,
    is_catalog: bool,
) -> ActivityItem:
    """Builds an ActivityItem, adjusting duration if necessary based on pace."""
    duration = float(attr_data.get("duration_hours", 2.0))

    # Pace pacing adjustments
    if pace == "Relaxed":
        duration = min(duration, 2.0)
    elif pace == "Packed":
        duration = max(duration, 1.5)

    return ActivityItem(
        name=attr_data.get("name", "Local Exploration"),
        category=attr_data.get("category", "Sightseeing"),
        description=attr_data.get("description", "Discover local points of interest."),
        duration_hours=round(duration, 1),
        indicative_cost_inr=float(attr_data.get("indicative_cost_inr", 0.0)),
        best_time_of_day=slot_time,
        recommendation_type="Catalog Suggestion" if is_catalog else "Generic Recommendation",
        practical_tips=attr_data.get("practical_tips", "Check local timings upon arrival."),
    )


def build_leisure_activity(slot_time: str, pace: str) -> ActivityItem:
    """Creates a relaxing pause or leisure activity when pace warrants lower intensity."""
    if slot_time == "Afternoon":
        return ActivityItem(
            name="Afternoon Leisure & Rest Break",
            category="Relaxation",
            description="Recharge at your accommodation, visit a local tea salon, or enjoy quiet personal time.",
            duration_hours=1.5,
            indicative_cost_inr=0.0,
            best_time_of_day="Afternoon",
            recommendation_type="Generic Recommendation",
            practical_tips="Paced relaxation allows more energy for evening activities.",
        )
    return ActivityItem(
        name="Serene Evening Walk & Reflection",
        category="Relaxation",
        description="Take an unhurried sunset stroll through peaceful local boulevards or gardens.",
        duration_hours=1.5,
        indicative_cost_inr=0.0,
        best_time_of_day="Evening",
        recommendation_type="Generic Recommendation",
        practical_tips="Soak in the ambient neighborhood atmosphere.",
    )


def generate_itinerary(
    destination: str,
    start_date: date,
    end_date: date,
    travelers: int,
    budget: float,
    travel_style: str = "Cultural",
    preferred_activities: Sequence[str] | None = None,
    accommodation: str = "Standard Hotel",
    transportation: str = "Public Transport",
    dietary: str = "No Preference",
    pace: str = "Balanced",
    catalog_path: str | Path | None = None,
) -> GeneratedItinerary:
    """Core deterministic itinerary generation function.

    Generates a structured day-by-day itinerary with verified date stepping,
    customized pace distribution, activity deduplication, dietary meal matching,
    and integrated budget calculations.
    """
    if start_date > end_date:
        raise ValueError(f"Start date ({start_date}) cannot be after end date ({end_date}).")

    num_days = (end_date - start_date).days + 1
    num_nights = max(0, num_days - 1)

    catalog = load_destination_catalog(catalog_path)
    catalog_dest = find_destination_in_catalog(destination, catalog)
    is_catalog = catalog_dest is not None

    if is_catalog and catalog_dest is not None:
        dest_name = catalog_dest.get("name", destination.strip().title())
        dest_tagline = catalog_dest.get("tagline", "Curated Travel Destination")
        dest_description = catalog_dest.get("description", "")
        raw_attractions = list(catalog_dest.get("attractions", []))
        prioritized_attractions = filter_and_prioritize_attractions(
            raw_attractions, travel_style, preferred_activities
        )
        catalog_meals = catalog_dest.get("meals", {})
        general_notes = catalog_dest.get("notes", "Wear comfortable shoes and stay hydrated.")
    else:
        dest_name = destination.strip().title()
        dest_tagline = f"Custom Exploration of {dest_name}"
        dest_description = (
            f"Personalized travel itinerary tailored for {dest_name}. "
            "Because this destination is not in our verified catalog, structured generic recommendations are provided."
        )
        prioritized_attractions = list(GENERIC_ACTIVITY_TEMPLATES)
        catalog_meals = {}
        general_notes = "Confirm local attraction hours, local transit cards, and seasonal advisories upon arrival."

    # Pool of attractions for scheduling without duplicates
    available_attractions = list(prioritized_attractions)
    generic_pool = list(GENERIC_ACTIVITY_TEMPLATES)

    def get_next_attraction() -> tuple[dict[str, Any], bool]:
        """Pulls next attraction, falling back to generic templates if catalog exhausted."""
        if available_attractions:
            return available_attractions.pop(0), is_catalog
        # If catalog is exhausted, reuse generic templates cycling gracefully
        idx = len(generic_pool) % len(GENERIC_ACTIVITY_TEMPLATES)
        item = GENERIC_ACTIVITY_TEMPLATES[idx]
        generic_pool.append(item)
        return item, False

    daily_itineraries: list[DailyItinerary] = []
    daily_activity_costs_per_person: list[float] = []

    for day_idx in range(num_days):
        current_date = start_date + timedelta(days=day_idx)
        date_str = current_date.strftime("%Y-%m-%d")
        day_num = day_idx + 1

        # 1. Pacing & Slot selection
        # Relaxed: 1 primary activity + 1 light activity + 1 leisure break
        # Balanced: 3 activities (Morning, Afternoon, Evening)
        # Packed: 3 full activities with active pacing
        attr1, is_cat1 = get_next_attraction()
        morning_slot = build_activity_slot(attr1, "Morning", pace, is_cat1)

        if pace == "Relaxed":
            afternoon_slot = build_leisure_activity("Afternoon", pace)
            attr2, is_cat2 = get_next_attraction()
            evening_slot = build_activity_slot(attr2, "Evening", pace, is_cat2)
        elif pace == "Packed":
            attr2, is_cat2 = get_next_attraction()
            afternoon_slot = build_activity_slot(attr2, "Afternoon", pace, is_cat2)
            attr3, is_cat3 = get_next_attraction()
            evening_slot = build_activity_slot(attr3, "Evening", pace, is_cat3)
        else:  # Balanced
            attr2, is_cat2 = get_next_attraction()
            afternoon_slot = build_activity_slot(attr2, "Afternoon", pace, is_cat2)
            attr3, is_cat3 = get_next_attraction()
            evening_slot = build_activity_slot(attr3, "Evening", pace, is_cat3)

        # 2. Daily activity cost sum
        day_act_cost = (
            morning_slot.indicative_cost_inr
            + afternoon_slot.indicative_cost_inr
            + evening_slot.indicative_cost_inr
        )
        daily_activity_costs_per_person.append(day_act_cost)

        # 3. Meal suggestions tailored to dietary preferences
        breakfast_rec = select_meal(catalog_meals.get("breakfast", []), dietary, "breakfast")
        lunch_rec = select_meal(catalog_meals.get("lunch", []), dietary, "lunch")
        dinner_rec = select_meal(catalog_meals.get("dinner", []), dietary, "dinner")

        # 4. Day Theme
        theme = f"Day {day_num}: {morning_slot.category} & {evening_slot.category} Discovery"

        # 5. Day Notes
        day_notes = (
            f"{general_notes} Start morning activity around 9:00 AM. Allocate 1-2 hours for lunch and hydration."
        )

        daily_itineraries.append(
            DailyItinerary(
                day_number=day_num,
                date_str=date_str,
                theme=theme,
                morning_activity=morning_slot,
                afternoon_activity=afternoon_slot,
                evening_activity=evening_slot,
                breakfast_suggestion=breakfast_rec,
                lunch_suggestion=lunch_rec,
                dinner_suggestion=dinner_rec,
                practical_notes=day_notes,
                day_estimated_activity_cost_inr=round(day_act_cost, 2),
            )
        )

    # 4. Integrated Budget Breakdown
    total_act_cost_per_traveler = sum(daily_activity_costs_per_person)
    budget_breakdown = calculate_budget(
        total_budget=budget,
        num_days=num_days,
        travelers=travelers,
        travel_style=travel_style,
        accommodation_type=accommodation,
        transportation_type=transportation,
        total_activity_cost_per_traveler=total_act_cost_per_traveler,
        daily_activity_costs_per_traveler=daily_activity_costs_per_person,
    )

    return GeneratedItinerary(
        destination=dest_name,
        is_catalog_destination=is_catalog,
        destination_tagline=dest_tagline,
        destination_description=dest_description,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        num_days=num_days,
        num_nights=num_nights,
        travelers=travelers,
        travel_style=travel_style,
        daily_pace=pace,
        dietary_preference=dietary,
        days=daily_itineraries,
        budget=budget_breakdown.to_dict(),
    )


def select_meal(
    meal_list: list[dict[str, Any]],
    dietary: str,
    meal_type: str,
) -> str:
    """Selects an appropriate meal suggestion matching user's dietary preferences."""
    if not meal_list:
        fallback = GENERIC_MEAL_PLANS.get(dietary, GENERIC_MEAL_PLANS["No Preference"])
        return fallback.get(meal_type, "Wholesome local meal.")

    # Dietary match filter
    dietary_clean = dietary.strip().lower()
    for meal in meal_list:
        meal_diet = meal.get("diet", "").strip().lower()
        if dietary_clean == "vegetarian" and meal_diet in ["vegetarian", "vegan"]:
            return f"{meal.get('name')} ({meal.get('style', 'Local')})"
        if dietary_clean == "vegan" and meal_diet == "vegan":
            return f"{meal.get('name')} ({meal.get('style', 'Plant-based')})"
        if dietary_clean in ["no preference", "other"]:
            return f"{meal.get('name')} ({meal.get('style', 'Specialty')})"

    # If no strict match found, return first available or generic
    first = meal_list[0]
    return f"{first.get('name')} ({first.get('style', 'Local Specialty')})"


def sanitize_filename(destination_name: str) -> str:
    """Sanitizes user destination string into a safe, alphanumeric filename."""
    import re
    cleaned = re.sub(r"[^\w\s-]", "", destination_name.strip().lower())
    cleaned = re.sub(r"[-\s]+", "_", cleaned)
    return cleaned or "destination"


def format_itinerary_as_text(itinerary: GeneratedItinerary) -> str:
    """Formats the generated itinerary into a clean, comprehensive plain-text export document."""
    lines: list[str] = []
    separator = "=" * 76
    sub_sep = "-" * 76

    lines.append(separator)
    lines.append("PERSONALIZED TRAVEL ITINERARY PLANNER")
    lines.append("Generated Travel Blueprint & Smart Budget Assessment")
    lines.append(separator)
    lines.append("")

    # Trip Overview
    lines.append("1. TRIP OVERVIEW")
    lines.append(sub_sep)
    lines.append(f"Destination:         {itinerary.destination}")
    lines.append(f"Destination Type:    {'Verified Bundled Catalog' if itinerary.is_catalog_destination else 'Custom Destination (Adaptive Planning)'}")
    lines.append(f"Tagline:             {itinerary.destination_tagline}")
    lines.append(f"Dates:               {itinerary.start_date} to {itinerary.end_date} ({itinerary.num_days} day(s), {itinerary.num_nights} night(s))")
    lines.append(f"Travelers:           {itinerary.travelers} person(s)")
    lines.append(f"Travel Style:        {itinerary.travel_style}")
    lines.append(f"Daily Pace:          {itinerary.daily_pace}")
    lines.append(f"Dietary Preference:  {itinerary.dietary_preference}")
    lines.append("")

    # Budget Summary
    b = itinerary.budget
    lines.append("2. BUDGET & EXPENSE SUMMARY (All amounts in INR)")
    lines.append(sub_sep)
    lines.append(f"Total Budget Specified:        ₹{b.get('total_budget', 0):,.2f}")
    lines.append(f"Estimated Total Trip Cost:     ₹{b.get('estimated_total_cost', 0):,.2f}")
    variance_str = (
        f"OVER BUDGET by ₹{abs(b.get('remaining_budget', 0)):,.2f}"
        if b.get("is_over_budget")
        else f"REMAINING SURPLUS: ₹{b.get('remaining_budget', 0):,.2f}"
    )
    lines.append(f"Budget Variance Status:        {variance_str}")
    lines.append(f"Estimated Cost Per Traveler:   ₹{b.get('cost_per_traveler', 0):,.2f}")
    lines.append("")
    lines.append("Category Breakdown:")
    lines.append(f"  • Accommodation ({itinerary.num_nights} nights):     ₹{b.get('accommodation_cost', 0):,.2f}")
    lines.append(f"  • Food & Dining ({itinerary.num_days} days):         ₹{b.get('food_cost', 0):,.2f}")
    lines.append(f"  • Local Transportation:        ₹{b.get('transportation_cost', 0):,.2f}")
    lines.append(f"  • Activities & Admissions:     ₹{b.get('activities_cost', 0):,.2f}")
    lines.append(f"  • Contingency Reserve (7%):    ₹{b.get('contingency_cost', 0):,.2f}")
    lines.append("")

    if b.get("cost_saving_suggestions"):
        lines.append("Cost Optimization Recommendations:")
        for tip in b.get("cost_saving_suggestions", []):
            lines.append(f"  [!] {tip}")
        lines.append("")

    # Daily Schedule
    lines.append("3. DAY-BY-DAY ITINERARY")
    lines.append(sub_sep)

    for day in itinerary.days:
        lines.append(f"DAY {day.day_number} | {day.date_str} - {day.theme}")
        lines.append("-" * 50)

        # Morning
        lines.append(f"  [MORNING]   {day.morning_activity.name} ({day.morning_activity.recommendation_type})")
        lines.append(f"              Category: {day.morning_activity.category} | Est. Duration: {day.morning_activity.duration_hours} hrs | Est. Cost: ₹{day.morning_activity.indicative_cost_inr:,.0f}/person")
        lines.append(f"              Description: {day.morning_activity.description}")
        if day.morning_activity.practical_tips:
            lines.append(f"              Tip: {day.morning_activity.practical_tips}")

        # Afternoon
        lines.append(f"  [AFTERNOON] {day.afternoon_activity.name} ({day.afternoon_activity.recommendation_type})")
        lines.append(f"              Category: {day.afternoon_activity.category} | Est. Duration: {day.afternoon_activity.duration_hours} hrs | Est. Cost: ₹{day.afternoon_activity.indicative_cost_inr:,.0f}/person")
        lines.append(f"              Description: {day.afternoon_activity.description}")
        if day.afternoon_activity.practical_tips:
            lines.append(f"              Tip: {day.afternoon_activity.practical_tips}")

        # Evening
        lines.append(f"  [EVENING]   {day.evening_activity.name} ({day.evening_activity.recommendation_type})")
        lines.append(f"              Category: {day.evening_activity.category} | Est. Duration: {day.evening_activity.duration_hours} hrs | Est. Cost: ₹{day.evening_activity.indicative_cost_inr:,.0f}/person")
        lines.append(f"              Description: {day.evening_activity.description}")
        if day.evening_activity.practical_tips:
            lines.append(f"              Tip: {day.evening_activity.practical_tips}")

        # Meals
        lines.append("  [SUGGESTED MEALS]")
        lines.append(f"    • Breakfast: {day.breakfast_suggestion}")
        lines.append(f"    • Lunch:     {day.lunch_suggestion}")
        lines.append(f"    • Dinner:    {day.dinner_suggestion}")

        # Day Notes
        lines.append(f"  [PRACTICAL LOGISTICS]: {day.practical_notes}")
        lines.append("")

    # Assumptions & Disclaimers
    lines.append("4. MODELING ASSUMPTIONS & DISCLAIMER")
    lines.append(sub_sep)
    lines.append("Planning Assumptions:")
    lines.append("  • Accommodation is computed based on nights (days - 1, or 0 for same-day trips).")
    lines.append("  • Hotel rooms assume standard double occupancy (2 travelers per room); hostels are per bed.")
    lines.append("  • Private vehicles and taxis assume standard capacity (up to 4 travelers per car).")
    lines.append("  • A 7% contingency reserve is included for fluctuating regional tariffs and tips.")
    lines.append("")
    lines.append("Important Travel Disclaimer:")
    lines.append(f"  {itinerary.disclaimer}")
    lines.append("  Always verify monument opening days, mandatory entry tickets, permits, and current")
    lines.append("  weather conditions with official local authorities prior to commencement of travel.")
    lines.append(separator)

    return "\n".join(lines)

