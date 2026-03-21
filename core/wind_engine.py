"""
core/wind_engine.py — IS 875 Part 3:2015 Wind Load Calculation
==============================================================
Covers:
  §6.2  Design wind speed Vz = Vb × k1 × k2 × k3 × k4
  §6.3  Design wind pressure pz = 0.6 × Vz²  (N/m²)
  §6.3  Design wind pressure pd = pz × Kd × Ka × Kc
  §7    Wind loads on buildings (external pressure coefficients)
  §6.4  Wind pressure on cladding/components
  NBC 105:2025 §3.7 WSM: Wind treated as lateral load in combinations

Terrain categories: 1–4 (open sea → urban dense)
Topography factor k3 for hills/cliffs
"""
from __future__ import annotations
import math


# ── Basic wind speed by location (India + Nepal border zones) ─────────────────
# IS 875 Part 3 Fig. 1 representative values (m/s)
BASIC_WIND_SPEED: dict[str, float] = {
    # Nepal — consult local hazard maps; these are indicative
    "Kathmandu":     47.0,
    "Pokhara":       44.0,
    "Biratnagar":    50.0,
    "Butwal":        47.0,
    "Hetauda":       47.0,
    "Dharan":        47.0,
    "Generic Nepal": 47.0,
    # India zones for reference
    "Coastal (India)": 55.0,
    "Delhi":           47.0,
    "Mumbai":          44.0,
}

# ── k1 (Risk coefficient / return period) IS 875 Pt 3 Table 1 ─────────────────
K1_FACTORS: dict[str, float] = {
    "General buildings (50 yr)":          1.00,
    "Important buildings (100 yr)":        1.07,
    "Critical structures (200 yr)":        1.14,
    "Temporary structures (<5 yr)":        0.82,
    "Temporary structures (5–25 yr)":      0.94,
}

# ── k2 (Height + terrain) IS 875 Pt 3 Table 2 ─────────────────────────────────
# k2 at 10m for terrain categories 1–4
K2_AT_10M = {1: 1.05, 2: 1.00, 3: 0.91, 4: 0.80}

# Power law exponent α for k2 = k2_10m × (z/10)^α
K2_ALPHA   = {1: 0.10, 2: 0.133, 3: 0.187, 4: 0.25}

# ── k3 (Topography factor) IS 875 Pt 3 §6.3.3 ───────────────────────────────
# k3 = 1.0 for flat ground; 1.0–1.36 for hills/cliffs
K3_TABLE: dict[str, float] = {
    "Flat or gently sloping (<3°)":     1.00,
    "Upwind slope 3°–17°":             1.07,
    "Upwind slope 17°–27°":            1.12,
    "Cliff / escarpment upwind slope >27°": 1.36,
}

# ── k4 (Importance factor for cyclone) IS 875 Pt 3 §6.3.4 ────────────────────
K4_TABLE: dict[str, float] = {
    "Residences (post-cyclone inhabit)": 1.15,
    "Schools, hospitals (life-safety)":  1.15,
    "Other structures":                  1.00,
}

# ── Kd (Wind directionality) IS 875 Pt 3 §7.3.1 ─────────────────────────────
Kd = 0.90   # 0.90 for most building types

# ── Ka (Area averaging) IS 875 Pt 3 §7.3.2 ───────────────────────────────────
def Ka_factor(area_m2: float) -> float:
    """Area averaging factor from Table 4."""
    if area_m2 <= 10:  return 1.00
    if area_m2 <= 25:  return 1.0 - 0.5*(area_m2-10)/15
    if area_m2 <= 100: return 0.9 - 0.1*(area_m2-25)/75
    return 0.80

# ── Kc (Combination factor) IS 875 Pt 3 §7.3.3 ──────────────────────────────
Kc = 0.90   # for buildings with more than one face exposed

# ── External pressure coefficients Cpe (IS 875 Pt 3 Table 5–6) ──────────────
# For a rectangular building: windward (+ve) and leeward (-ve)
def Cpe_walls(h: float, d: float) -> dict:
    """
    External pressure coefficients for rectangular buildings.
    h = height, d = depth (in wind direction).
    IS 875 Part 3 Table 5.
    """
    hd = h / max(d, 1e-9)
    if hd < 0.25:
        cpe_windward = 0.7; cpe_leeward = -0.5
    elif hd < 1.0:
        cpe_windward = 0.7; cpe_leeward = -0.5
    else:
        cpe_windward = 0.8; cpe_leeward = -0.6 if hd >= 1.5 else -0.5
    return {
        "windward":  cpe_windward,
        "leeward":   cpe_leeward,
        "side_left": -0.6,
        "side_right":-0.6,
        "h_d_ratio": round(hd, 3),
    }

def Cpe_roof_flat(h: float, d: float) -> dict:
    """IS 875 Pt 3 Table 6 — flat/low-pitch roof."""
    return {
        "h < d": (-0.8 if h < d else -1.0),
        "eaves": -1.2,
        "ridge": -0.4,
    }


