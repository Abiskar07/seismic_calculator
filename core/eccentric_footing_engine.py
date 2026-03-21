"""
core/eccentric_footing_engine.py — IS 456:2000 §34 + NBC 105:2025 §3.8
Eccentric and Combined Footing Design
======================================
Covers:
  • Concentric and eccentric isolated footings (one-way + two-way eccentricity)
  • Column-to-footing eccentricity from moments
  • Pressure diagram (trapezoidal / triangular — uplift detection)
  • Effective area method when tension (IS 456 §34.2.4)
  • Combined (rectangular) footing for two columns
  • Full bending, shear, punching, development length checks
  • NBC 105:2025 §3.8 seismic SBC allowance
"""
from __future__ import annotations
import math

_TAU_C = [(0.15,0.28),(0.25,0.36),(0.50,0.48),(0.75,0.56),(1.00,0.62),
           (1.25,0.67),(1.50,0.72),(1.75,0.75),(2.00,0.79),(2.25,0.81),
           (2.50,0.82),(3.00,0.82)]

def _tc(pt, fck):
    xs=[p for p,_ in _TAU_C]; ys=[t for _,t in _TAU_C]
    def interp(x):
        if x<=xs[0]: return ys[0]
        if x>=xs[-1]: return ys[-1]
        for i in range(len(xs)-1):
            if xs[i]<=x<=xs[i+1]:
                return ys[i]+(ys[i+1]-ys[i])*(x-xs[i])/(xs[i+1]-xs[i])
        return ys[-1]
    return interp(pt) * (min((fck/20)**0.5, 1.25) if fck>20 else 1.0)

def _ast_req(Mu_kNm_per_m, d_mm, fck, fy):
    if Mu_kNm_per_m <= 0:
        return (0.85/fy)*1000*d_mm
    Mu = Mu_kNm_per_m * 1e6
    a=-0.36*0.42*fck; b=0.36*fck*d_mm; c=-Mu
    disc=b**2-4*a*c
    if disc<0: return (0.85/fy)*1000*d_mm
    xu_list=[x for x in ((-b+math.sqrt(disc))/(2*a),(-b-math.sqrt(disc))/(2*a))
             if 0<x<=0.48*d_mm]
    xu=min(xu_list) if xu_list else 0.48*d_mm
    z=d_mm-0.42*xu
    return max(Mu/(0.87*fy*z) if z>0 else 0, (0.85/fy)*1000*d_mm)

def _ld(bar_dia, fy, fck):
    tbd={20:1.2,25:1.4,30:1.5,35:1.7,40:1.9}.get(int(fck),1.2)
    return (0.87*fy*bar_dia)/(4*tbd)


