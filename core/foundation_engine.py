"""
core/foundation_engine.py — IS 456:2000 Isolated Footing + NBC 105:2025 §3.8
=============================================================================
Priority: NBC 105:2025 §3.8 (seismic SBC allowance) over IS 456 §34.
Covers IS 456:2000 §34 fully:
  §34.1   General requirements (min depth 300mm RC, 150mm PCC)
  §34.2   Soil pressure under footing
  §34.4   Design of rectangular footing
  §34.4.1 Bending moment at column face
  §34.4.2 Shear (one-way at d from face; two-way at d/2 from column)
  §34.4.3 Bond and development length
  NBC 105:2025 §3.8 — Increase in allowable bearing pressure (seismic +50%)
"""
from __future__ import annotations
import math

_TAU_C = [
    (0.15,0.28),(0.25,0.36),(0.50,0.48),(0.75,0.56),(1.00,0.62),
    (1.25,0.67),(1.50,0.72),(1.75,0.75),(2.00,0.79),(2.25,0.81),
    (2.50,0.82),(3.00,0.82),
]

def _interp(x, xs, ys):
    if x<=xs[0]: return ys[0]
    if x>=xs[-1]:return ys[-1]
    for i in range(len(xs)-1):
        if xs[i]<=x<=xs[i+1]:
            return ys[i]+(ys[i+1]-ys[i])*(x-xs[i])/(xs[i+1]-xs[i])
    return ys[-1]

def _tau_c(pt, fck):
    base = _interp(pt, [p for p,_ in _TAU_C], [t for _,t in _TAU_C])
    return base * (min((fck/20)**0.5, 1.25) if fck > 20 else 1.0)

def _Ast_required(Mu_kNm_per_m, d_mm, fck, fy, D_mm) -> float:
    """Ast mm²/m for given Mu (kN·m/m), effective depth d (mm), and overall depth D (mm)."""
    Mu_Nmm = Mu_kNm_per_m * 1e6
    xu_max = 0.48 * d_mm
    a = -0.36*0.42*fck; b_ = 0.36*fck*d_mm; c = -Mu_Nmm
    disc = b_**2 - 4*a*c
    if disc < 0:
        return (0.0012 if fy > 250 else 0.0015) * 1000 * D_mm   # IS 456 §26.5.2.1
    xu_list = [x for x in ((-b_+math.sqrt(disc))/(2*a),(-b_-math.sqrt(disc))/(2*a))
               if 0 < x <= xu_max]
    xu = min(xu_list) if xu_list else xu_max
    z  = d_mm - 0.42*xu
    Ast = Mu_Nmm / (0.87*fy*z) if z > 0 else 0
    Ast_min = (0.0012 if fy > 250 else 0.0015) * 1000 * D_mm   # IS 456 §34.4.1 / §26.5.2.1
    return max(Ast, Ast_min)

def _dev_length(bar_dia, fy, fck) -> float:
    """IS 456 Table 5 — basic development length (tension, deformed bar)."""
    tau_bd = {20:1.2, 25:1.4, 30:1.5, 35:1.7, 40:1.9}.get(int(fck), 1.2)
    return (0.87 * fy * bar_dia) / (4 * tau_bd)


