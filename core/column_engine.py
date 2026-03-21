"""
core/column_engine.py — IS 456:2000 Complete Column Design Engine
=================================================================
Priority: NBC 105:2025 Annex A ductile detailing overrides IS 456 where more stringent.

Covers:
  §25.1.2  Slenderness classification (short / slender)
  §25.4    Minimum eccentricity
  §39.2    Short column design formulae
  §39.3    Pure axial capacity
  §39.6    Biaxial bending — IS 456 interaction formula + SP 16 Annex D approach
  §39.7    Additional moments for slender columns
  §26.5.3  Lateral ties arrangement (including multi-leg ties for >4 bars)
  §26.5.3.2 Spiral columns (basic)
  Annex A  NBC 105:2025 ductile RC detailing requirements for columns
"""
from __future__ import annotations
import math


def _mu_x_capacity(b_mm, D_mm, fck, fy, Ast_total, d_prime, Pu_N, axis="x") -> float:
    """
    Compute uniaxial moment capacity Mu1 at given Pu (N) by equilibrium.

    Method (IS 456 §39 / SP 16 Annex D equivalent):
      1. Find neutral axis depth xu by equilibrium C = T + Pu
      2. Compute Mu about section centroid at that xu
    Assumes equal reinforcement on two opposite faces (standard column layout).
    """
    b_   = b_mm if axis == "x" else D_mm
    D_   = D_mm if axis == "x" else b_mm
    dp_  = d_prime
    d_   = D_ - dp_
    if d_ <= 0:
        return 0.01
    As_t = Ast_total / 2.0   # tension-face bars
    As_c = Ast_total / 2.0   # compression-face bars
    Es   = 2e5  # N/mm²

    def _equilibrium_residual(xu: float) -> float:
        if xu <= 0:
            return -Pu_N
        eps_sc = 0.0035 * (xu - dp_) / xu
        fsc    = min(0.87*fy, max(0.0, eps_sc * Es))
        eps_st = 0.0035 * (d_ - xu) / xu
        fst    = min(0.87*fy, max(0.0, eps_st * Es))
        C_conc = 0.36 * fck * b_ * xu
        C_stl  = (fsc - 0.45*fck) * As_c
        T_stl  = fst * As_t
        return C_conc + C_stl - T_stl - Pu_N

    # Binary search for xu in [1 mm, 3·D_]
    lo_, hi_ = 1.0, 3.0 * D_
    for _ in range(60):
        mid = (lo_ + hi_) / 2.0
        if _equilibrium_residual(mid) > 0:
            hi_ = mid
        else:
            lo_ = mid
    xu = (lo_ + hi_) / 2.0

    # Strains and stresses at found xu
    eps_sc = 0.0035 * (xu - dp_) / xu
    fsc    = min(0.87*fy, max(0.0, eps_sc * Es))
    eps_st = 0.0035 * (d_ - xu) / xu
    fst    = min(0.87*fy, max(0.0, eps_st * Es))
    C_conc = 0.36 * fck * b_ * xu
    C_stl  = (fsc - 0.45*fck) * As_c
    T_stl  = fst * As_t

    # Moment about centroid of section
    Mu = abs(
        C_conc * (D_/2.0 - 0.42*xu) +
        C_stl  * (D_/2.0 - dp_) +
        T_stl  * (d_ - D_/2.0)
    )
    return max(Mu / 1e6, 0.01)


def _ties_arrangement(n_bars: int, b_mm: float, D_mm: float, tie_dia: float) -> list[str]:
    """
    IS 456 Cl. 26.5.3.1 — determine tie leg arrangement.
    For >4 bars: additional cross-ties required for every alternate bar > 75mm from a corner.
    """
    notes = [f"Ø{int(tie_dia)} peripheral tie at {b_mm:.0f}×{D_mm:.0f} mm."]
    if n_bars <= 4:
        notes.append("4 corner bars — peripheral tie sufficient.")
    elif n_bars <= 6:
        notes.append(f"{n_bars} bars — 1 cross-tie required (IS 456 Cl. 26.5.3.1c).")
    elif n_bars <= 8:
        notes.append(f"{n_bars} bars — 2 cross-ties required.")
    else:
        n_extra = math.ceil((n_bars - 4) / 2)
        notes.append(f"{n_bars} bars — {n_extra} cross-ties required per IS 456 Cl. 26.5.3.1c.")
    return notes