def design_eccentric_footing(
    col_b_mm:      float,      # column width (mm)
    col_D_mm:      float,      # column depth (mm)
    P_kN:          float,      # service axial load (kN)
    Mx_kNm:        float = 0.0,# moment about x-axis (kN·m)
    My_kNm:        float = 0.0,# moment about y-axis (kN·m)
    SBC_kPa:       float = 150.0,
    fck:           float = 20.0,
    fy:            float = 415.0,
    cover_mm:      float = 50.0,
    bar_dia_mm:    float = 12.0,
    footing_D_mm:  float | None = None,
    footing_L_mm:  float | None = None,
    footing_B_mm:  float | None = None,
    seismic:       bool = False,
) -> dict:
    """
    Eccentric isolated footing design per IS 456:2000 §34.
    Handles biaxial eccentricity with pressure diagram and uplift check.
    """
    notes: list[str] = []

    # ── SBC (NBC 105:2025 §3.8 seismic allowance) ────────────────────────────
    sbc_use = SBC_kPa * (1.5 if seismic else 1.0)
    if seismic:
        notes.append(f"Seismic: SBC × 1.5 = {sbc_use:.0f} kN/m² (NBC 105:2025 §3.8).")

    # ── Eccentricities ─────────────────────────────────────────────────────────
    ex = abs(My_kNm) / max(P_kN, 0.01)   # m (eccentricity in x-direction, from My)
    ey = abs(Mx_kNm) / max(P_kN, 0.01)   # m (eccentricity in y-direction, from Mx)

    # Kern of footing: e ≤ L/6 for no tension
    # For combined biaxial: ex/L + ey/B ≤ 1/6 (Meyerhof criterion)
    notes.append(
        f"Eccentricities: ex={ex:.3f} m (from My), ey={ey:.3f} m (from Mx)."
    )

    # ── Plan size determination ────────────────────────────────────────────────
    if footing_L_mm and footing_B_mm:
        L = footing_L_mm / 1000; B = footing_B_mm / 1000
    else:
        # For eccentric footing shift centroid; increase size for moment
        # Required area accounting for eccentricity:
        # q_max = P/A * (1 + 6ex/L + 6ey/B) ≤ SBC
        # First try: A = 1.3 * P/SBC (add ~30% for moments)
        A_req  = max(1.25 * P_kN / sbc_use, (col_D_mm/1000+1.0)*(col_b_mm/1000+1.0))
        side   = math.ceil(math.sqrt(A_req) * 10) / 10
        # Increase if eccentricity is large
        if ex > side / 6:
            side = math.ceil(6 * ex * 10) / 10 + 0.2
        if ey > side / 6:
            side = math.ceil(6 * ey * 10) / 10 + 0.2
        L = side; B = side

    A = L * B
    notes.append(f"Footing plan: {L*1000:.0f}×{B*1000:.0f} mm (A={A:.2f} m²).")

    # ── Pressure diagram ───────────────────────────────────────────────────────
    # General formula: q = P/A ± My/Zy ± Mx/Zx
    # Zy = B*L²/6, Zx = L*B²/6
    Zy = B * L**2 / 6   # m³
    Zx = L * B**2 / 6

    q_c   = P_kN / A                      # average (centre)
    q_max = q_c + abs(My_kNm)/Zy + abs(Mx_kNm)/Zx
    q_min = q_c - abs(My_kNm)/Zy - abs(Mx_kNm)/Zx

    # Check kern (no tension): IS 456 §34.2.4
    # If q_min < 0, part of footing lifts. Use effective contact area.
    tension = q_min < 0
    if tension:
        notes.append(
            f"⚠ q_min = {q_min:.2f} kN/m² < 0 (uplift/tension zone). "
            "Effective contact area method applied (IS 456 §34.2.4)."
        )
        # Effective contact length L' for one-way eccentricity (conservative for biaxial):
        # L' = 3*(L/2 - ex) for My dominant; B' = 3*(B/2 - ey)
        L_eff = max(0.1, 3*(L/2 - ex))
        B_eff = max(0.1, 3*(B/2 - ey))
        A_eff = L_eff * B_eff
        q_max_eff = P_kN / (0.5 * A_eff)   # triangular: peak = 2P/A_eff
        q_design  = q_max_eff
        notes.append(
            f"Effective area: L'={L_eff*1000:.0f}mm, B'={B_eff*1000:.0f}mm. "
            f"q_max,eff = {q_max_eff:.1f} kN/m²."
        )
    else:
        q_design = q_max

    # Check against SBC
    pressure_ok = q_max <= sbc_use
    if not pressure_ok:
        notes.append(
            f"⚠ q_max={q_max:.1f} > SBC={sbc_use:.0f} kN/m². Increase plan size.")
    else:
        notes.append(f"Pressure OK: q_max={q_max:.1f} ≤ {sbc_use:.0f} kN/m²  ✓")

    # ── Footing depth ─────────────────────────────────────────────────────────
    D_f = footing_D_mm or max(300.0, math.ceil(max((L-col_D_mm/1000)/2,
                                                     (B-col_b_mm/1000)/2)*1000/8/50)*50)
    D_f = max(D_f, 300.0)
    d   = D_f - cover_mm - bar_dia_mm
    notes.append(f"Footing: {L*1000:.0f}×{B*1000:.0f}×{D_f:.0f} mm, d={d:.0f} mm.")

    # ── Factored design pressure ───────────────────────────────────────────────
    qu = 1.5 * q_design    # factored (net upward)

    # ── Critical overhangs ─────────────────────────────────────────────────────
    a_L = (L - col_D_mm/1000) / 2
    a_B = (B - col_b_mm/1000) / 2

    # ── Bending moments at column face ─────────────────────────────────────────
    Mu_L = qu * B * a_L**2 / 2   # kN·m in L direction
    Mu_B = qu * L * a_B**2 / 2

    # ── Reinforcement design ───────────────────────────────────────────────────
    Ast_L = _ast_req(Mu_L/B, d, fck, fy)   # mm²/m
    Ast_B = _ast_req(Mu_B/L, d, fck, fy)
    ab    = math.pi * bar_dia_mm**2 / 4
    sp_L  = max(75.0, math.floor(min(1000*ab/Ast_L, 3*d, 450)/10)*10)
    sp_B  = max(75.0, math.floor(min(1000*ab/Ast_B, 3*d, 450)/10)*10)
    ast_L_prov = ab*1000/sp_L
    ast_B_prov = ab*1000/sp_B

    # ── One-way shear ──────────────────────────────────────────────────────────
    crit_L = max(0.0, a_L - d/1000)
    crit_B = max(0.0, a_B - d/1000)
    Vu_L   = qu * B * crit_L
    Vu_B   = qu * L * crit_B
    tv_L   = Vu_L*1000/(B*1000*d) if d>0 else 0
    tv_B   = Vu_B*1000/(L*1000*d) if d>0 else 0
    pt_L   = min(100*ast_L_prov/(1000*d), 3.0)
    pt_B   = min(100*ast_B_prov/(1000*d), 3.0)
    k_fac  = 1.3 if D_f<=150 else max(1.0,1.3-(D_f-150)*0.3/150) if D_f<=300 else 1.0
    tc_L   = _tc(pt_L, fck); tc_B = _tc(pt_B, fck)
    one_way_ok = (tv_L <= k_fac*tc_L) and (tv_B <= k_fac*tc_B)
    if not one_way_ok:
        notes.append(f"⚠ One-way shear fails. Increase depth D_f.")
    else:
        notes.append(f"One-way shear OK ✓ (τv_L={tv_L:.3f}, τv_B={tv_B:.3f} MPa)")

    # ── Punching shear ─────────────────────────────────────────────────────────
    pL  = col_D_mm + d; pB = col_b_mm + d
    b0  = 2*(pL+pB)
    Aex = (pL/1000)*(pB/1000)
    Vp  = max(0.0, qu*(A - Aex))
    tv_p = Vp*1000/(b0*d) if (b0*d)>0 else 0
    tc_p = 0.25*math.sqrt(fck)
    punch_ok = tv_p <= tc_p
    if not punch_ok:
        notes.append(f"⚠ Punching shear τv={tv_p:.3f} > τc={tc_p:.3f} MPa. Increase D_f.")
    else:
        notes.append(f"Punching shear OK ✓ (τv={tv_p:.3f} ≤ {tc_p:.3f} MPa)")

    # ── Development length ─────────────────────────────────────────────────────
    Ld    = _ld(bar_dia_mm, fy, fck)
    av_L  = a_L*1000 - cover_mm
    av_B  = a_B*1000 - cover_mm
    dev_ok = (av_L >= Ld) and (av_B >= Ld)
    notes.append(
        f"Development Ld={Ld:.0f} mm; available L={av_L:.0f}mm, B={av_B:.0f}mm "
        f"({'✓' if dev_ok else '⚠ Insufficient'})")

    # ── Kern check summary ─────────────────────────────────────────────────────
    kern_ok_L = ex <= L/6
    kern_ok_B = ey <= B/6
    if kern_ok_L and kern_ok_B:
        notes.append(
            f"Within kern: ex={ex:.3f}≤{L/6:.3f}m, ey={ey:.3f}≤{B/6:.3f}m — "
            "uniform compression throughout. No tension on soil.")
    else:
        notes.append(
            f"Outside kern: Partial uplift. ex={ex:.3f}m vs {L/6:.3f}m limit. "
            "Effective area design applied.")

    return {
        "type":             "eccentric",
        "L_mm":             round(L*1000),
        "B_mm":             round(B*1000),
        "D_mm":             D_f,
        "d_mm":             round(d),
        "A_m2":             round(A, 3),
        "ex_m":             round(ex, 4),
        "ey_m":             round(ey, 4),
        "q_avg_kPa":        round(q_c, 2),
        "q_max_kPa":        round(q_max, 2),
        "q_min_kPa":        round(q_min, 2),
        "tension_zone":     tension,
        "SBC_used_kPa":     sbc_use,
        "pressure_ok":      pressure_ok,
        "kern_ok":          kern_ok_L and kern_ok_B,
        "qu_kPa":           round(qu, 2),
        "Mu_L_kNm":         round(Mu_L, 2),
        "Mu_B_kNm":         round(Mu_B, 2),
        "Ast_L_per_m_mm2":  round(Ast_L, 1),
        "Ast_B_per_m_mm2":  round(Ast_B, 1),
        "sp_L_mm":          sp_L,
        "sp_B_mm":          sp_B,
        "ast_L_prov_mm2m":  round(ast_L_prov, 1),
        "ast_B_prov_mm2m":  round(ast_B_prov, 1),
        "bar_dia_mm":       bar_dia_mm,
        "tau_v_L":          round(tv_L, 3),
        "tau_c_L":          round(k_fac*tc_L, 3),
        "tau_v_B":          round(tv_B, 3),
        "tau_c_B":          round(k_fac*tc_B, 3),
        "one_way_ok":       one_way_ok,
        "tau_v_punch":      round(tv_p, 3),
        "tau_c_punch":      round(tc_p, 3),
        "punch_ok":         punch_ok,
        "Ld_mm":            round(Ld),
        "dev_ok":           dev_ok,
        "notes":            notes,
    }


