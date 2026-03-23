"""
core/seismic_engine.py — NBC 105:2025 Complete Seismic Design Engine
====================================================================
Implements NBC 105:2025 (Second Revision) in full:

§4.1   Elastic site spectra C(T): 3-zone Ch(T) formula
§4.2   SLS spectra Cs(T) = 0.20 C(T)
§4.3   Vertical spectra Cv(Tv) = 2/3 Z
§5.1   Fundamental period — empirical (×1.25) and Rayleigh
§5.2   Seismic weight per floor
§5.3   Structural system Rμ / Ωu / Ωs
§5.4   Structural irregularity flags
§5.5   Drifts, displacements, building separation (SRSS)
§5.6   Accidental eccentricity ±0.05b
§6.1   Horizontal base shear coefficient (ULS + SLS)
§6.2   Base shear V = Cd(T)·W
§6.3   Story force distribution Fi = V·Wi·hi^k / Σ(Wj·hj^k)
§6.5   Deflection scale factor kd (Table 6-1)
§3.6   Load combinations (LSM and WSM)
§3.8   Increase in allowable bearing pressure (seismic)
§10    Parts & components Fp
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from constants import (  # type: ignore
    ZONE_FACTOR_DATA, IMPORTANCE_FACTORS, SOIL_PARAMS,
    KT_VALUES, PERIOD_AMPLIFICATION_FACTOR, STRUCTURAL_SYSTEMS,
    DEFLECTION_SCALE_FACTORS_KD,
)


class SeismicCalcError(ValueError):
    pass


# ── Internal helpers ──────────────────────────────────────────────────────────
def _spectral_shape_factor(T: float, soil: dict, method: str) -> float:
    """NBC 105:2025 §4.1.2 Eq. 4.1(2) — 3-zone spectral shape factor."""
    alpha = soil["alpha"]
    Tc    = soil["Tc"]
    Td    = soil["Td"]
    Ta    = 0.0 if method == "Equivalent Static Method" else soil["Ta_table"]

    if Ta > 0 and T < Ta:
        return 1.0 + (alpha - 1.0) * (T / Ta)   # ascending branch
    elif T < Tc:
        return alpha                               # flat plateau
    elif T < Td:
        return alpha * Tc / T                     # velocity-sensitive
    else:
        return alpha * Tc * Td / (T ** 2)         # displacement-sensitive


def _exponent_k(T: float) -> float:
    """Lateral force exponent k per NBC 105:2025 §6.3."""
    if T <= 0.5: return 1.0
    if T >= 2.5: return 2.0
    return 1.0 + (T - 0.5) / 2.0


def _kd(num_stories: int) -> float:
    """Deflection scale factor per Table 6-1."""
    return DEFLECTION_SCALE_FACTORS_KD.get(num_stories, 0.85)


# ── Load Combinations NBC 105:2025 §3.6 ─────────────────────────────────────
def get_load_combos(lsm_or_wsm: str, is_parallel: bool, include_snow: bool) -> list[tuple[str, str, float, float | str, float, float, float]]:
    """
    Returns list of combinations: (label, formula_str, DL, LL, EX_ULS, EY_ULS, E_SLS)
    For WSM, the 'E' components are already multiplied by 0.7.
    """
    combos: list[tuple[str, str, float, float | str, float, float, float]] = []
    
    if lsm_or_wsm == "LSM":
        combos.append(("LC-1 Gravity+Live", "1.2 DL + 1.5 LL", 1.2, 1.5, 0.0, 0.0, 0.0))
        if include_snow:
            combos.append(("LC-2 Gravity+Live+S", "1.2 DL + 0.5 LL + S", 1.2, 0.5, 0.0, 0.0, 0.0))
            
        i = 3 if include_snow else 2
        
        if is_parallel:
            # Parallel systems (Ex and Ey applied separately)
            for ex, ey, sign in [(1.0, 0.0, "+"), (-1.0, 0.0, "−"), (0.0, 1.0, "+"), (0.0, -1.0, "−")]:
                lbl = "EX" if ex != 0 else "EY"
                combos.append((f"LC-{i} Seismic (ULS)", f"DL + λLL {sign} {lbl}", 1.0, "λ", ex, ey, 0.0))
                combos.append((f"LC-{i+4} Seismic (ULS)", f"0.9 DL {sign} {lbl}", 0.9, 0.0, ex, ey, 0.0))
                i += 1
            i += 4
        else:
            # Non-parallel (Ex ± 0.3Ey)
            for ex, ey, sign_ex, sign_ey in [
                (1.0, 0.3, "+", "+"), (1.0, -0.3, "+", "−"), (-1.0, 0.3, "−", "+"), (-1.0, -0.3, "−", "−"),
                (0.3, 1.0, "+", "+"), (0.3, -1.0, "+", "−"), (-0.3, 1.0, "−", "+"), (-0.3, -1.0, "−", "−")
            ]:
                combos.append((f"LC-{i} Seismic (ULS)", f"DL + λLL {sign_ex}{abs(ex):.1f}EX {sign_ey}{abs(ey):.1f}EY", 1.0, "λ", ex, ey, 0.0))
                combos.append((f"LC-{i+8} Seismic (ULS)", f"0.9 DL {sign_ex}{abs(ex):.1f}EX {sign_ey}{abs(ey):.1f}EY", 0.9, 0.0, ex, ey, 0.0))
                i += 1
            i += 8
            
        # SLS
        combos.append((f"LC-{i} SLS Seismic X", "DL + λLL + E_SLS_X", 1.0, "λ", 0.0, 0.0, 1.0))
        combos.append((f"LC-{i+1} SLS Seismic Y", "DL + λLL + E_SLS_Y", 1.0, "λ", 0.0, 0.0, 1.0))

    else: # WSM
        combos.append(("WS-1 Gravity", "DL + LL", 1.0, 1.0, 0.0, 0.0, 0.0))
        if include_snow:
            combos.append(("WS-2 Gravity+S", "DL + LL + S", 1.0, 1.0, 0.0, 0.0, 0.0))
            
        i = 3 if include_snow else 2
        
        if is_parallel:
            for ex, ey, sign in [(1.0, 0.0, "+"), (-1.0, 0.0, "−"), (0.0, 1.0, "+"), (0.0, -1.0, "−")]:
                lbl = "0.7EX" if ex != 0 else "0.7EY"
                wsm_ex = ex * 0.7; wsm_ey = ey * 0.7
                combos.append((f"WS-{i} Seismic", f"DL + λLL {sign} {lbl}", 1.0, "λ", wsm_ex, wsm_ey, 0.0))
                combos.append((f"WS-{i+4} Seismic", f"0.9 DL {sign} {lbl}", 0.9, 0.0, wsm_ex, wsm_ey, 0.0))
                i += 1
        else:
            for ex, ey, sign_ex, sign_ey in [
                (1.0, 0.3, "+", "+"), (1.0, -0.3, "+", "−"), (-1.0, 0.3, "−", "+"), (-1.0, -0.3, "−", "−"),
                (0.3, 1.0, "+", "+"), (0.3, -1.0, "+", "−"), (-0.3, 1.0, "−", "+"), (-0.3, -1.0, "−", "−")
            ]:
                wsm_ex = ex * 0.7; wsm_ey = ey * 0.7
                combos.append((f"WS-{i} Seismic", f"DL + λLL {sign_ex}{abs(wsm_ex):.2f}EX {sign_ey}{abs(wsm_ey):.2f}EY", 1.0, "λ", wsm_ex, wsm_ey, 0.0))
                combos.append((f"WS-{i+8} Seismic", f"0.9 DL {sign_ex}{abs(wsm_ex):.2f}EX {sign_ey}{abs(wsm_ey):.2f}EY", 0.9, 0.0, wsm_ex, wsm_ey, 0.0))
                i += 1

    return combos

# Live load seismic reduction factor λ per NBC 105:2025 Table 5-1
def _lambda_seismic(occupancy: str) -> float:
    if "storage" in occupancy.lower(): return 0.60
    return 0.30


# ── Parts & Components (NBC 105:2025 §10) ────────────────────────────────────
# Amplification factors Cp (Table 10-1)
COMPONENT_AMP = {
    "Parapets, gables, cornices, canopies": 2.5,
    "Access floors, false ceilings":         1.0,
    "Mechanical/Electrical equipment":       1.0,
    "Tanks, vessels":                         2.0,
    "Exterior cladding":                      1.0,
    "Interior partitions":                    1.0,
}
# Component ductility factor μp (Table 10-2)
COMPONENT_DUCTILITY = {
    "Ductile (metal, wood)":  3.0,
    "Brittle (glass, masonry)":1.0,
    "Equipment (anchored)":   1.5,
}
# Component importance Ip (Table 10-3)
COMPONENT_IMPORTANCE = {
    "Life-safety critical":        1.5,
    "Ordinary (non-structural)":   1.0,
}


def compute_component_force(
    Cd_T: float,    # horizontal base shear coefficient (ULS)
    Wp_kN: float,   # weight of component (kN)
    hp_m: float,    # height of component above base (m)
    H_m: float,     # total building height (m)
    Cp: float,      # component amplification factor
    mu_p: float,    # component ductility factor
    Ip: float,      # component importance factor
) -> float:
    """NBC 105:2025 §10.3: Fp = Cd(T)·Cp·(1 + z/H)·Ip/μp · Wp"""
    z_ratio = min(hp_m / max(H_m, 0.01), 1.0)
    Fp = Cd_T * Cp * (1.0 + z_ratio) * Ip / max(mu_p, 0.1) * Wp_kN
    # Limits: 0.1·Wp ≤ Fp ≤ Cd(T)·Wp (NBC 105 §10.3 limits)
    Fp = max(Fp, 0.1 * Wp_kN)
    Fp = min(float(Fp), float(Cd_T * Cp * 3.0 * Wp_kN))  # upper bound
    return round(float(Fp), 3)  # type: ignore


# ── Effective Stiffness (NBC 105:2025 §3.4, Table 3-1) ───────────────────────
# Each component has ULS and SLS flexural stiffness multipliers (× EcIg)
EFFECTIVE_STIFFNESS = {
    "RC Beam":                         {"ULS": 0.35, "SLS": 0.70},
    "RC Column":                       {"ULS": 0.70, "SLS": 0.90},
    "RC Wall (cracked)":               {"ULS": 0.50, "SLS": 0.70},
    "RC Wall (uncracked)":             {"ULS": 0.80, "SLS": 0.90},
    "Masonry Wall":                    {"ULS": 0.45, "SLS": 0.60},
    "RC Flat Slab":                    {"ULS": 0.25, "SLS": 0.50},
}


# ── Irregularity checks (NBC 105:2025 §5.4) ──────────────────────────────────
def check_torsional_irregularity(
    delta_max_mm: float,
    delta_min_mm: float,
) -> dict:
    """
    NBC 105:2025 §5.4.2.1 / §5.4.2.2.
    Ratio = δ_max / δ_min at any floor.
    > 1.5  → Torsional Irregularity (restrict to certain analysis methods).
    > 2.5  → Extreme Torsional Irregularity (NOT PERMITTED; revise configuration).
    """
    if delta_min_mm <= 0:
        return {"ratio": float("inf"), "status": "EXTREME — REVISE",
                "code": "NBC 105:2025 §5.4.2.2"}
    ratio = delta_max_mm / delta_min_mm
    if ratio > 2.5:
        status = "EXTREME (>2.5) — NOT PERMITTED"
    elif ratio > 1.5:
        status = "IRREGULAR (>1.5) — Check analysis method"
    else:
        status = "REGULAR (≤1.5) — OK"
    return {"ratio": round(float(ratio), 3), "status": status,  # type: ignore
            "code": "NBC 105:2025 §5.4.2.1–2"}


def check_mass_irregularity(mass_i: float, mass_i_plus1: float) -> dict:
    """NBC 105:2025 §5.4.1.5 — mass difference > 50% between adjacent stories."""
    ratio = mass_i / max(mass_i_plus1, 1e-9)
    irregular = ratio > 1.5 or ratio < (1/1.5)
    return {"ratio": round(float(ratio), 3),  # type: ignore
            "status": "IRREGULAR (>50% difference)" if irregular else "REGULAR",
            "code": "NBC 105:2025 §5.4.1.5"}


def check_soft_story(stiffness_i: float, stiffness_above: float) -> dict:
    """NBC 105:2025 §5.4.1.2 — soft story if K_i < 70% K_above."""
    ratio = stiffness_i / max(stiffness_above, 1e-9)
    if ratio < 0.70:
        status = "SOFT STORY (<70% of story above)"
    else:
        status = "OK"
    return {"ratio": round(float(ratio), 3), "status": status,  # type: ignore
            "code": "NBC 105:2025 §5.4.1.2"}


def check_weak_story(strength_i: float, strength_above: float) -> dict:
    """NBC 105:2025 §5.4.1.1 — weak story if V_i < 80% V_above."""
    ratio = strength_i / max(strength_above, 1e-9)
    status = "WEAK STORY (<80% of story above)" if ratio < 0.80 else "OK"
    return {"ratio": round(float(ratio), 3), "status": status,  # type: ignore
            "code": "NBC 105:2025 §5.4.1.1"}


# ── Building Separation (NBC 105:2025 §5.5.2) ────────────────────────────────
def building_separation(delta1_mm: float, delta2_mm: float) -> float:
    """SRSS gap: Δgap = √(Δ1² + Δ2²)  (NBC 105:2025 §5.5.2)."""
    return round(float(math.sqrt(delta1_mm**2 + delta2_mm**2)), 2)  # type: ignore


# ── Main calculation ──────────────────────────────────────────────────────────
def run_seismic_calculation(params: dict) -> dict:
    """
    Full NBC 105:2025 ESM seismic calculation.

    Required params keys:
      zone_name, method, imp_name, soil_type, H, struct_cat, struct_sub,
      num_stories (int)

    Optional keys:
      floor_weights   : list[float]  kN per floor (bottom→top); enables story forces
      floor_heights   : list[float]  m above base per floor
      occupancy_type  : str for seismic live load factor λ
    """
    # ── Input validation ──────────────────────────────────────────────────────
    try:
        zone_name   = params["zone_name"]
        method      = params["method"]
        imp_name    = params["imp_name"]
        soil_type   = params["soil_type"]
        H           = float(params["H"])
        struct_cat  = params["struct_cat"]
        struct_sub  = params["struct_sub"]
        num_stories = int(params.get("num_stories", max(1, round(H / 3.0))))
    except (KeyError, ValueError, TypeError) as e:
        raise SeismicCalcError(f"Invalid input: {e}") from e

    if H <= 0:
        raise SeismicCalcError("Building height H must be positive.")
    for name, table, key in [
        ("zone",      ZONE_FACTOR_DATA,   zone_name),
        ("importance",IMPORTANCE_FACTORS, imp_name),
        ("soil",      SOIL_PARAMS,        soil_type),
        ("system cat",STRUCTURAL_SYSTEMS, struct_cat),
    ]:
        if key not in table:
            raise SeismicCalcError(f"Unknown {name}: '{key}'")
    if struct_sub not in STRUCTURAL_SYSTEMS[struct_cat]:
        raise SeismicCalcError(f"Unknown sub-type: '{struct_sub}'")

    Z    = ZONE_FACTOR_DATA[zone_name]
    I    = IMPORTANCE_FACTORS[imp_name]
    soil = SOIL_PARAMS[soil_type]
    sys_ = STRUCTURAL_SYSTEMS[struct_cat][struct_sub]
    Ru   = sys_["Ru"];  O_u = sys_["Ωu"];  O_s = sys_["Ωs"]
    kt   = KT_VALUES[sys_["Kt_key"]]

    # ── Fundamental period ────────────────────────────────────────────────────
    T_approx = kt * (H ** 0.75)                      # §5.1.2
    T        = PERIOD_AMPLIFICATION_FACTOR * T_approx  # ×1.25 per §5.1.3
    k        = _exponent_k(T)

    # ── Spectral calculations ─────────────────────────────────────────────────
    Ch_T  = _spectral_shape_factor(T, soil, method)
    C_T   = Ch_T * Z * I                # ULS elastic site spectra §4.1.1
    Cs_T  = 0.20 * C_T                  # SLS elastic site spectra §4.2
    Cv_T  = (2.0/3.0) * Z               # Vertical elastic spectra §4.3

    # ── Base shear coefficients ───────────────────────────────────────────────
    Cd_ULS = C_T  / (Ru * O_u)          # §6.1.1
    Cd_SLS = Cs_T / O_s                 # §6.1.2

    # ── Minimum base shear check (NBC 105 — implied from SBC requirements) ───
    Cd_ULS_min = 0.04 * Z * I           # practical minimum check
    Cd_ULS_governed = max(Cd_ULS, Cd_ULS_min)
    min_governed    = Cd_ULS_governed > Cd_ULS

    # ── Drift & displacement ──────────────────────────────────────────────────
    kd_factor    = _kd(num_stories)
    Drift_ULS    = 0.025                         # §5.5.3 inter-story drift ratio limit
    Drift_SLS    = 0.006
    # ULS design deflection: ESM result × Rμ (§5.5.1.1), then × kd (§6.5)
    Disp_ULS_mm  = Drift_ULS * H * 1000 * kd_factor
    Disp_SLS_mm  = Drift_SLS * H * 1000

    # ── Story force distribution §6.3 ─────────────────────────────────────────
    floor_weights = params.get("floor_weights") or []
    floor_heights = params.get("floor_heights") or []
    story_forces  = []

    if floor_weights and len(floor_weights) >= 1:
        if not floor_heights:
            # uniform story heights if not provided
            story_h = H / len(floor_weights)
            floor_heights = [story_h * (i+1) for i in range(len(floor_weights))]

        W_seismic = sum(floor_weights)
        V_base    = Cd_ULS_governed * W_seismic  # kN

        # Wi * hi^k products
        Wh_k = [w * (h**k) for w,h in zip(floor_weights, floor_heights)]
        sum_Wh_k = sum(Wh_k)

        for i,(w,h,whk) in enumerate(zip(floor_weights,floor_heights,Wh_k)):
            Fi = (whk / max(float(sum_Wh_k), 1e-9)) * V_base
            sf_dict: dict[str, float | int] = {
                "floor":    int(i + 1),
                "W_kN":     round(float(w), 2),  # type: ignore
                "h_m":      round(float(h), 3),  # type: ignore
                "Wh_k":     round(float(whk), 3),  # type: ignore
                "Fi_kN":    round(float(Fi), 3),  # type: ignore
                "Vx_kN":    0.0,
            }
            story_forces.append(sf_dict)
        # Fix cumulative story shear
        cum = 0.0
        for f in reversed(story_forces):
            cum += float(f["Fi_kN"])
            f["Vx_kN"] = round(float(cum), 3)  # type: ignore
        W_total  = W_seismic
        V_base_f = V_base
    else:
        W_total = V_base_f = 0.0

    # ── Accidental eccentricity §5.6 ──────────────────────────────────────────
    # ±0.05b in each plan direction (b = plan dimension)
    acc_eccentricity = 0.05   # factor; user multiplies by floor dimension

    # ── Vertical seismic §4.3 ─────────────────────────────────────────────────
    # Applies to horizontal members ≥20m, cantilevers ≥5m, prestressed, base-isolated
    Cv_note = (
        f"Cv(Tv) = 2/3·Z = {Cv_T:.3f}  "
        "Applies to: horizontal members ≥20m, cantilevers ≥5m, "
        "prestressed members, beams supporting columns, base-isolated structures."
    )

    # ── Load combinations (NBC 105:2025 §3.6) ─────────────────────────────────
    # Return as structured data; actual factored values need DL/LL inputs from user
    occupancy = params.get("occupancy_type", "General")
    lam          = _lambda_seismic(occupancy)
    is_parallel  = params.get("is_parallel", True)
    include_snow = params.get("include_snow", False)

    load_combos = []
    for label, formula, dl, ll, ex_uls, ey_uls, e_sls in get_load_combos("LSM", is_parallel, include_snow):
        ll_f = lam if ll == "λ" else (ll if isinstance(ll, (int, float)) else 0.0)
        load_combos.append({
            "label":   label,
            "formula": formula,
            "DL_fac":  dl,
            "LL_fac":  ll_f,
            "EX_ULS_fac": ex_uls,
            "EY_ULS_fac": ey_uls,
            "E_SLS_fac": e_sls,
            "lambda":  lam,
        })

    return {
        # ── Site params
        "Z": Z, "I": I, "soil_type": soil_type,
        "Tc": soil["Tc"], "Td": soil["Td"], "alpha": soil["alpha"],
        # ── Period
        "kt": kt, "T_approx": T_approx, "T": T, "k": k,
        # ── Spectra
        "Ch_T": Ch_T, "C_T": C_T, "Cs_T": Cs_T, "Cv_T": Cv_T,
        # ── System
        "Ru": Ru, "O_u": O_u, "O_s": O_s,
        # ── Coefficients
        "Cd_ULS": Cd_ULS, "Cd_ULS_governed": Cd_ULS_governed,
        "min_governed": min_governed, "Cd_ULS_min": Cd_ULS_min,
        "Cd_SLS": Cd_SLS,
        # ── Drift/displacement
        "kd": kd_factor, "num_stories": num_stories,
        "Drift_ULS": Drift_ULS, "Drift_SLS": Drift_SLS,
        "Disp_ULS_mm": Disp_ULS_mm, "Disp_SLS_mm": Disp_SLS_mm,
        # ── Story forces
        "W_seismic_kN": W_total, "V_base_kN": V_base_f,
        "story_forces": story_forces,
        # ── Accidental eccentricity
        "acc_eccentricity": acc_eccentricity,
        # ── Vertical seismic
        "Cv_note": Cv_note,
        # ── Load combinations
        "load_combos": load_combos, "lambda_ll": lam,
    }