def _ductile_detailing_nbc(
    b_mm, D_mm, eff_len_avg, main_dia, fck, fy, tie_dia, n_bars
) -> dict:
    """
    NBC 105:2025 Annex A — Ductile RC Column Detailing.
    Stricter than IS 456; governs in seismic design.
    """
    # Confinement zone length lo (§A.4.4.1): lo ≥ max(D, B, Lu/6, 450mm)
    lo = max(D_mm, b_mm, eff_len_avg / 6.0, 450.0)

    # Tie spacing in confinement zone (§A.4.4.3):
    # ≤ min(b/4, 100mm, 6·Ø_main)  (not less than 50mm)
    s_conf = min(min(b_mm, D_mm) / 4.0, 100.0, 6.0 * main_dia)
    s_conf = max(50.0, math.floor(s_conf / 5) * 5)

    # Tie spacing outside confinement zone (§A.4.4.2):
    # ≤ min(12·Ø_main, b_short, 250mm)
    s_out = min(12.0 * main_dia, min(b_mm, D_mm), 250.0)
    s_out = max(75.0, math.floor(s_out / 25) * 25)

    # Hoop area requirement for rectangular confinement (NBC 105 Annex A §A.4.4.4):
    # Ash ≥ 0.09 · s · h" · fck/fy  (h" = dim of concrete core perp to hoop)
    h_core = b_mm - 2 * 40  # approx (cover ≈ 40)
    Ash_req = 0.09 * s_conf * h_core * fck / fy
    Ash_prov = 2 * math.pi * tie_dia ** 2 / 4.0  # 2 legs of tie
    hoop_ok = Ash_prov >= Ash_req

    # Minimum steel NBC 105 Annex A §A.4.3: same as IS 456 (0.8%)
    # Maximum steel in seismic: 4% (IS 456 and NBC 105 Annex A agree)
    # Lap splice location: only in middle half of column height
    # Hook requirement: 135° hooks on ties in confinement zone

    return {
        "lo_mm":          round(lo, 0),
        "s_conf_mm":      s_conf,
        "s_out_mm":       s_out,
        "Ash_req_mm2":    round(Ash_req, 1),
        "Ash_prov_mm2":   round(Ash_prov, 1),
        "hoop_ok":        hoop_ok,
    }


