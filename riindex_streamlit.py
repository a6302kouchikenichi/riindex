from __future__ import annotations

from typing import List

import streamlit as st

from riindex import estimate_current_iri, run_simulation, simulate_one_year


st.set_page_config(page_title="RI Index Simulator", layout="wide")

st.title("Road Roughness and User Cost Simulator")
st.caption("Interactive UI for simplified HDM-style IRI progression and cost estimation")

with st.sidebar:
    st.header("Current Condition Inputs")
    crack_rate = st.number_input("Crack rate (%)", min_value=0.0, value=12.0, step=0.5)
    pothole_count = st.number_input("Pothole count", min_value=0.0, value=4.0, step=1.0)
    length_km = st.number_input("Section length (km)", min_value=0.1, value=1.0, step=0.1)
    traffic_volume = st.number_input("Traffic volume (veh/day)", min_value=0.0, value=10000.0, step=100.0)

    estimated_current_iri = estimate_current_iri(
        crack_rate=crack_rate,
        pothole_count=pothole_count,
        length_km=length_km,
        traffic_volume=traffic_volume,
    )

    st.metric("Estimated Current IRI", f"{estimated_current_iri:.3f}")

    st.divider()
    st.header("Shared Inputs")
    SNPK = st.number_input("SNPK", min_value=0.0, value=3.5, step=0.1)
    YE4 = st.number_input("YE4", min_value=0.0, value=1.2, step=0.1)
    dACR = st.number_input("dACR", min_value=0.0, value=2.0, step=0.1)
    dRDS = st.number_input("dRDS", min_value=0.0, value=1.5, step=0.1)

    V_free = st.number_input("Free-flow speed (km/h)", min_value=5.0, value=80.0, step=1.0)
    distance = st.number_input("Distance (km)", min_value=0.1, value=100.0, step=1.0)
    value_of_time = st.number_input("Value of time", min_value=0.0, value=10.0, step=0.5)
    exposure = st.number_input("Exposure", min_value=0.0, value=10000.0, step=100.0)
    unit_accident_cost = st.number_input("Unit accident cost", min_value=0.0, value=5000.0, step=100.0)

col1, col2 = st.columns(2)

with col1:
    st.subheader("One-Year Simulation")
    AGE3 = st.number_input("Road age (years)", min_value=0.0, value=5.0, step=1.0)

    if st.button("Run one-year simulation", use_container_width=True):
        one_year = simulate_one_year(
            RI=estimated_current_iri,
            SNPK=SNPK,
            YE4=YE4,
            AGE3=AGE3,
            dACR=dACR,
            dRDS=dRDS,
            V_free=V_free,
            distance=distance,
            value_of_time=value_of_time,
            exposure=exposure,
            unit_accident_cost=unit_accident_cost,
        )

        metrics = st.columns(5)
        metrics[0].metric("IRI", f"{one_year['IRI']:.3f}")
        metrics[1].metric("Speed", f"{one_year['Speed']:.2f} km/h")
        metrics[2].metric("VOC", f"{one_year['VOC']:.2f}")
        metrics[3].metric("TravelTimeCost", f"{one_year['TravelTimeCost']:.2f}")
        metrics[4].metric("AccidentCost", f"{one_year['AccidentCost']:.2f}")

        st.json(one_year)

with col2:
    st.subheader("Multi-Year Simulation")
    years = st.number_input("Years", min_value=1, value=15, step=1)
    discount_rate = st.number_input("Discount rate", min_value=0.0, max_value=1.0, value=0.08, step=0.01)

    if st.button("Run multi-year simulation", use_container_width=True):
        rows, npv = run_simulation(
            years=int(years),
            RI0=estimated_current_iri,
            SNPK=SNPK,
            YE4=YE4,
            dACR=dACR,
            dRDS=dRDS,
            V_free=V_free,
            distance=distance,
            value_of_time=value_of_time,
            exposure=exposure,
            unit_accident_cost=unit_accident_cost,
            discount_rate=discount_rate,
        )

        st.metric("Total Discounted Cost (NPV)", f"{npv:,.2f}")

        st.write("Yearly results")
        st.dataframe(rows, use_container_width=True)

        chart_data: List[dict[str, float]] = []
        cumulative_annual_cost = 0.0
        for r in rows:
            cumulative_annual_cost += r["AnnualCost"]
            chart_data.append(
                {
                    "Year": r["Year"],
                    "IRI": r["IRI"],
                    "CumulativeAnnualCost": cumulative_annual_cost,
                }
            )

        st.write("IRI (left axis) and cumulative annual cost (right axis)")
        st.vega_lite_chart(
            chart_data,
            {
                "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                "encoding": {
                    "x": {"field": "Year", "type": "quantitative", "title": "Year"}
                },
                "layer": [
                    {
                        "transform": [{"calculate": "'IRI'", "as": "Series"}],
                        "mark": {"type": "line", "color": "#1f77b4", "strokeWidth": 3},
                        "encoding": {
                            "y": {
                                "field": "IRI",
                                "type": "quantitative",
                                "title": "IRI",
                            },
                            "color": {
                                "field": "Series",
                                "type": "nominal",
                                "title": "Legend",
                                "scale": {
                                    "domain": ["IRI", "Cumulative Annual Cost"],
                                    "range": ["#1f77b4", "#d62728"],
                                },
                            },
                        },
                    },
                    {
                        "transform": [
                            {
                                "calculate": "'Cumulative Annual Cost'",
                                "as": "Series",
                            }
                        ],
                        "mark": {"type": "line", "color": "#d62728", "strokeWidth": 3},
                        "encoding": {
                            "y": {
                                "field": "CumulativeAnnualCost",
                                "type": "quantitative",
                                "title": "Cumulative Annual Cost",
                            },
                            "color": {
                                "field": "Series",
                                "type": "nominal",
                                "title": "Legend",
                                "scale": {
                                    "domain": ["IRI", "Cumulative Annual Cost"],
                                    "range": ["#1f77b4", "#d62728"],
                                },
                            },
                        },
                    },
                ],
                "resolve": {"scale": {"y": "independent"}},
            },
            use_container_width=True,
        )

st.divider()
st.caption("Run with: streamlit run riindex_streamlit.py")
