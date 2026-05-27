"""Simplified HDM-style road roughness and road-user-cost simulation.

This module models annual IRI progression and estimates road user effects:
- Vehicle operating cost (VOC)
- Travel time cost
- Accident cost
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple


def estimate_current_iri(
    crack_rate: float,
    pothole_count: float,
    length_km: float,
    traffic_volume: float,
) -> float:
    """Estimate current IRI from observed distress and traffic inputs.

    This is a transparent surrogate model for the current app. The coefficients
    are intentionally simple so they can be calibrated later with local data.
    """
    if length_km <= 0:
        raise ValueError("length_km must be positive")

    pothole_density = pothole_count / length_km
    length_term = 0.08 * math.log1p(length_km)

    iri = (
        1.8
        + 0.035 * crack_rate
        + 0.45 * pothole_density
        + 0.00005 * traffic_volume
        + length_term
    )
    return max(iri, 0.0)


def roughness_increment(
    RI_a: float,
    SNPK: float,
    YE4: float,
    AGE3: float,
    dACR: float,
    dRDS: float,
    Kgs: float = 1.0,
    Kgc: float = 1.0,
    Kgr: float = 1.0,
    Kgm: float = 1.0,
    m: float = 0.02,
) -> float:
    """Compute annual roughness increment dIRI."""
    dRI_s = Kgs * 134 * math.exp(Kgm * m * AGE3) * (1 + SNPK) ** (-5) * YE4
    dRI_c = Kgc * 0.0066 * dACR
    dRI_r = Kgr * 0.088 * dRDS
    dRI_e = Kgm * m * RI_a
    return dRI_s + dRI_c + dRI_r + dRI_e


def update_iri(RI_a: float, dRI: float) -> float:
    return RI_a + dRI


def speed_from_roughness(V_free: float, IRI: float, beta: float = 0.06) -> float:
    """Estimate speed from roughness and clamp to a realistic floor."""
    return max(V_free * math.exp(-beta * IRI), 5.0)


def compute_voc(IRI: float, speed: float) -> float:
    """Simplified VOC function based on IRI and speed."""
    if speed <= 0:
        raise ValueError("speed must be positive")
    return 0.2 + 0.05 * IRI + 0.01 * speed + 1.5 / speed


def travel_time_cost(distance_km: float, speed_kmh: float, value_of_time: float) -> float:
    if speed_kmh <= 0:
        raise ValueError("speed_kmh must be positive")
    time_hours = distance_km / speed_kmh
    return time_hours * value_of_time


def accident_cost(IRI: float, exposure: float, unit_cost: float) -> float:
    """Lookup-style accident cost where rate increases with IRI."""
    accident_rate = 0.1 + 0.05 * IRI
    return accident_rate * exposure * unit_cost


def simulate_one_year(
    RI: float,
    SNPK: float,
    YE4: float,
    AGE3: float,
    dACR: float,
    dRDS: float,
    V_free: float,
    distance: float,
    value_of_time: float,
    exposure: float,
    unit_accident_cost: float,
) -> Dict[str, float]:
    """Run one-year progression and cost calculation."""
    dRI = roughness_increment(RI, SNPK, YE4, AGE3, dACR, dRDS)
    RI_new = update_iri(RI, dRI)
    speed = speed_from_roughness(V_free, RI_new)
    voc = compute_voc(RI_new, speed)
    ttc = travel_time_cost(distance, speed, value_of_time)
    acc = accident_cost(RI_new, exposure, unit_accident_cost)

    return {
        "IRI": RI_new,
        "Speed": speed,
        "VOC": voc,
        "TravelTimeCost": ttc,
        "AccidentCost": acc,
    }


def run_simulation(
    years: int = 10,
    RI0: float = 3.0,
    SNPK: float = 3.5,
    YE4: float = 1.2,
    dACR: float = 2.0,
    dRDS: float = 1.5,
    V_free: float = 80.0,
    distance: float = 100.0,
    value_of_time: float = 10.0,
    exposure: float = 10000.0,
    unit_accident_cost: float = 5000.0,
    discount_rate: float = 0.08,
) -> Tuple[List[Dict[str, float]], float]:
    """Run multi-year simulation and return yearly rows plus total discounted cost."""
    if years <= 0:
        raise ValueError("years must be >= 1")

    results: List[Dict[str, float]] = []
    RI = RI0
    total_cost_npv = 0.0

    for year in range(1, years + 1):
        AGE3 = year
        dRI = roughness_increment(RI, SNPK, YE4, AGE3, dACR, dRDS)
        RI = update_iri(RI, dRI)

        speed = speed_from_roughness(V_free, RI)
        voc = compute_voc(RI, speed)
        ttc = travel_time_cost(distance, speed, value_of_time)
        acc = accident_cost(RI, exposure, unit_accident_cost)

        annual_cost = voc + ttc + acc
        discount_factor = 1 / ((1 + discount_rate) ** year)
        discounted_cost = annual_cost * discount_factor
        total_cost_npv += discounted_cost

        results.append(
            {
                "Year": float(year),
                "IRI": RI,
                "Speed": speed,
                "VOC": voc,
                "TravelTimeCost": ttc,
                "AccidentCost": acc,
                "AnnualCost": annual_cost,
                "DiscountedCost": discounted_cost,
            }
        )

    return results, total_cost_npv


if __name__ == "__main__":
    one_year = simulate_one_year(
        RI=3.0,
        SNPK=3.5,
        YE4=1.2,
        AGE3=5,
        dACR=2.0,
        dRDS=1.5,
        V_free=80.0,
        distance=100.0,
        value_of_time=10.0,
        exposure=10000.0,
        unit_accident_cost=5000.0,
    )
    print("One-year result:", one_year)

    rows, npv = run_simulation(years=15)
    print("Total NPV Cost =", npv)
    print("Last year row =", rows[-1])