def design_combined_footing(
    col1_b_mm: float, col1_D_mm: float,
    col2_b_mm: float, col2_D_mm: float,
    P1_kN:     float, P2_kN: float,
    spacing_m: float,          # centre-to-centre of columns (m)
    SBC_kPa:   float = 150.0,
    fck:       float = 20.0,
    fy:        float = 415.0,
    cover_mm:  float = 50.0,
    bar_dia_mm:float = 16.0,
    footing_D_mm: float | None = None,
    seismic:   bool = False,
) -> dict:
    """
    Rectangular combined footing for two columns (IS 456:2000 §34 principles).
    Centroid of footing aligned with resultant column load.
    """
    notes: list[str] = []
    sbc_use = SBC_kPa * (1.5 if seismic else 1.0)
    if seismic:
        notes.append(f"Seismic: SBC × 1.5 = {sbc_use:.0f} kN/m² (NBC 105:2025 §3.8).")

    P_total = P1_kN + P2_kN

    # ── Resultant location from col1 centre ────────────────────────────────────
    x_bar = P2_kN * spacing_m / P_total   # m from col1

    # ── Footing length (symmetric about resultant for uniform pressure) ────────
    # L must extend equal distances each side of resultant
    # But constrained by column positions:
    # col1 edge: 0.5*col1_D/1000 + min_overhang
    # col2 edge: spacing + 0.5*col2_D/1000 + min_overhang
    min_overhang = 0.10  # m minimum projection beyond column face
    x_col1_edge = col1_D_mm/2000 + min_overhang   # m from col1 CL
    x_col2_edge = spacing_m + col2_D_mm/2000 + min_overhang

    # Symmetric about resultant
    x_left  = max(x_bar, x_col1_edge)
    x_right = max(spacing_m + col2_D_mm/2000 + min_overhang - x_bar, col2_D_mm/2000 + min_overhang)
    # But we want x_left ≈ x_right for uniform pressure → adjust
    L = x_left + x_right

    # Breadth for required area
    A_req = P_total * 1.10 / sbc_use   # +10% for self weight
    B = math.ceil(A_req / L * 10) / 10
    B = max(B, max(col1_b_mm, col2_b_mm)/1000 + 0.4)
    A = L * B

    notes.append(
        f"Combined footing: L={L*1000:.0f}mm, B={B*1000:.0f}mm. "
        f"Resultant at {x_bar*1000:.0f}mm from col1. "
        f"x_left={x_left*1000:.0f}mm, x_right={x_right*1000:.0f}mm."
    )

    # ── Pressure (uniform, resultant centred) ──────────────────────────────────
    q_net = P_total / A
    if q_net > sbc_use:
        notes.append(f"⚠ q={q_net:.1f} > SBC={sbc_use:.0f} kN/m². Increase plan.")
    else:
        notes.append(f"Soil pressure: q = {q_net:.2f} kN/m² ≤ {sbc_use:.0f} kN/m²  ✓")

    # ── Depth ─────────────────────────────────────────────────────────────────
    D_f = footing_D_mm or max(300.0, math.ceil(B*1000/8/50)*50)
    D_f = max(D_f, 300.0)
    d   = D_f - cover_mm - bar_dia_mm

    # ── Shear force & bending moment diagram (per metre width B) ──────────────
    # Factored upward pressure (per m width)
    qu_per_m = 1.5 * q_net * B   # kN/m total
    P1f = 1.5 * P1_kN; P2f = 1.5 * P2_kN

    # Maximum sagging moment (between columns, under resultant)
    # For simplicity: treat as simply-supported beam with two point loads
    # Reactions from upward distributed load:
    # RA (at x=0) = qu_per_m*L/2 - P2f*(spacing_m)/(L) ... actually uniform q
    # Reaction at left end: RA = qu_per_m*(L**2/2) / L = qu_per_m*L/2
    # BUT the column loads create hogging at columns.
    # Using influence lines:
    q_factored = 1.5 * q_net   # kN/m² factored
    w = q_factored * B         # kN/m strip (full width)

    # Hogging at col1 (from left): M_col1 = -w*x_left²/2
    M_hog1 = -w * x_left**2 / 2
    # Hogging at col2 (from right): M_col2 = -w*x_right²/2
    M_hog2 = -w * x_right**2 / 2
    # Sagging between columns (approximate): midspan between columns
    x_mid   = x_left + spacing_m/2
    M_sag   = w*x_mid**2/2 - P1f*max(0,x_mid-x_left)
    M_sag   = max(abs(M_sag), abs(M_hog1)*0.3)   # practical lower bound
    # Design for max of hogging and sagging
    Mu_design = max(abs(M_hog1), abs(M_hog2), M_sag)

    # ── Reinforcement ─────────────────────────────────────────────────────────
    Ast_long = _ast_req(Mu_design/B, d, fck, fy)   # mm²/m in longitudinal dir
    Ast_trans = _ast_req(q_factored*(B/2)**2/2, d, fck, fy)  # transverse cantilever
    ab = math.pi*bar_dia_mm**2/4
    sp_long  = max(75.0, math.floor(min(1000*ab/Ast_long,  3*d,450)/10)*10)
    sp_trans = max(75.0, math.floor(min(1000*ab/Ast_trans, 3*d,450)/10)*10)
    ast_long_prov  = ab*1000/sp_long
    ast_trans_prov = ab*1000/sp_trans

    # ── Punching at each column ────────────────────────────────────────────────
    def _punch(col_b, col_D, Pf):
        pL = col_D + d; pB = col_b + d; b0_p = 2*(pL+pB)
        A_exc = (pL/1000)*(pB/1000)
        Vp  = max(0, Pf - q_factored*A_exc)
        tv  = Vp*1000/(b0_p*d) if b0_p*d>0 else 0
        tc  = 0.25*math.sqrt(fck)
        return round(tv,3), round(tc,3), tv<=tc

    tv1,tc1,p1ok = _punch(col1_b_mm, col1_D_mm, P1f)
    tv2,tc2,p2ok = _punch(col2_b_mm, col2_D_mm, P2f)
    notes.append(
        f"Punching col1: τv={tv1:.3f}{'≤' if p1ok else '>'}τc={tc1:.3f}  "
        f"{'✓' if p1ok else '⚠'}")
    notes.append(
        f"Punching col2: τv={tv2:.3f}{'≤' if p2ok else '>'}τc={tc2:.3f}  "
        f"{'✓' if p2ok else '⚠'}")

    # ── Development length ─────────────────────────────────────────────────────
    Ld     = _ld(bar_dia_mm, fy, fck)
    av_end = max(x_left, x_right)*1000 - cover_mm
    dev_ok = av_end >= Ld
    notes.append(f"Development Ld={Ld:.0f}mm; available={av_end:.0f}mm {'✓' if dev_ok else '⚠'}")

    return {
        "type":              "combined",
        "L_mm":              round(L*1000),
        "B_mm":              round(B*1000),
        "D_mm":              D_f,
        "d_mm":              round(d),
        "A_m2":              round(A, 3),
        "q_net_kPa":         round(q_net, 2),
        "SBC_used_kPa":      sbc_use,
        "pressure_ok":       q_net <= sbc_use,
        "x_resultant_m":     round(x_bar, 3),
        "x_left_m":          round(x_left, 3),
        "x_right_m":         round(x_right, 3),
        "Mu_design_kNm":     round(Mu_design, 2),
        "M_hog1_kNm":        round(abs(M_hog1), 2),
        "M_hog2_kNm":        round(abs(M_hog2), 2),
        "M_sag_kNm":         round(M_sag, 2),
        "Ast_long_per_m_mm2":round(Ast_long, 1),
        "Ast_trans_per_m_mm2":round(Ast_trans, 1),
        "sp_long_mm":        sp_long,
        "sp_trans_mm":       sp_trans,
        "ast_long_prov":     round(ast_long_prov, 1),
        "ast_trans_prov":    round(ast_trans_prov, 1),
        "bar_dia_mm":        bar_dia_mm,
        "punch_col1_ok":     p1ok,
        "punch_col2_ok":     p2ok,
        "tau_v_punch_c1":    tv1,
        "tau_v_punch_c2":    tv2,
        "tau_c_punch":       tc1,
        "Ld_mm":             round(Ld),
        "dev_ok":            dev_ok,
        "notes":             notes,
    }