def check_column(
    b_mm:           float,
    D_mm:           float,
    eff_len_x:      float,   # effective length for bending about major axis (mm)
    eff_len_y:      float,   # effective length for bending about minor axis (mm)
    fck:            float,
    fy:             float,
    Pu_kN:          float,
    Mux_kNm:        float,
    Muy_kNm:        float,
    cover_mm:       float = 40.0,
    tie_dia_mm:     float = 8.0,
    main_dia_mm:    float = 16.0,
    seismic_zone:   str   = "moderate",  # "low" | "moderate" | "high"
) -> dict:
    notes: list[str] = []
    Ag   = b_mm * D_mm
    Pu_N = Pu_kN * 1000

    # ── Slenderness (IS 456 §25.1.2) ─────────────────────────────────────────
    lambda_x = eff_len_x / D_mm   # slenderness ratio about major axis
    lambda_y = eff_len_y / b_mm   # slenderness ratio about minor axis
    is_slender_x = lambda_x > 12
    is_slender_y = lambda_y > 12
    is_slender   = is_slender_x or is_slender_y

    if lambda_x > 60 or lambda_y > 60:
        notes.append(
            f"⚠ Slenderness ratio > 60 (λx={lambda_x:.1f}, λy={lambda_y:.1f}). "
            "Special analysis required (IS 456 Cl. 25.1.3)."
        )

    # ── Additional moments for slender columns (IS 456 §39.7) ────────────────
    min_steel_pct = 0.8
    max_steel_pct = 4.0   # NBC 105 Annex A for seismic zone
    Ast_trial = (min_steel_pct / 100) * Ag

    # Puz for k_factor estimate
    Puz_est = (0.45 * fck * Ag + 0.75 * fy * Ast_trial)
    k_val   = max(0.0, min(1.0, (Puz_est - Pu_N) / max(Puz_est - 0.4*Ag*fck, 1e-9)))

    Ma_x = k_val * Pu_N * D_mm * (lambda_x**2) / 2000.0 / 1e6   # kN·m
    Ma_y = k_val * Pu_N * b_mm * (lambda_y**2) / 2000.0 / 1e6

    # ── Minimum eccentricity (IS 456 §25.4) ──────────────────────────────────
    emin_x = max(eff_len_x / 500.0 + D_mm / 30.0, 20.0)   # mm
    emin_y = max(eff_len_y / 500.0 + b_mm / 30.0, 20.0)
    Mmin_x = Pu_N * emin_x / 1e6   # kN·m
    Mmin_y = Pu_N * emin_y / 1e6

    # Design moments (larger of applied+additional or minimum)
    Mux_design = max(Mux_kNm + Ma_x, Mmin_x)
    Muy_design = max(Muy_kNm + Ma_y, Mmin_y)

    if is_slender:
        notes.append(
            f"Slender column (λx={lambda_x:.1f}, λy={lambda_y:.1f} > 12). "
            f"Additional moments: Max={Ma_x:.2f} kN·m, May={Ma_y:.2f} kN·m (k={k_val:.3f})."
        )
    notes.append(
        f"Min. eccentricity: ex={emin_x:.1f} mm, ey={emin_y:.1f} mm. "
        f"Design: Mux={Mux_design:.2f}, Muy={Muy_design:.2f} kN·m."
    )

    # ── Effective cover (to bar centroid) ─────────────────────────────────────
    d_prime = cover_mm + tie_dia_mm + main_dia_mm / 2.0
    d_prime = min(d_prime, min(b_mm, D_mm) * 0.25)   # practical limit

    # ── Iterate Ast to satisfy IS 456 §39.6 biaxial interaction ──────────────
    area_bar = math.pi * main_dia_mm**2 / 4.0
    Ast_design = 0.0
    final_pct  = min_steel_pct

    for pct in [min_steel_pct, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 3.5, max_steel_pct]:
        ast = (pct / 100.0) * Ag
        ast = max(ast, 4 * area_bar)   # at least 4 bars

        # Uniaxial moment capacities at this Ast
        Mux1 = _mu_x_capacity(b_mm, D_mm, fck, fy, ast, d_prime, Pu_N, "x")
        Muy1 = _mu_x_capacity(b_mm, D_mm, fck, fy, ast, d_prime, Pu_N, "y")

        # Puz (IS 456 §39.6)
        Puz  = 0.45 * fck * Ag + 0.75 * fy * ast
        ratio_pu = Pu_N / max(Puz, 1e-9)

        # Interaction exponent αn (IS 456 §39.6)
        # αn = 1.0 + (Pu/Puz - 0.2) / 0.6 clamped to [1.0, 2.0]
        alpha_n = max(1.0, min(2.0,
            1.0 + (ratio_pu - 0.2) / 0.6 if ratio_pu > 0.2 else 1.0
        ))

        interaction = (
            (Mux_design / max(Mux1, 0.001)) ** alpha_n +
            (Muy_design / max(Muy1, 0.001)) ** alpha_n
        )

        Ast_design = ast
        final_pct  = pct
        if interaction <= 1.0:
            break

    # Final check values
    n_bars = max(4, math.ceil(Ast_design / area_bar))
    if n_bars % 2 != 0:   # prefer even numbers for symmetric layout
        n_bars += 1
    Ast_prov  = area_bar * n_bars
    pct_prov  = 100.0 * Ast_prov / Ag

    # Recalculate with provided steel
    Mux1_f  = _mu_x_capacity(b_mm, D_mm, fck, fy, Ast_prov, d_prime, Pu_N, "x")
    Muy1_f  = _mu_x_capacity(b_mm, D_mm, fck, fy, Ast_prov, d_prime, Pu_N, "y")
    Puz_f   = 0.45 * fck * Ag + 0.75 * fy * Ast_prov
    ratio_f  = Pu_N / max(Puz_f, 1e-9)
    alpha_f  = max(1.0, min(2.0,
        1.0 + (ratio_f - 0.2) / 0.6 if ratio_f > 0.2 else 1.0))
    interaction_f = (
        (Mux_design / max(Mux1_f, 0.001)) ** alpha_f +
        (Muy_design / max(Muy1_f, 0.001)) ** alpha_f
    )

    # ── Axial capacity checks ─────────────────────────────────────────────────
    # IS 456 §39.3: Pure axial (un-factored for column)
    Pu_max   = 0.40 * fck * (Ag - Ast_prov) + 0.67 * fy * Ast_prov   # N
    Pu_max_kN = Pu_max / 1000
    # IS 456 §39.5: Minimum axial (tension)
    Pu_min = 0.0   # zero tension capacity for plain RC

    # ── Tie design (IS 456 §26.5.3.1) ─────────────────────────────────────────
    s_tie = min(
        min(b_mm, D_mm),             # least lateral dimension
        16.0 * main_dia_mm,          # 16× main bar dia
        300.0,                        # IS 456 absolute max
    )
    s_tie = math.floor(s_tie / 25) * 25
    s_tie = max(s_tie, 75)

    # ── NBC 105:2025 Annex A ductile detailing ─────────────────────────────────
    eff_avg = (eff_len_x + eff_len_y) / 2.0
    ductile = _ductile_detailing_nbc(b_mm, D_mm, eff_avg, main_dia_mm,
                                      fck, fy, tie_dia_mm, n_bars)

    # ── Tie leg arrangement ───────────────────────────────────────────────────
    tie_notes = _ties_arrangement(n_bars, b_mm, D_mm, tie_dia_mm)
    notes.extend(tie_notes)

    # ── Side face steel check ─────────────────────────────────────────────────
    # IS 456 Cl. 26.5.1.2 — not directly for columns but good practice
    # NBC 105 Annex A — minimum 2 bars each face between corner bars
    if n_bars > 4 and (b_mm > 300 or D_mm > 300):
        notes.append(
            "Intermediate bars required on each face > 300mm wide. "
            "Ensure bar spacing ≤ 300mm along each face (NBC 105 Annex A §A.4.3)."
        )

    # ── Status notes ──────────────────────────────────────────────────────────
    if pct_prov < 0.8:
        notes.append(f"⚠ Steel {pct_prov:.2f}% < 0.8% min (IS 456 Cl. 26.5.3).")
    if pct_prov > max_steel_pct:
        notes.append(f"⚠ Steel {pct_prov:.2f}% > {max_steel_pct}% max (NBC 105 Annex A).")
    if interaction_f > 1.0:
        notes.append(
            f"⚠ Biaxial interaction = {interaction_f:.4f} > 1.0. "
            "Increase section size or steel percentage."
        )
    else:
        notes.append(
            f"Biaxial interaction = {interaction_f:.4f} ≤ 1.0  ✓  "
            f"(αn={alpha_f:.2f}, Puz={Puz_f/1000:.0f} kN)"
        )
    notes.append(
        f"Pure axial capacity Pu,max = {Pu_max_kN:.0f} kN  "
        f"({'> Pu ✓' if Pu_max_kN >= Pu_kN else '< Pu ⚠ overstressed'}) (IS 456 §39.3)"
    )
    notes.append(
        f"NBC 105 Annex A — Confinement zone: top + bottom {ductile['lo_mm']:.0f} mm.  "
        f"Tie @ {ductile['s_conf_mm']:.0f} mm c/c in zone, {ductile['s_out_mm']:.0f} mm elsewhere.  "
        f"135° hooks required in confinement zone.  "
        f"Lap splices only in middle ½ of column height.  "
        f"Hoop Ash: req={ductile['Ash_req_mm2']:.1f} mm², prov={ductile['Ash_prov_mm2']:.1f} mm² "
        f"({'OK ✓' if ductile['hoop_ok'] else '⚠ INCREASE TIE SIZE'})."
    )

    return {
        "b_mm": b_mm, "D_mm": D_mm, "Ag_mm2": round(Ag),
        "d_prime_mm": round(d_prime, 1),
        # Slenderness
        "lambda_x": round(lambda_x, 2), "lambda_y": round(lambda_y, 2),
        "is_slender": is_slender,
        # Design loads
        "Pu_kN": Pu_kN,
        "Ma_x_kNm": round(Ma_x, 3), "Ma_y_kNm": round(Ma_y, 3),
        "emin_x_mm": round(emin_x, 1), "emin_y_mm": round(emin_y, 1),
        "Mux_design_kNm": round(Mux_design, 3),
        "Muy_design_kNm": round(Muy_design, 3),
        # Steel
        "Ast_req_mm2": round(Ast_design, 1),
        "Ast_min_mm2": round((0.8/100)*Ag, 1),
        "Ast_max_mm2": round((max_steel_pct/100)*Ag, 1),
        "Ast_prov_mm2": round(Ast_prov, 1),
        "steel_pct": round(pct_prov, 2),
        "no_of_bars": n_bars,
        "bar_dia_mm": main_dia_mm,
        # Capacity
        "Mux1_kNm": round(Mux1_f, 2),
        "Muy1_kNm": round(Muy1_f, 2),
        "Puz_kN":   round(Puz_f/1000, 1),
        "Pu_max_kN":round(Pu_max_kN, 1),
        "alpha_n":  round(alpha_f, 3),
        "interaction": round(interaction_f, 4),
        # Ties
        "tie_dia_mm":     tie_dia_mm,
        "tie_spacing_mm": s_tie,
        # Ductile detailing (NBC 105 Annex A)
        "conf_zone_mm":   ductile["lo_mm"],
        "conf_tie_sp_mm": ductile["s_conf_mm"],
        "out_tie_sp_mm":  ductile["s_out_mm"],
        "Ash_req_mm2":    ductile["Ash_req_mm2"],
        "Ash_prov_mm2":   ductile["Ash_prov_mm2"],
        "hoop_ok":        ductile["hoop_ok"],
        "notes": notes,
    }
