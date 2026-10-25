"""Personalized Travel Itinerary Planner
Capstone Application for Academic Submission & Faculty Demonstration.
Deployable on Streamlit Community Cloud.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.itinerary import (
    format_itinerary_as_text,
    generate_itinerary,
    load_destination_catalog,
    sanitize_filename,
)
from utils.validation import (
    VALID_ACCOMMODATIONS,
    VALID_ACTIVITY_CATEGORIES,
    VALID_DAILY_PACES,
    VALID_DIETARY_PREFERENCES,
    VALID_TRANSPORTATIONS,
    VALID_TRAVEL_STYLES,
    validate_trip_inputs,
)

# Setup privacy-preserving application logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("travel_planner.app")

# Page Configuration
st.set_page_config(
    page_title="Personalized Travel Itinerary Planner",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom Styling for Professional Travel-Tech Aesthetic
st.markdown(
    """
    <style>
    /* Main container and typography */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .main {
        background-color: #F8FAFC;
    }

    /* Hero Section Styling */
    .hero-container {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 60%, #0D9488 100%);
        color: #FFFFFF;
        padding: 3rem 2.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.15);
    }
    .hero-title {
        font-size: 2.6rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin-bottom: 0.75rem;
        color: #FFFFFF;
    }
    .hero-subtitle {
        font-size: 1.15rem;
        color: #E2E8F0;
        max-width: 820px;
        line-height: 1.6;
        margin-bottom: 1.75rem;
    }

    /* Feature Cards */
    .feature-card {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        color: #FFFFFF;
        backdrop-filter: blur(8px);
    }
    .feature-card h4 {
        margin: 0 0 0.5rem 0;
        font-size: 1.05rem;
        color: #38BDF8;
        font-weight: 600;
    }
    .feature-card p {
        margin: 0;
        font-size: 0.9rem;
        color: #CBD5E1;
        line-height: 1.45;
    }

    /* Section Cards */
    .content-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 1.75rem;
        margin-bottom: 1.75rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.04);
    }
    .section-header {
        font-size: 1.4rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.5rem;
    }
    .section-subheader {
        font-size: 0.95rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }

    /* Activity Slot Card */
    .activity-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #0D9488;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .activity-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px -2px rgba(13, 148, 136, 0.1);
    }
    .activity-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #0F172A;
        margin-bottom: 0.35rem;
    }
    .badge-tag {
        display: inline-block;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.2rem 0.55rem;
        border-radius: 6px;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .badge-cat {
        background-color: #E0F2FE;
        color: #0369A1;
    }
    .badge-dur {
        background-color: #F1F5F9;
        color: #475569;
    }
    .badge-cost {
        background-color: #FEF3C7;
        color: #B45309;
    }
    .badge-catalog {
        background-color: #DCFCE7;
        color: #15803D;
    }
    .badge-generic {
        background-color: #F3E8FF;
        color: #6B21A8;
    }

    /* Destination Browser Card */
    .dest-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 1.25rem;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    }
    .dest-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.2rem;
    }
    .dest-tagline {
        font-size: 0.85rem;
        color: #0D9488;
        font-weight: 500;
        margin-bottom: 0.6rem;
    }
    .dest-desc {
        font-size: 0.88rem;
        color: #475569;
        line-height: 1.45;
        margin-bottom: 0.8rem;
    }

    /* Metric Card Customization */
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }

    /* Alert Boxes */
    .overbudget-warning {
        background-color: #FFF7ED;
        border: 1px solid #FDBA74;
        border-radius: 12px;
        padding: 1.25rem;
        margin-top: 1rem;
        color: #9A3412;
    }

    .disclaimer-banner {
        background-color: #F1F5F9;
        border: 1px solid #CBD5E1;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        font-size: 0.88rem;
        color: #475569;
        line-height: 1.5;
        margin-top: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Session State Initialization
if "itinerary" not in st.session_state:
    st.session_state["itinerary"] = None

if "form_destination" not in st.session_state:
    st.session_state["form_destination"] = "Jaipur"

if "form_start_date" not in st.session_state:
    st.session_state["form_start_date"] = date.today() + timedelta(days=14)

if "form_end_date" not in st.session_state:
    st.session_state["form_end_date"] = date.today() + timedelta(days=17)

if "form_travelers" not in st.session_state:
    st.session_state["form_travelers"] = 2

if "form_budget" not in st.session_state:
    st.session_state["form_budget"] = 35000.0

if "form_style" not in st.session_state:
    st.session_state["form_style"] = "Cultural"

if "form_pace" not in st.session_state:
    st.session_state["form_pace"] = "Balanced"

if "form_accommodation" not in st.session_state:
    st.session_state["form_accommodation"] = "Standard Hotel"

if "form_transportation" not in st.session_state:
    st.session_state["form_transportation"] = "Public Transport"

if "form_dietary" not in st.session_state:
    st.session_state["form_dietary"] = "Vegetarian"

if "form_activities" not in st.session_state:
    st.session_state["form_activities"] = ["Historical Landmarks", "Sightseeing", "Food"]

# Load bundled catalog
catalog_path = Path(__file__).resolve().parent / "data" / "destinations.json"
catalog_data = load_destination_catalog(catalog_path)
catalog_destinations = catalog_data.get("destinations", [])
catalog_dest_names = [d["name"] for d in catalog_destinations]

# ==============================================================================
# SECTION A: HERO SECTION
# ==============================================================================
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-title">🧭 Personalized Travel Itinerary Planner</div>
        <div class="hero-subtitle">
            An intelligent, deterministic travel planning engine designed for transparent budgeting, 
            tailored activity pacing, and complete day-by-day itineraries across India and global destinations.
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-top: 1.5rem;">
            <div class="feature-card">
                <h4>🎯 Personalized Itineraries</h4>
                <p>Day-by-day morning, afternoon, and evening slots calibrated to your pace, dietary needs, and activity styles.</p>
            </div>
            <div class="feature-card">
                <h4>📊 Smart Budget Planning</h4>
                <p>Transparent INR cost modeling with clear shared lodging/vehicle allocations, dining tiers, and contingency reserves.</p>
            </div>
            <div class="feature-card">
                <h4>📥 Downloadable Travel Plans</h4>
                <p>Instantly export clean, offline-ready travel blueprints with complete cost summaries for your upcoming trip.</p>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Navigation Tabs
tab_plan, tab_discover, tab_about = st.tabs([
    "📋 Plan My Trip",
    "🌍 Explore Destinations",
    "ℹ️ Architecture & Methodology",
])

# ==============================================================================
# SECTION B & D & E: TRIP PLANNING & ITINERARY GENERATION
# ==============================================================================
with tab_plan:
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">Trip Planning Configuration</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subheader">Configure your destination, dates, budget, and travel preferences below to generate your customized blueprint.</div>',
        unsafe_allow_html=True,
    )

    with st.form("itinerary_form"):
        col1, col2, col3 = st.columns([1.2, 1, 1])

        with col1:
            dest_input = st.text_input(
                "Destination",
                value=st.session_state["form_destination"],
                help="Type any destination or choose from bundled catalog recommendations.",
                placeholder="e.g. Jaipur, Goa, Manali, Paris, Tokyo...",
            )
            st.caption("Bundled: " + ", ".join(catalog_dest_names[:5]) + ", etc.")

        with col2:
            start_dt = st.date_input(
                "Travel Start Date",
                value=st.session_state["form_start_date"],
                help="Inclusive arrival date.",
            )

        with col3:
            end_dt = st.date_input(
                "Travel End Date",
                value=st.session_state["form_end_date"],
                help="Inclusive departure date.",
            )

        col4, col5, col6 = st.columns([1, 1, 1])

        with col4:
            travelers_count = st.number_input(
                "Number of Travelers",
                min_value=1,
                max_value=20,
                value=int(st.session_state["form_travelers"]),
                step=1,
                help="Between 1 and 20 travelers.",
            )

        with col5:
            budget_amount = st.number_input(
                "Total Travel Budget (INR ₹)",
                min_value=500.0,
                max_value=10000000.0,
                value=float(st.session_state["form_budget"]),
                step=1000.0,
                format="%.0f",
                help="Total funds available for accommodation, local transit, dining, and activities.",
            )

        with col6:
            travel_style_sel = st.selectbox(
                "Travel Style",
                options=sorted(list(VALID_TRAVEL_STYLES)),
                index=sorted(list(VALID_TRAVEL_STYLES)).index(st.session_state["form_style"]),
                help="Guides activity prioritization and dining expenditure models.",
            )

        col7, col8 = st.columns([1.5, 1.5])

        with col7:
            activities_sel = st.multiselect(
                "Preferred Activities (Select all that apply)",
                options=sorted(list(VALID_ACTIVITY_CATEGORIES)),
                default=st.session_state["form_activities"],
                help="Select activity themes you would like emphasized in your schedule.",
            )

        with col8:
            daily_pace_sel = st.selectbox(
                "Daily Activity Pace",
                options=sorted(list(VALID_DAILY_PACES)),
                index=sorted(list(VALID_DAILY_PACES)).index(st.session_state["form_pace"]),
                help="Relaxed (1-2 activities + leisure), Balanced (2-3 activities), Packed (3-4 full activities).",
            )

        col9, col10, col11 = st.columns([1, 1, 1])

        with col9:
            accom_sel = st.selectbox(
                "Accommodation Preference",
                options=sorted(list(VALID_ACCOMMODATIONS)),
                index=sorted(list(VALID_ACCOMMODATIONS)).index(st.session_state["form_accommodation"]),
                help="Hostel (per bed), Hotel (double occupancy shared rooms).",
            )

        with col10:
            trans_sel = st.selectbox(
                "Local Transportation Preference",
                options=sorted(list(VALID_TRANSPORTATIONS)),
                index=sorted(list(VALID_TRANSPORTATIONS)).index(st.session_state["form_transportation"]),
                help="Public transit, rental vehicle, local taxi, or mixed.",
            )

        with col11:
            dietary_sel = st.selectbox(
                "Dietary Preference",
                options=sorted(list(VALID_DIETARY_PREFERENCES)),
                index=sorted(list(VALID_DIETARY_PREFERENCES)).index(st.session_state["form_dietary"]),
                help="Tailors daily culinary recommendations.",
            )

        submit_btn = st.form_submit_button(
            "🚀 Generate Personalized Itinerary",
            type="primary",
            use_container_width=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # Process Form Submission
    if submit_btn:
        # Update session state with current form values
        st.session_state["form_destination"] = dest_input
        st.session_state["form_start_date"] = start_dt
        st.session_state["form_end_date"] = end_dt
        st.session_state["form_travelers"] = travelers_count
        st.session_state["form_budget"] = budget_amount
        st.session_state["form_style"] = travel_style_sel
        st.session_state["form_pace"] = daily_pace_sel
        st.session_state["form_accommodation"] = accom_sel
        st.session_state["form_transportation"] = trans_sel
        st.session_state["form_dietary"] = dietary_sel
        st.session_state["form_activities"] = activities_sel

        # Validation Step
        val_result = validate_trip_inputs(
            destination=dest_input,
            start_date=start_dt,
            end_date=end_dt,
            travelers=travelers_count,
            budget=budget_amount,
            travel_style=travel_style_sel,
            activities=activities_sel,
            accommodation=accom_sel,
            transportation=trans_sel,
            dietary=dietary_sel,
            pace=daily_pace_sel,
        )

        if not val_result.is_valid:
            st.error("⚠️ Please resolve the following validation issues before generating your itinerary:")
            for err in val_result.errors:
                st.markdown(f"- **{err}**")
        else:
            if val_result.warnings:
                for warn in val_result.warnings:
                    st.warning(f"Note: {warn}")

            with st.spinner("Synthesizing deterministic travel itinerary and calculating budget..."):
                try:
                    generated_plan = generate_itinerary(
                        destination=dest_input,
                        start_date=start_dt,
                        end_date=end_dt,
                        travelers=int(travelers_count),
                        budget=float(budget_amount),
                        travel_style=travel_style_sel,
                        preferred_activities=activities_sel,
                        accommodation=accom_sel,
                        transportation=trans_sel,
                        dietary=dietary_sel,
                        pace=daily_pace_sel,
                        catalog_path=catalog_path,
                    )
                    st.session_state["itinerary"] = generated_plan
                    st.success("✨ Your personalized itinerary has been successfully generated!")
                except Exception as exc:
                    logger.exception("Failed to generate itinerary: %s", exc)
                    st.error(f"An unexpected error occurred while generating the plan: {exc}")

    # ==============================================================================
    # RENDER GENERATED ITINERARY & BUDGET DASHBOARD
    # ==============================================================================
    itinerary = st.session_state.get("itinerary")
    if itinerary:
        st.markdown("---")

        # Destination Overview Banner
        cat_badge = (
            '<span class="badge-tag badge-catalog">✓ Verified Bundled Catalog</span>'
            if itinerary.is_catalog_destination
            else '<span class="badge-tag badge-generic">⚡ Adaptive Custom Destination</span>'
        )

        st.markdown(
            f"""
            <div class="content-box" style="border-left: 6px solid #1E3A8A;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.5rem;">
                    <div>
                        <div class="section-header">{itinerary.destination}</div>
                        <div class="dest-tagline">{itinerary.destination_tagline}</div>
                    </div>
                    <div>{cat_badge}</div>
                </div>
                <p style="color: #475569; margin: 0.5rem 0 0.75rem 0; font-size: 0.95rem;">{itinerary.destination_description}</p>
                <div style="display: flex; flex-wrap: wrap; gap: 0.75rem; font-size: 0.88rem; color: #334155;">
                    <div>📅 <strong>Dates:</strong> {itinerary.start_date} to {itinerary.end_date} ({itinerary.num_days} days, {itinerary.num_nights} nights)</div>
                    <div>👥 <strong>Travelers:</strong> {itinerary.travelers}</div>
                    <div>⚡ <strong>Pace:</strong> {itinerary.daily_pace}</div>
                    <div>🍽️ <strong>Dietary:</strong> {itinerary.dietary_preference}</div>
                    <div>🎒 <strong>Style:</strong> {itinerary.travel_style}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Budget KPI Metrics
        b = itinerary.budget
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)

        with col_m1:
            st.metric("Total Trip Budget", f"₹{b.get('total_budget', 0):,.0f}")

        with col_m2:
            st.metric("Estimated Total Cost", f"₹{b.get('estimated_total_cost', 0):,.0f}")

        with col_m3:
            rem = b.get("remaining_budget", 0)
            is_over = b.get("is_over_budget", False)
            st.metric(
                "Budget Variance",
                f"{'Overspend' if is_over else 'Surplus'}: ₹{abs(rem):,.0f}",
                delta=f"{'-' if is_over else '+'}₹{abs(rem):,.0f}",
                delta_color="inverse" if is_over else "normal",
            )

        with col_m4:
            st.metric("Cost Per Traveler", f"₹{b.get('cost_per_traveler', 0):,.0f}")

        # Overspend Alert & Cost Optimization Suggestions
        if b.get("is_over_budget"):
            st.markdown(
                f"""
                <div class="overbudget-warning">
                    <h4 style="margin: 0 0 0.5rem 0; color: #9A3412;">⚠️ Budget Exceeded Warning</h4>
                    <p style="margin: 0 0 0.5rem 0; font-size: 0.92rem;">
                        The estimated cost of ₹{b.get('estimated_total_cost', 0):,.0f} exceeds your target budget of 
                        ₹{b.get('total_budget', 0):,.0f} by <strong>₹{abs(b.get('remaining_budget', 0)):,.0f}</strong>.
                    </p>
                    <ul style="margin: 0; padding-left: 1.25rem; font-size: 0.9rem;">
                        {''.join(f'<li>{tip}</li>' for tip in b.get('cost_saving_suggestions', []))}
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Interactive Budget Visualizations (Plotly)
        st.markdown('<div class="content-box" style="margin-top: 1.5rem;">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Expense Analytics & Cost Distribution</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-subheader">Interactive graphical breakdown of estimated expenditures by category and day.</div>',
            unsafe_allow_html=True,
        )

        col_chart1, col_chart2 = st.columns([1, 1.2])

        with col_chart1:
            # Donut Chart for Expense Categories
            cat_labels = ["Accommodation", "Food & Dining", "Local Transport", "Activities", "Contingency (7%)"]
            cat_values = [
                b.get("accommodation_cost", 0),
                b.get("food_cost", 0),
                b.get("transportation_cost", 0),
                b.get("activities_cost", 0),
                b.get("contingency_cost", 0),
            ]
            donut_fig = px.pie(
                names=cat_labels,
                values=cat_values,
                hole=0.48,
                color_discrete_sequence=["#2563EB", "#0D9488", "#F59E0B", "#8B5CF6", "#64748B"],
                title="Expense Allocation by Category",
            )
            donut_fig.update_traces(textposition="inside", textinfo="percent+label")
            donut_fig.update_layout(
                margin=dict(t=40, b=10, l=10, r=10),
                showlegend=False,
                height=320,
            )
            st.plotly_chart(donut_fig, use_container_width=True)

        with col_chart2:
            # Daily Stacked Bar Chart
            daily_breakdown = b.get("daily_expense_breakdown", [])
            if daily_breakdown:
                df_daily = pd.DataFrame(daily_breakdown)
                df_daily["Day Label"] = df_daily["day"].apply(lambda d: f"Day {d}")

                bar_fig = go.Figure()
                bar_fig.add_trace(go.Bar(name="Lodging", x=df_daily["Day Label"], y=df_daily["accommodation"], marker_color="#2563EB"))
                bar_fig.add_trace(go.Bar(name="Food", x=df_daily["Day Label"], y=df_daily["food"], marker_color="#0D9488"))
                bar_fig.add_trace(go.Bar(name="Transit", x=df_daily["Day Label"], y=df_daily["transportation"], marker_color="#F59E0B"))
                bar_fig.add_trace(go.Bar(name="Activities", x=df_daily["Day Label"], y=df_daily["activities"], marker_color="#8B5CF6"))
                bar_fig.add_trace(go.Bar(name="Contingency", x=df_daily["Day Label"], y=df_daily["contingency"], marker_color="#64748B"))

                bar_fig.update_layout(
                    barmode="stack",
                    title="Daily Cost Trajectory (INR ₹)",
                    xaxis_title="Itinerary Day",
                    yaxis_title="Estimated Expense (₹)",
                    margin=dict(t=40, b=10, l=10, r=10),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    height=320,
                )
                st.plotly_chart(bar_fig, use_container_width=True)

        # Transparent Cost Assumption Details
        with st.expander("🔍 View Transparent Cost Modeling Assumptions & Shared Expense Details"):
            st.markdown(
                """
                - **Accommodation**: Computed strictly by **nights** (days - 1; 0 nights for single-day excursions).
                  Hotels assume standard double rooms shared by up to 2 travelers; hostels are per bed.
                - **Local Transportation**: Public transit is charged per traveler; rental vehicles and taxis are shared (up to 4 travelers per car).
                - **Food & Dining**: Calculated per traveler per day based on selected travel style and culinary preferences.
                - **Activities**: Summed from admissions and ticket estimates per traveler.
                - **Contingency Reserve**: A standard 7% buffer is added to absorb local price fluctuations and tips.
                """
            )
            detail_data = []
            for item in b.get("details", []):
                detail_data.append({
                    "Category": item.get("category_name"),
                    "Total Cost (INR)": f"₹{item.get('total_cost', 0):,.2f}",
                    "Cost Model": "Shared Across Travelers" if item.get("is_shared") else "Per-Traveler Direct",
                    "Calculation Logic": item.get("explanation"),
                })
            st.dataframe(pd.DataFrame(detail_data), use_container_width=True, hide_index=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # Day-by-Day Itinerary Cards
        st.markdown('<div class="content-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Detailed Day-by-Day Itinerary</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-subheader">Explore structured morning, afternoon, and evening slots with curated meal ideas.</div>',
            unsafe_allow_html=True,
        )

        day_tabs = st.tabs([f"Day {d.day_number} ({d.date_str})" for d in itinerary.days])

        for idx, (d_tab, day) in enumerate(zip(day_tabs, itinerary.days)):
            with d_tab:
                st.markdown(f"#### 📅 {day.theme}")
                st.caption(f"Estimated Activity Admissions for Day {day.day_number}: ₹{day.day_estimated_activity_cost_inr:,.0f} per traveler")

                # Slots rendering
                slots = [
                    ("🌅 Morning", day.morning_activity),
                    ("☀️ Afternoon", day.afternoon_activity),
                    ("🌙 Evening", day.evening_activity),
                ]

                for slot_title, act in slots:
                    badge_rec_class = "badge-catalog" if act.recommendation_type == "Catalog Suggestion" else "badge-generic"
                    st.markdown(
                        f"""
                        <div class="activity-card">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
                                <div class="activity-title">{slot_title}: {act.name}</div>
                                <div>
                                    <span class="badge-tag {badge_rec_class}">{act.recommendation_type}</span>
                                    <span class="badge-tag badge-cat">{act.category}</span>
                                    <span class="badge-tag badge-dur">⏱️ {act.duration_hours} hrs</span>
                                    <span class="badge-tag badge-cost">💰 ₹{act.indicative_cost_inr:,.0f}/person</span>
                                </div>
                            </div>
                            <p style="color: #475569; margin: 0.4rem 0 0.5rem 0; font-size: 0.92rem;">{act.description}</p>
                            {f'<div style="font-size: 0.85rem; color: #0D9488;"><strong>💡 Practical Tip:</strong> {act.practical_tips}</div>' if act.practical_tips else ''}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Meal Suggestions & Notes
                col_m_rec, col_n_rec = st.columns([1.2, 1])

                with col_m_rec:
                    st.markdown(
                        f"""
                        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1rem; margin-top: 0.5rem;">
                            <div style="font-weight: 600; color: #0F172A; margin-bottom: 0.4rem;">🍽️ Suggested Meals ({itinerary.dietary_preference})</div>
                            <div style="font-size: 0.88rem; color: #334155; margin-bottom: 0.25rem;">• <strong>Breakfast:</strong> {day.breakfast_suggestion}</div>
                            <div style="font-size: 0.88rem; color: #334155; margin-bottom: 0.25rem;">• <strong>Lunch:</strong> {day.lunch_suggestion}</div>
                            <div style="font-size: 0.88rem; color: #334155;">• <strong>Dinner:</strong> {day.dinner_suggestion}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with col_n_rec:
                    st.markdown(
                        f"""
                        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1rem; margin-top: 0.5rem;">
                            <div style="font-weight: 600; color: #0F172A; margin-bottom: 0.4rem;">📋 Day Logistics & Notes</div>
                            <div style="font-size: 0.88rem; color: #475569; line-height: 1.45;">{day.practical_notes}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.markdown("</div>", unsafe_allow_html=True)

        # Download / Export Section
        st.markdown('<div class="content-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Download Offline Itinerary Blueprint</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-subheader">Save your complete day-by-day travel plan, expense calculations, and disclaimers as a formatted text file.</div>',
            unsafe_allow_html=True,
        )

        export_text = format_itinerary_as_text(itinerary)
        safe_filename = f"travel_itinerary_{sanitize_filename(itinerary.destination)}.txt"

        col_d1, col_d2 = st.columns([1, 2])
        with col_d1:
            st.download_button(
                label=f"📥 Download {safe_filename}",
                data=export_text,
                file_name=safe_filename,
                mime="text/plain",
                type="primary",
                use_container_width=True,
            )
        with col_d2:
            st.caption(
                f"Generated file size: ~{len(export_text):,} characters. "
                "Contains all itinerary details, cost assumptions, and travel tips."
            )

        st.markdown("</div>", unsafe_allow_html=True)

    else:
        # Prompt user to generate itinerary
        st.info("👋 Welcome! Fill out the travel preferences above and click **'Generate Personalized Itinerary'** to build your custom schedule.")

# ==============================================================================
# SECTION C: DESTINATION DISCOVERY
# ==============================================================================
with tab_discover:
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">Curated Destination Catalog</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subheader">'
        'Browse sample destinations from our verified catalog with illustrative attractions, '
        'visit durations, and local tips. You can also type any unlisted city in the planning form!'
        '</div>',
        unsafe_allow_html=True,
    )

    # Render destinations in a responsive 2-column card grid
    for i in range(0, len(catalog_destinations), 2):
        col_c1, col_c2 = st.columns(2)
        batch = catalog_destinations[i : i + 2]

        for col, dest in zip([col_c1, col_c2], batch):
            with col:
                st.markdown(
                    f"""
                    <div class="dest-card">
                        <div>
                            <div class="dest-title">📍 {dest.get('name')} <span style="font-size: 0.85rem; font-weight: normal; color: #64748B;">({dest.get('state')})</span></div>
                            <div class="dest-tagline">{dest.get('tagline')}</div>
                            <div class="dest-desc">{dest.get('description')}</div>
                            <div style="margin-bottom: 0.5rem;">
                                {''.join(f'<span class="badge-tag badge-cat">{s}</span>' for s in dest.get('styles', []))}
                            </div>
                            <div style="font-size: 0.82rem; color: #475569; margin-bottom: 0.5rem;">
                                🌡️ <strong>Climate:</strong> {dest.get('climate_summary')}<br>
                                ⏱️ <strong>Ideal Duration:</strong> ~{dest.get('suggested_duration_days')} days
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(f"Select {dest.get('name')} for Planning", key=f"btn_dest_{dest.get('id')}"):
                    st.session_state["form_destination"] = dest.get("name")
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# SECTION: ARCHITECTURE & METHODOLOGY (FOR FACULTY & PORTAL EVALUATION)
# ==============================================================================
with tab_about:
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">Capstone Project Architecture & Technical Report</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subheader">Academic submission details, system architecture, and algorithmic design.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        ### 1. Problem Statement & Motivation
        Traditional travel planners either rely on rigid static templates or heavy external generative AI APIs that introduce 
        latency, recurring subscription costs, and non-deterministic hallucinations regarding attraction scheduling. 
        This capstone project provides an offline-capable, deterministic, rule-based travel intelligence engine that 
        generates personalized day-by-day itineraries with transparent INR budget breakdowns.

        ### 2. Architectural Principles
        - **Separation of Concerns**: Strict decoupling of Presentation (`app.py`), Itinerary Generation (`utils/itinerary.py`), 
          Budget Modeling (`utils/budget.py`), and Validation (`utils/validation.py`).
        - **Zero Paid Dependencies**: Operates completely without external commercial APIs, proprietary databases, or tracking.
        - **Deterministic Recommendation Engine**: Transparent scoring heuristics match traveler preferences to catalog items without hallucinations.
        - **Budget Integrity**: Component costs (accommodation, meals, local transit, admissions, and 7% contingency) strictly sum to total trip expense.
        - **Defensive Error Handling**: Input validation guards against invalid date sequences, out-of-bounds traveler counts, and malformed inputs.

        ### 3. Technology Stack
        - **Runtime**: Python 3.11+
        - **UI Dashboard**: Streamlit
        - **Data Processing**: Pandas
        - **Interactive Visualizations**: Plotly Express & Plotly Graph Objects
        - **Automated Testing**: Pytest
        """,
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# FOOTER & GLOBAL DISCLAIMER
# ==============================================================================
st.markdown(
    """
    <div class="disclaimer-banner">
        <strong>⚖️ Educational & Planning Disclaimer:</strong> 
        All attraction costs, entry admissions, operating schedules, visit durations, and meal recommendations provided by this application 
        are illustrative benchmarks. They are not live-verified in real-time. Travelers must independently confirm current monument timings, 
        ticket availability, transit schedules, and entry permits prior to travel.
    </div>
    <div style="text-align: center; color: #94A3B8; font-size: 0.8rem; margin: 1.5rem 0;">
        Personalized Travel Itinerary Planner • Academic Capstone Submission • Built with Python & Streamlit
    </div>
    """,
    unsafe_allow_html=True,
)
