"""
core/staircase_engine.py — IS 456:2000 Staircase Design
=======================================================
Covers:
  Dog-legged staircase (most common in Nepal)
  Waist slab method — load on inclined slab per IS 456:2000
  Effective span per IS 456:2000 §33.1
  Step geometry: tread, riser, going
  Waist slab thickness (from deflection L/d)
  Reinforcement: main bars (along span) + distribution bars
  Checks: moment, shear, deflection (IS 456 §23.2)
  Self-weight of steps: 0.5 × tread × riser × γ_conc (IS 456 §33.2)
  NBC 105:2025: staircase treated as inclined slab (no special clause — IS 456 governs)
"""
from __future__ import annotations
import math


def design_staircase(
    floor_to_floor_m: float,     # floor-to-floor height (m)
    stair_width_m:    float,     # width of stair flight (m)
    tread_mm:         float = 250.0,   # horizontal going (mm)
    riser_mm:         float = 150.0,   # vertical rise (mm)
    fck:              float = 20.0,
    fy:               float = 415.0,
    ll_kNm2:          float = 3.0,     # imposed live load (kN/m²) per IS 875 Pt 2
    cover_mm:         float = 15.0,
    main_dia_mm:      float = 10.0,
    dist_dia_mm:      float = 8.0,
    gamma_conc:       float = 25.0,    # kN/m³
    support_type:     str   = "SS",    # "SS" (simply supported) | "One end fixed"
) -> dict:
    """Design a dog-legged staircase waist-slab per IS 456:2000 §33."""
    notes: list[str] = []

    # ── Step geometry ─────────────────────────────────────────────────────────
    n_risers  = round(floor_to_floor_m * 1000 / riser_mm)
    riser_act = floor_to_floor_m * 1000 / n_risers   # actual riser (mm)
    n_going   = n_risers - 1   # number of treads per flight (for dog-legged: n/2 per flight)
    n_flight  = math.ceil(n_risers / 2)   # risers per flight

    # Check 2R + T ≈ 600–650 mm (IS 456 §33 comfort rule)
    comfort = 2 * riser_act + tread_mm
    comfort_ok = 600 <= comfort <= 650
    notes.append(
        f"Step geometry: R={riser_act:.0f}mm, T={tread_mm:.0f}mm. "
        f"2R+T = {comfort:.0f}mm ({'OK ✓' if comfort_ok else '⚠ outside 600–650 range'}). "
        f"Flights: {n_flight} risers each."
    )

    # ── Effective span IS 456:2000 §33.1 ──────────────────────────────────────
    # For dog-legged staircase:
    # Horizontal span of flight = (n_flight − 1) × tread + (landing_width typically 1.0–1.2m)
    # Here: span = (n_flight−1) × T + landing/2 each end
    landing_m  = 1.0   # typical landing width
    horiz_span = (n_flight - 1) * tread_mm / 1000 + landing_m
    # Effective span including landing
    L_eff      = horiz_span   # m (horizontal projection)
    notes.append(
        f"Effective horizontal span L = {L_eff:.2f} m "
        f"({n_flight-1} treads + landing {landing_m:.1f}m, IS 456 §33.1)."
    )

    # ── Slope angle ───────────────────────────────────────────────────────────
    alpha     = math.atan(riser_act / tread_mm)   # radians
    cos_alpha = math.cos(alpha)
    sec_alpha = 1 / cos_alpha  # slant length / horizontal span ratio

    # ── Waist slab thickness (from deflection) ────────────────────────────────
    # IS 456 §23.2: L/d basic = 20 (SS), 26 (fixed one end)
    ld_basic = 20 if support_type == "SS" else 26
    d_min    = math.ceil(L_eff * 1000 / ld_basic / 5) * 5   # round to 5mm
    D_waist  = d_min + cover_mm + main_dia_mm   # overall thickness
    D_waist  = max(D_waist, 100.0)   # absolute minimum
    D_waist  = math.ceil(D_waist / 10) * 10   # round to nearest 10mm
    d_waist  = D_waist - cover_mm - main_dia_mm / 2.0
    notes.append(
        f"Waist slab: D = {D_waist:.0f} mm, d = {d_waist:.1f} mm "
        f"(from L/d = {ld_basic}, IS 456 §23.2)."
    )

    # ── Loading per unit plan area ────────────────────────────────────────────
    # Self-weight of waist slab (inclined):
    sw_waist  = gamma_conc * (D_waist / 1000) * sec_alpha   # kN/m²
    # Self-weight of steps: 0.5 × riser × tread per unit plan area
    sw_steps  = gamma_conc * 0.5 * (riser_act / 1000) * (tread_mm / 1000) / (tread_mm / 1000)
    # = γ × 0.5 × R  (per unit horizontal area)
    sw_steps  = gamma_conc * 0.5 * (riser_act / 1000)   # kN/m²
    # Floor finish (assume 1.0 kN/m²)
    sw_finish = 1.0
    w_DL      = sw_waist + sw_steps + sw_finish
    w_LL      = ll_kNm2
    w_total   = 1.5 * (w_DL + w_LL)   # factored (IS 456 §5.3)

    notes.append(
        f"Loading: DL = {w_DL:.2f} kN/m² (waist={sw_waist:.2f} + steps={sw_steps:.2f} + "
        f"finish={sw_finish:.1f}), LL = {w_LL:.2f} kN/m². "
        f"Factored wu = 1.5×({w_DL:.2f}+{w_LL:.2f}) = {w_total:.2f} kN/m²."
    )

    # ── Design moment & shear ─────────────────────────────────────────────────
    coeff_M = 1/8 if support_type == "SS" else 1/10  # hogging at support for fixed end
    Mu   = w_total * L_eff**2 * coeff_M   # kN·m/m width
    Vu   = w_total * L_eff / 2.0          # kN/m

    # ── Reinforcement design ──────────────────────────────────────────────────
    xu_max = 0.48 * d_waist
    Mu_lim = 0.36 * fck * 1000 * xu_max * (d_waist - 0.42 * xu_max) / 1e6
    is_doubly = Mu > Mu_lim
    if is_doubly:
        notes.append("⚠ Mu > Mu,lim. Increase waist slab thickness.")

    Mu_Nmm = Mu * 1e6
    a_q = -0.36 * 0.42 * fck * 1000
    b_q =  0.36 * fck * 1000 * d_waist
    c_q = -Mu_Nmm
    disc = b_q**2 - 4 * a_q * c_q
    if disc >= 0:
        xu_list = [x for x in ((-b_q + math.sqrt(disc)) / (2*a_q),
                                (-b_q - math.sqrt(disc)) / (2*a_q))
                   if 0 < x <= xu_max]
        xu = min(xu_list) if xu_list else xu_max
        z  = d_waist - 0.42 * xu
        Ast_req = Mu_Nmm / (0.87 * fy * z) if z > 0 else 0.0
    else:
        Ast_req = 0.0

    Ast_min = (0.85 / fy) * 1000 * d_waist  # per m width
    Ast     = max(Ast_req, Ast_min)

    # Distribution steel: 0.12% bD for fy=415, 0.15% for fy=250
    dist_pct  = 0.0012 if fy >= 415 else 0.0015   # IS 456 §26.5.2
    Ast_dist  = dist_pct * 1000 * D_waist

    # Bar spacing
    a_main = math.pi * main_dia_mm**2 / 4.0
    a_dist = math.pi * dist_dia_mm**2  / 4.0
    sp_main = min(1000 * a_main / Ast,      min(3 * d_waist, 450))
    sp_dist = min(1000 * a_dist / Ast_dist, min(5 * d_waist, 450))
    sp_main = max(75.0, math.floor(sp_main / 10) * 10)
    sp_dist = max(75.0, math.floor(sp_dist / 10) * 10)
    ast_main_prov = a_main * 1000 / sp_main
    ast_dist_prov = a_dist * 1000 / sp_dist

    # ── Shear check ───────────────────────────────────────────────────────────
    tau_v = Vu * 1000 / (1000 * d_waist)   # MPa (per m width)
    pt    = min(100 * ast_main_prov / (1000 * d_waist), 3.0)
    # τc from IS 456 Table 19 (simplified)
    tau_c_table = [(0.15,0.28),(0.25,0.36),(0.50,0.48),(0.75,0.56),(1.00,0.62),
                   (1.25,0.67),(1.50,0.72),(1.75,0.75),(2.00,0.79),(2.50,0.82),(3.00,0.82)]
    pts = [p for p,_ in tau_c_table]; tcs = [t for _,t in tau_c_table]
    def _interp(x):
        if x<=pts[0]: return tcs[0]
        if x>=pts[-1]:return tcs[-1]
        for i in range(len(pts)-1):
            if pts[i]<=x<=pts[i+1]:
                return tcs[i]+(tcs[i+1]-tcs[i])*(x-pts[i])/(pts[i+1]-pts[i])
        return tcs[-1]
    tau_c = _interp(pt) * ((fck/20)**0.5 if fck > 20 else 1.0)
    shear_ok = tau_v <= tau_c
    if not shear_ok:
        notes.append(f"⚠ Shear: τv={tau_v:.3f} > τc={tau_c:.3f} MPa. Increase waist slab depth.")
    else:
        notes.append(f"Shear OK: τv={tau_v:.3f} ≤ τc={tau_c:.3f} MPa  ✓")

    # ── Deflection check ──────────────────────────────────────────────────────
    fs_serv   = min(0.58 * fy * (Ast_req / max(ast_main_prov, 1e-9)), 0.58 * fy)
    pt_serv   = min(100 * ast_main_prov / (1000 * d_waist), 2.8)
    # kt approximation: from table at fs≈240, pt≈0.3 → kt≈1.6
    kt        = min(2.0, max(0.5, 1.6 - (fs_serv - 120) / 400))
    ld_allow  = ld_basic * kt
    ld_prov   = L_eff * 1000 / d_waist
    defl_ok   = ld_prov <= ld_allow
    notes.append(
        f"Deflection: L/d = {ld_prov:.1f}  ≤  {ld_allow:.1f} "
        f"(basic={ld_basic}, kt={kt:.2f})  {'✓' if defl_ok else '⚠ REVISE'}"
    )

    # ── Development length ────────────────────────────────────────────────────
    tau_bd = {20:1.2,25:1.4,30:1.5,35:1.7,40:1.9}.get(int(fck),1.2)
    Ld_main = (0.87 * fy * main_dia_mm) / (4 * tau_bd)

    return {
        # Geometry
        "n_risers":      n_risers,
        "n_risers_per_flight": n_flight,
        "riser_actual_mm": round(riser_act, 1),
        "tread_mm":      tread_mm,
        "comfort_check": round(comfort, 0),
        "comfort_ok":    comfort_ok,
        "alpha_deg":     round(math.degrees(alpha), 1),
        "L_eff_m":       round(L_eff, 3),
        # Slab
        "D_waist_mm":    D_waist,
        "d_waist_mm":    round(d_waist, 1),
        # Loading
        "w_DL_kNm2":    round(w_DL, 3),
        "w_LL_kNm2":    round(w_LL, 2),
        "wu_kNm2":      round(w_total, 3),
        # Design
        "Mu_kNm_m":     round(Mu, 3),
        "Mu_lim_kNm_m": round(Mu_lim, 3),
        "Vu_kN_m":      round(Vu, 3),
        "is_doubly":    is_doubly,
        # Reinforcement
        "Ast_req_mm2_m":  round(Ast, 1),
        "Ast_dist_mm2_m": round(Ast_dist, 1),
        "sp_main_mm":     sp_main,
        "sp_dist_mm":     sp_dist,
        "ast_main_prov":  round(ast_main_prov, 1),
        "ast_dist_prov":  round(ast_dist_prov, 1),
        "main_dia_mm":    main_dia_mm,
        "dist_dia_mm":    dist_dia_mm,
        # Checks
        "tau_v":      round(tau_v, 3),
        "tau_c":      round(tau_c, 3),
        "shear_ok":   shear_ok,
        "ld_prov":    round(ld_prov, 1),
        "ld_allow":   round(ld_allow, 1),
        "defl_ok":    defl_ok,
        "Ld_main_mm": round(Ld_main, 0),
        "notes":      notes,
    }