def calculate_wind_loads(
    location:      str   = "Generic Nepal",
    Vb:            float | None = None,   # override basic wind speed (m/s)
    H_m:           float = 10.0,          # building height (m)
    B_m:           float = 10.0,          # building width ⊥ wind (m)
    D_m:           float = 10.0,          # building depth ∥ wind (m)
    terrain_cat:   int   = 2,
    k1_label:      str   = "General buildings (50 yr)",
    k3_label:      str   = "Flat or gently sloping (<3°)",
    k4_label:      str   = "Other structures",
    floor_heights: list[float] | None = None,  # list of storey heights (m) for story forces
) -> dict:
    """
    Compute design wind pressure and base shear per IS 875 Part 3:2015.
    """
    notes: list[str] = []

    # ── Basic wind speed ──────────────────────────────────────────────────────
    if Vb is None:
        Vb = BASIC_WIND_SPEED.get(location, 47.0)
    notes.append(
        f"Basic wind speed Vb = {Vb:.0f} m/s for '{location}' "
        f"(IS 875 Pt 3 §5.2 / Figure 1)."
    )

    k1 = K1_FACTORS.get(k1_label, 1.00)
    k2_10 = K2_AT_10M.get(terrain_cat, 1.00)
    alpha = K2_ALPHA.get(terrain_cat, 0.133)
    k2    = k2_10 * (H_m / 10.0) ** alpha if H_m > 10 else k2_10 * (10.0 / 10.0) ** alpha
    k3    = K3_TABLE.get(k3_label, 1.00)
    k4    = K4_TABLE.get(k4_label, 1.00)

    Vz = Vb * k1 * k2 * k3 * k4
    pz = 0.6 * Vz**2 / 1000   # kN/m² (converting N/m² → kN/m²)

    Ka = Ka_factor(B_m * H_m)  # wind face area
    pd = pz * Kd * Ka * Kc     # design wind pressure (kN/m²)

    notes.append(
        f"k1={k1:.2f}, k2={k2:.3f} (terrain {terrain_cat}, H={H_m}m), "
        f"k3={k3:.2f}, k4={k4:.2f}."
    )
    notes.append(
        f"Design wind speed Vz = Vb·k1·k2·k3·k4 = {Vz:.2f} m/s."
    )
    notes.append(
        f"Design wind pressure pz = 0.6·Vz² = {pz:.3f} kN/m².  "
        f"pd = pz·Kd·Ka·Kc = {pd:.3f} kN/m²  "
        f"(Kd={Kd}, Ka={Ka:.2f}, Kc={Kc})."
    )

    # ── Pressure coefficients & net pressure ──────────────────────────────────
    cpe = Cpe_walls(H_m, D_m)
    p_windward = (cpe["windward"] - cpe["leeward"]) * pd   # net cross-wind
    p_lateral  = cpe["windward"] * pd                       # windward face only
    notes.append(
        f"Wall Cpe: windward={cpe['windward']}, leeward={cpe['leeward']} "
        f"(h/d={cpe['h_d_ratio']:.2f}, IS 875 Pt 3 Table 5). "
        f"Net wall pressure = {p_windward:.3f} kN/m²."
    )

    # ── Base shear (simple tributary) ─────────────────────────────────────────
    V_wind_kN = pd * (cpe["windward"] - cpe["leeward"]) * B_m * H_m / 2
    # Factor of 0.5 since tributary approach for symmetric building

    # ── Story forces (if heights given) ───────────────────────────────────────
    story_forces = []
    if floor_heights:
        # Pressure at each storey height; triangular distribution
        story_h_avg = [
            (floor_heights[i] + (floor_heights[i-1] if i>0 else 0)) / 2
            for i in range(len(floor_heights))
        ]
        k2_i_list = [k2_10 * (h/10)**alpha if h>10 else k2_10 for h in story_h_avg]
        pz_i_list = [0.6 * (Vb*k1*k2i*k3*k4)**2 / 1000 for k2i in k2_i_list]
        h_diffs   = [floor_heights[0]] + [floor_heights[i]-floor_heights[i-1]
                                           for i in range(1,len(floor_heights))]
        for i,(h,pz_i,dh) in enumerate(zip(floor_heights,pz_i_list,h_diffs)):
            Fi = pz_i * (cpe["windward"]-cpe["leeward"]) * B_m * dh * Kd * Ka * Kc
            story_forces.append({
                "floor":  i+1,
                "h_m":    round(h, 2),
                "pz_kPa": round(pz_i, 3),
                "Fi_kN":  round(Fi, 2),
            })
        V_wind_kN = sum(f["Fi_kN"] for f in story_forces)

    return {
        "location": location,
        "Vb_ms":    Vb,
        "k1": k1, "k2": round(k2,3), "k3": k3, "k4": k4,
        "Vz_ms":    round(Vz, 2),
        "pz_kPa":   round(pz, 4),
        "pd_kPa":   round(pd, 4),
        "Kd": Kd, "Ka": round(Ka,3), "Kc": Kc,
        "Cpe_windward":  cpe["windward"],
        "Cpe_leeward":   cpe["leeward"],
        "Cpe_side":      cpe["side_left"],
        "h_d_ratio":     cpe["h_d_ratio"],
        "p_net_kPa":     round(p_windward, 4),
        "V_wind_kN":     round(V_wind_kN, 2),
        "story_forces":  story_forces,
        "notes": notes,
    }