def design_footing(
    col_b_mm:  float,       # column width (mm)
    col_D_mm:  float,       # column depth (mm)
    P_kN:      float,       # service column axial load (kN)
    Mx_kNm:    float = 0.0, # service moment about x (kN·m)
    My_kNm:    float = 0.0, # service moment about y (kN·m)
    SBC_kPa:   float = 150.0,
    fck:       float = 20.0,
    fy:        float = 415.0,
    cover_mm:  float = 50.0,
    bar_dia_mm:float = 12.0,
    footing_D_mm: float | None = None,
    footing_L_mm: float | None = None,
    footing_B_mm: float | None = None,
    seismic:   bool = False,
) -> dict:
    notes: list[str] = []

    # ── Minimum depth check IS 456 §34.1.3 ───────────────────────────────────
    D_min_rc = 300.0   # RC isolated footing
    D_min_pcc = 150.0  # PCC (mass concrete) footing

    # ── Seismic SBC allowance (NBC 105:2025 §3.8) ────────────────────────────
    sbc_use = SBC_kPa * (1.5 if seismic else 1.0)
    if seismic:
        notes.append(
            f"Seismic load combination: SBC increased by 50% per NBC 105:2025 §3.8. "
            f"Effective SBC = {sbc_use:.0f} kN/m²."
        )

    # ── Self-weight estimate (10% of column load → refine with plan area) ────
    Wf   = 0.10 * P_kN
    Ptot = P_kN + Wf

    # ── Plan size ─────────────────────────────────────────────────────────────
    if footing_L_mm and footing_B_mm:
        L = footing_L_mm / 1000.0
        B = footing_B_mm / 1000.0
    else:
        A_req = Ptot / sbc_use
        # Minimum dimension at least 1.5× column dimension
        side_min = max(math.ceil(math.sqrt(A_req) * 10) / 10,
                       max(col_D_mm, col_b_mm) * 1.5 / 1000)
        L = side_min; B = side_min
    A = L * B

    # Refine self-weight
    Wf   = A * ((footing_D_mm or 450.0) / 1000.0) * 25.0   # 25 kN/m³ for RC
    Ptot = P_kN + Wf

    # ── Soil pressure ─────────────────────────────────────────────────────────
    # For SBC check, use total load (P + Wf)
    q_max_sbc = Ptot/A + 6*abs(My_kNm)/(B*L**2) + 6*abs(Mx_kNm)/(L*B**2)
    q_min_sbc = Ptot/A - 6*abs(My_kNm)/(B*L**2) - 6*abs(Mx_kNm)/(L*B**2)

    # For structural design (bending/shear), use net upward pressure from column load only
    q_avg = P_kN / A
    q_max_net = P_kN/A + 6*abs(My_kNm)/(B*L**2) + 6*abs(Mx_kNm)/(L*B**2)

    pressure_ok = q_max_sbc <= sbc_use and q_min_sbc >= 0
    if q_max_sbc > sbc_use:
        over = q_max_sbc - sbc_use
        notes.append(
            f"⚠ q_max={q_max_sbc:.1f} exceeds SBC={sbc_use:.0f} kN/m² "
            f"(by {over:.1f}). Increase plan size."
        )
    if q_min_sbc < 0:
        notes.append(
            f"⚠ q_min={q_min_sbc:.1f} kN/m² < 0 (tensile — no soil tension). "
            "Increase plan size or check eccentricity."
        )

    # ── Footing depth ─────────────────────────────────────────────────────────
    if footing_D_mm:
        D_f = footing_D_mm
    else:
        # Estimate depth for punching: try D ≈ (L - col_D/1000)/2 / 8
        span_est = max((L - col_D_mm/1000)/2, (B - col_b_mm/1000)/2)
        D_est    = max(D_min_rc, span_est * 1000 / 8, 300.0)
        D_f      = math.ceil(D_est / 50) * 50
    D_f = max(D_f, D_min_rc)
    d   = D_f - cover_mm - bar_dia_mm   # effective depth

    if D_f < D_min_rc:
        notes.append(
            f"⚠ Footing depth {D_f:.0f} mm < 300 mm minimum for RC (IS 456 §34.1.3). "
            "Use 300 mm minimum."
        )

    notes.append(
        f"Footing: {L*1000:.0f}×{B*1000:.0f}×{D_f:.0f} mm.  "
        f"Effective depth d = {d:.0f} mm (cover={cover_mm:.0f} mm, Ø{bar_dia_mm:.0f} mm)."
    )

    # ── Net factored design pressure ──────────────────────────────────────────
    # Factored for design: 1.5 × service (net soil pressure on footing)
    qu = 1.5 * q_avg   # kN/m² (factored net)

    # ── Overhangs ─────────────────────────────────────────────────────────────
    a_L = (L - col_D_mm/1000) / 2.0   # overhang in long direction (m)
    a_B = (B - col_b_mm/1000) / 2.0   # overhang in short direction (m)

    # ── Bending moment at face of column (IS 456 §34.4.1) ────────────────────
    Mu_L = qu * B * a_L**2 / 2.0    # kN·m (bending strip B wide in L direction)
    Mu_B = qu * L * a_B**2 / 2.0    # kN·m

    Mu_L_per_m = Mu_L / B           # kN·m/m
    Mu_B_per_m = Mu_B / L

    # ── Steel design ─────────────────────────────────────────────────────────
    Ast_L = _Ast_required(Mu_L_per_m, d, fck, fy, D_f)   # mm²/m in L dir
    Ast_B = _Ast_required(Mu_B_per_m, d, fck, fy, D_f)   # mm²/m in B dir

    area_bar = math.pi * bar_dia_mm**2 / 4.0
    sp_L = min(1000 * area_bar / Ast_L, 3*d, 450.0)   # IS 456 §26.3.3b
    sp_B = min(1000 * area_bar / Ast_B, 3*d, 450.0)
    sp_L = max(75.0, math.floor(sp_L / 10) * 10)
    sp_B = max(75.0, math.floor(sp_B / 10) * 10)
    ast_L_prov = area_bar * 1000 / sp_L
    ast_B_prov = area_bar * 1000 / sp_B

    # ── One-way shear (IS 456 §34.4.2, critical section at d from face) ──────
    crit_L = a_L - d/1000    # m
    crit_B = a_B - d/1000
    Vu_L  = max(0.0, qu * B * crit_L)    # kN
    Vu_B  = max(0.0, qu * L * crit_B)
    tau_v_L = Vu_L * 1000 / (B * 1000 * d) if d > 0 else 0   # MPa
    tau_v_B = Vu_B * 1000 / (L * 1000 * d) if d > 0 else 0

    pt_L = min(100*ast_L_prov/(1000*d), 3.0)
    pt_B = min(100*ast_B_prov/(1000*d), 3.0)
    tc_L = _tau_c(pt_L, fck)
    tc_B = _tau_c(pt_B, fck)

    # k factor for D < 300mm (IS 456 Cl. 40.2.1)
    k_fac = 1.3 if D_f <= 150 else max(1.0, 1.3-(D_f-150)*0.3/150) if D_f <= 300 else 1.0
    one_way_ok = (tau_v_L <= k_fac*tc_L) and (tau_v_B <= k_fac*tc_B)
    if not one_way_ok:
        notes.append(
            f"⚠ One-way shear: τv_L={tau_v_L:.3f} vs k·τc={k_fac*tc_L:.3f}, "
            f"τv_B={tau_v_B:.3f} vs k·τc={k_fac*tc_B:.3f} MPa. Increase depth."
        )
    else:
        notes.append(
            f"One-way shear: τv_L={tau_v_L:.3f} ≤ {k_fac*tc_L:.3f}, "
            f"τv_B={tau_v_B:.3f} ≤ {k_fac*tc_B:.3f} MPa  ✓"
        )

    # ── Two-way (punching) shear (IS 456 §34.4.2, §31.6) ────────────────────
    # Critical perimeter at d/2 from column face
    p_len = col_D_mm + d    # mm (in L direction)
    p_brd = col_b_mm + d    # mm (in B direction)
    b0    = 2 * (p_len + p_brd)   # perimeter (mm)
    A_exc = (p_len/1000) * (p_brd/1000)   # excluded area m²
    Vp    = max(0.0, qu * (A - A_exc))
    tau_v_punch = Vp * 1000 / (b0 * d) if (b0 > 0 and d > 0) else 0
    tau_c_punch = 0.25 * math.sqrt(fck)   # IS 456 §31.6.3.1
    punch_ok    = tau_v_punch <= tau_c_punch

    if not punch_ok:
        # Estimate required depth for punching
        # V = qu*(A-A_exc), tau_c_punch = V/(b0*d) → solve for d iteratively
        d_need = math.ceil(Vp*1000 / (tau_c_punch * b0) + 10)
        notes.append(
            f"⚠ Punching: τv={tau_v_punch:.3f} > τc={tau_c_punch:.3f} MPa. "
            f"Need d ≥ {d_need:.0f} mm → increase footing depth."
        )
    else:
        notes.append(
            f"Punching shear: τv={tau_v_punch:.3f} ≤ τc={tau_c_punch:.3f} MPa  ✓"
        )

    # ── Development length (IS 456 §34.4.3) ──────────────────────────────────
    Ld = _dev_length(bar_dia_mm, fy, fck)
    # Available from face of column to end of bar (minus cover)
    avail_L = a_L * 1000 - cover_mm
    avail_B = a_B * 1000 - cover_mm
    dev_ok  = (avail_L >= Ld) and (avail_B >= Ld)
    if not dev_ok:
        notes.append(
            f"⚠ Development: Ld={Ld:.0f} mm > available={min(avail_L,avail_B):.0f} mm. "
            "Increase plan size or use hooks / reduce bar diameter."
        )
    else:
        notes.append(
            f"Development length: Ld={Ld:.0f} mm ≤ available={min(avail_L,avail_B):.0f} mm  ✓"
        )

    # ── Column-footing interface check (IS 456 §34.4.4) ─────────────────────
    # Bearing stress at interface: Pu / (col_b × col_D) ≤ 0.45 fck × √(A1/A2)
    A_col = col_b_mm * col_D_mm / 1e6   # m²
    A1    = min(4.0 * A_col, A)          # dispersal area (frustum, IS 456 §34.4.4)
    sqrt_ratio = min(math.sqrt(A1 / max(A_col, 1e-9)), 2.0)
    bear_allow = 0.45 * fck * sqrt_ratio   # MPa
    Pu_factored = 1.5 * P_kN * 1000 / (col_b_mm * col_D_mm)   # MPa
    bear_ok = Pu_factored <= bear_allow
    notes.append(
        f"Bearing at col-ftg interface: {Pu_factored:.2f} MPa "
        f"{'≤' if bear_ok else '>'} {bear_allow:.2f} MPa "
        f"({'OK ✓' if bear_ok else '⚠ Provide dowels IS 456 §34.4.4'})"
    )

    return {
        # Plan
        "L_mm": round(L*1000), "B_mm": round(B*1000),
        "D_mm": D_f, "d_mm": round(d),
        "A_m2": round(A, 3),
        # Pressures
        "q_avg_kPa":    round(q_avg, 2),
        "q_max_kPa":    round(q_max_sbc, 2),
        "q_min_kPa":    round(q_min_sbc, 2),
        "SBC_used_kPa": sbc_use,
        "pressure_ok":  pressure_ok,
        # Design pressure
        "qu_kPa":   round(qu, 2),
        "a_L_m":    round(a_L, 3),
        "a_B_m":    round(a_B, 3),
        # Moments
        "Mu_L_kNm": round(Mu_L, 2),
        "Mu_B_kNm": round(Mu_B, 2),
        # Reinforcement
        "Ast_L_per_m_mm2":  round(Ast_L, 1),
        "Ast_B_per_m_mm2":  round(Ast_B, 1),
        "sp_L_mm": sp_L, "sp_B_mm": sp_B,
        "ast_L_prov_mm2m":  round(ast_L_prov, 1),
        "ast_B_prov_mm2m":  round(ast_B_prov, 1),
        "bar_dia_mm": bar_dia_mm,
        # Shear
        "tau_v_L":  round(tau_v_L, 3),
        "tau_c_L":  round(k_fac*tc_L, 3),
        "tau_v_B":  round(tau_v_B, 3),
        "tau_c_B":  round(k_fac*tc_B, 3),
        "one_way_ok": one_way_ok,
        "tau_v_punch": round(tau_v_punch, 3),
        "tau_c_punch": round(tau_c_punch, 3),
        "punch_ok":    punch_ok,
        # Development
        "Ld_mm":      round(Ld, 0),
        "avail_L_mm": round(avail_L, 0),
        "avail_B_mm": round(avail_B, 0),
        "dev_ok":     dev_ok,
        # Bearing
        "bear_stress_MPa": round(Pu_factored, 3),
        "bear_allow_MPa":  round(bear_allow, 3),
        "bear_ok":         bear_ok,
        "notes": notes,
    }
