"""
core/beam_engine.py — IS 456:2000 Complete Beam Design Engine
=============================================================
Priority: IS 456:2000 throughout. NBC 105:2025 §3.6 load combinations
applied upstream by caller; this engine works with factored Mu/Vu.

Covers:
  §23.2   Effective span; deflection with kt / kc / kf
  §26.3   Slab/beam effective width (T-beam)
  §26.5.1 Longitudinal reinforcement (min, max, side face)
  §38–39  Flexural design — singly and doubly reinforced
  §40     Shear design
  §41     Torsion combined with shear and flexure
  §26.2.1 Development length
  §35.3   Crack width (service stress guidance)
  Annex G Doubly-reinforced sections
  Annex B T-beam effective flange width
"""
from __future__ import annotations
import math

_TAU_C_TABLE = [
    (0.15,0.28),(0.25,0.36),(0.50,0.48),(0.75,0.56),(1.00,0.62),
    (1.25,0.67),(1.50,0.72),(1.75,0.75),(2.00,0.79),(2.25,0.81),
    (2.50,0.82),(3.00,0.82),
]
_KT_FS  = [120,145,190,240,290]
_KT_PT  = [0.2,0.4,0.6,0.8,1.0,1.4,2.0,2.8]
_KT_VALS = [
    [1.90,1.55,1.38,1.25,1.18,1.06,0.95,0.86],
    [1.70,1.40,1.25,1.15,1.08,1.00,0.90,0.82],
    [1.40,1.18,1.05,0.98,0.94,0.88,0.82,0.77],
    [1.15,0.98,0.89,0.83,0.80,0.75,0.70,0.66],
    [0.95,0.82,0.75,0.71,0.68,0.64,0.60,0.56],
]
_TAU_BD = {20:1.2, 25:1.4, 30:1.5, 35:1.7, 40:1.9}


def _interp(x, xs, ys):
    if x<=xs[0]: return ys[0]
    if x>=xs[-1]:return ys[-1]
    for i in range(len(xs)-1):
        if xs[i]<=x<=xs[i+1]:
            return ys[i]+(ys[i+1]-ys[i])*(x-xs[i])/(xs[i+1]-xs[i])
    return ys[-1]


def _tau_c(pt_pct: float, fck: float) -> float:
    """IS 456 Table 19 — design shear strength."""
    base = _interp(pt_pct, [p for p,_ in _TAU_C_TABLE], [t for _,t in _TAU_C_TABLE])
    fac  = min((fck/20)**0.5, 1.25) if fck > 20 else 1.0
    return base * fac


def _xu_d_max(fy: float) -> float:
    """Max neutral axis depth ratio IS 456 Table F."""
    if fy <= 250: return 0.53
    if fy <= 415: return 0.48
    return 0.46


def _t_beam_bf(b_w: float, l_eff: float, b_f_user: float | None,
               Df_mm: float, beam_type: str) -> float:
    """
    IS 456 §26.3 / Annex B — effective flange width.
    beam_type: 'T' (flange on both sides) or 'L' (flange on one side).
    """
    if b_f_user:
        return b_f_user
    if beam_type == "T":
        bf = min(l_eff/6 + b_w + 12*Df_mm, b_w + l_eff/3)
    else:  # L-beam
        bf = min(l_eff/12 + b_w + 6*Df_mm,  b_w + l_eff/4)
    return bf


def design_beam_section(
    b_mm:             float,
    D_mm:             float,
    cover_mm:         float,
    main_bar_dia_mm:  float,
    fck:              float,
    fy:               float,
    Mu_kNm:           float,
    Vu_kN:            float,
    Tu_kNm:           float = 0.0,
    span_m:           float = 0.0,
    support_type:     str   = "Simply Supported",
    wdl_kNm:          float = 0.0,
    wll_kNm:          float = 0.0,
    spacing_round_base: int = 5,
    user_spacing_mm:  float | None = None,
    user_no_of_bars:  int   | None = None,
    allow_doubly:     bool  = True,
    comp_bar_dia_mm:  float = 16.0,
    d_prime_mm:       float | None = None,
    # T-beam params
    beam_type:        str   = "Rectangular",   # "Rectangular" | "T" | "L"
    Df_mm:            float = 0.0,              # flange thickness (mm) for T/L
    bf_mm_user:       float | None = None,      # user override effective width
    stir_dia_mm:      float = 8.0,              # stirrup diameter
    stir_legs:        int   = 2,                # stirrup legs
) -> dict:
    """
    Full IS 456:2000 beam design.
    Returns dict; all values in consistent units (mm, kN, MPa, kN·m).
    """
    notes: list[str] = []
    Es = 2e5   # N/mm²

    # ── Effective depth ───────────────────────────────────────────────────────
    d = D_mm - cover_mm - main_bar_dia_mm / 2.0
    if d <= 0:
        raise ValueError(f"Effective depth ≤ 0 (d={d:.1f} mm). Check cover ({cover_mm}) and bar Ø ({main_bar_dia_mm}).")

    # ── T-beam effective width ────────────────────────────────────────────────
    l_eff = span_m * 1000 if span_m > 0 else D_mm * 20   # fallback
    bf    = _t_beam_bf(b_mm, l_eff, bf_mm_user, Df_mm, beam_type)
    if beam_type != "Rectangular":
        notes.append(
            f"T/L-beam: bf={bf:.0f} mm, bw={b_mm:.0f} mm, Df={Df_mm:.0f} mm "
            f"(IS 456 §26.3 / Annex B)."
        )

    # ── xu_max ────────────────────────────────────────────────────────────────
    xu_d = _xu_d_max(fy)
    xu_max = xu_d * d

    # ── Torsion: equivalent shear and moment (IS 456 §41.3) ─────────────────
    if Tu_kNm > 0:
        Ve = Vu_kN + 1.6 * Tu_kNm / (b_mm / 1000)    # equivalent shear (kN)
        Me = Mu_kNm + Tu_kNm * (1.0 + D_mm / b_mm) / 1.7  # equiv moment (kN·m)
        notes.append(
            f"Torsion Tu={Tu_kNm:.2f} kN·m → Ve={Ve:.2f} kN, Me={Me:.2f} kN·m "
            "(IS 456 §41.3). Closed stirrups and side-face bars required."
        )
    else:
        Ve = Vu_kN
        Me = Mu_kNm

    Mu_design = Me
    Vu_design = Ve

    # ── Limiting moment (singly) ──────────────────────────────────────────────
    if beam_type != "Rectangular" and Df_mm > 0:
        # T-beam limiting moment: includes flange contribution
        # IS 456 §38.1 for flanged beams (simplified: assume NA in flange)
        xu_flange = Df_mm
        Mu_flange_Nm = (0.36*fck*bf*xu_flange*(d-0.42*xu_flange)
                        + 0.45*fck*(bf-b_mm)*Df_mm*(d-Df_mm/2))
        Mu_lim = min(Mu_flange_Nm, 0.36*fck*b_mm*xu_max*(d-0.42*xu_max)) / 1e6
        # Use full T-beam capacity if flange is wide enough
        Mu_lim = Mu_flange_Nm / 1e6
    else:
        Mu_lim = 0.36 * fck * b_mm * xu_max * (d - 0.42 * xu_max) / 1e6

    # ── Flexural design ───────────────────────────────────────────────────────
    doubly_res = None
    Mu_Nmm     = Mu_design * 1e6
    b_eff      = bf if beam_type != "Rectangular" else b_mm  # for NA calc

    if Mu_design <= Mu_lim:
        # Singly reinforced
        a_q = -0.36*0.42*fck*b_eff
        b_q =  0.36*fck*b_eff*d
        c_q = -Mu_Nmm
        disc = b_q**2 - 4*a_q*c_q
        if disc < 0:
            Ast_req = (0.85/fy)*b_mm*d
        else:
            xu_cands = [x for x in ((-b_q+math.sqrt(disc))/(2*a_q),
                                     (-b_q-math.sqrt(disc))/(2*a_q))
                        if 0 < x <= xu_max]
            xu = min(xu_cands) if xu_cands else xu_max
            z  = d - 0.42*xu
            Ast_req = Mu_Nmm / (0.87*fy*z) if z > 0 else 0.0
    else:
        # Doubly reinforced (IS 456 Annex G)
        if not allow_doubly:
            notes.append(
                "⚠ Mu > Mu,lim and doubly-reinforced is disabled. Increase section depth."
            )
            Ast_req = 0.0
        else:
            notes.append("ℹ Mu > Mu,lim → doubly-reinforced section (IS 456 Annex G).")
            dp_     = d_prime_mm if d_prime_mm else (cover_mm + main_bar_dia_mm / 2.0)
            # Limit d' to ≤ 0.2d (practical)
            dp_     = min(dp_, 0.2 * d)
            eps_y   = 0.87 * fy / Es + 0.002
            eps_sc  = 0.0035 * (xu_max - dp_) / max(xu_max, 1e-9)
            fsc     = min(0.87*fy, max(eps_sc * Es, 0.0))  # always cap at design yield strength
            notes.append(
                f"Comp. bar: εsc={eps_sc:.4f} {'≥' if eps_sc>=eps_y else '<'} "
                f"εy={eps_y:.4f} → fsc={fsc:.0f} MPa (d'={dp_:.1f} mm)."
            )
            Mu_extra_Nm = Mu_Nmm - Mu_lim * 1e6
            lever       = d - dp_
            if lever <= 0:
                raise ValueError(f"d'={dp_:.1f} ≥ d={d:.1f}. Check section geometry.")
            Asc = Mu_extra_Nm / max((fsc - 0.45*fck) * lever, 1e-9)
            # Ast1 for balanced (limiting) moment
            Ast1 = (Mu_lim*1e6) / (0.87*fy*(d - 0.42*xu_max)) if (d-0.42*xu_max)>0 else 0
            # Ast2 to balance compression steel
            Ast2 = Asc * (fsc - 0.45*fck) / max(0.87*fy, 1e-9)
            Ast_req = Ast1 + Ast2

            area_comp = math.pi * comp_bar_dia_mm**2 / 4.0
            n_comp    = max(2, math.ceil(Asc / area_comp))
            doubly_res = {
                "Asc_req_mm2":  round(Asc, 2),
                "Asc_prov_mm2": round(area_comp * n_comp, 2),
                "no_comp_bars": n_comp,
                "comp_bar_dia": comp_bar_dia_mm,
                "fsc_MPa":      round(fsc, 1),
                "eps_sc":       round(eps_sc, 5),
                "Ast1_mm2":     round(Ast1, 2),
                "Ast2_mm2":     round(Ast2, 2),
                "d_prime_mm":   round(dp_, 1),
            }

    # ── Min / Max steel (IS 456 §26.5.1) ─────────────────────────────────────
    Ast_min = (0.85 / fy) * b_mm * d    # §26.5.1.1
    Ast_max = 0.04 * b_mm * D_mm        # §26.5.1.1
    Ast_design = max(Ast_req, Ast_min)

    # ── Side face reinforcement (IS 456 §26.5.1.3) ────────────────────────────
    if D_mm > 750:
        Asf = 0.1 * (D_mm - 750) * b_mm / 100   # mm² per face (0.1% of web area)
        notes.append(
            f"Side-face reinforcement required (D={D_mm:.0f} > 750 mm): "
            f"≥ {Asf:.0f} mm² each face (IS 456 §26.5.1.3). "
            f"Use Ø{int(main_bar_dia_mm/2):.0f}–{int(main_bar_dia_mm/1.5):.0f} mm bars "
            f"spaced ≤ 300 mm."
        )

    # ── Bar layout ────────────────────────────────────────────────────────────
    area_bar = math.pi * main_bar_dia_mm**2 / 4.0
    if user_no_of_bars and user_no_of_bars > 0:
        no_bars = user_no_of_bars
    else:
        no_bars = max(2, math.ceil(Ast_design / area_bar))

    if user_spacing_mm and user_spacing_mm > 0:
        spacing_prov = user_spacing_mm
        no_bars = max(1, int((b_mm - 2*cover_mm + spacing_prov)
                             / (main_bar_dia_mm + spacing_prov)))
    else:
        clear_w = b_mm - 2*cover_mm - main_bar_dia_mm * no_bars
        raw_sp  = clear_w / (no_bars - 1) if no_bars > 1 else clear_w
        spacing_prov = max(spacing_round_base,
                           round(raw_sp / spacing_round_base) * spacing_round_base
                           if raw_sp > 0 else spacing_round_base)

    # Min clear spacing IS 456 §26.3.2: ≥ max(bar dia, 25mm, 5/3 × agg size)
    min_clear = max(main_bar_dia_mm, 25.0)
    if spacing_prov < min_clear:
        notes.append(
            f"⚠ Bar spacing {spacing_prov:.0f} mm < {min_clear:.0f} mm min clear "
            f"(IS 456 §26.3.2). Increase spacing or use larger bars."
        )

    Ast_prov = area_bar * no_bars

    # Max bar spacing IS 456 §26.3.3 for tension zone: ≤ min(300mm, d)
    max_sp_tens = min(300.0, d)
    if spacing_prov > max_sp_tens:
        notes.append(
            f"⚠ Bar spacing {spacing_prov:.0f} > {max_sp_tens:.0f} mm max (IS 456 §26.3.3)."
        )

    # ── Shear design (IS 456 §40) ─────────────────────────────────────────────
    tau_v   = Vu_design * 1000 / (b_mm * d) if d > 0 else 0
    pt      = min(100 * Ast_prov / (b_mm * d), 3.0)
    tc      = _tau_c(pt, fck)
    # k factor IS 456 §40.2.1.1 (for D < 300mm)
    k_fac   = (1.3 if D_mm <= 150
               else max(1.0, 1.3 - (D_mm-150)*0.3/150) if D_mm <= 300
               else 1.0)
    tau_c_max = 0.62 * math.sqrt(fck)   # IS 456 Table 20

    Asv   = stir_legs * math.pi * stir_dia_mm**2 / 4.0

    if tau_v > tau_c_max:
        shear_status = "Revise Section"; Sv_mm = None
        notes.append(
            f"⚠ τv={tau_v:.3f} > τc,max={tau_c_max:.3f} MPa (IS 456 Table 20). "
            "Increase section dimensions."
        )
    elif tau_v > k_fac * tc:
        # Shear reinforcement required IS 456 §40.4
        Vus    = (tau_v - tc) * b_mm * d / 1000.0   # kN
        fy_str = min(fy, 500)   # IS 456 cap for stirrups
        Sv_calc = (0.87 * fy_str * Asv * d) / (Vus * 1000) if Vus > 0 else 300
        Sv_min  = (Asv * fy_str * 0.87) / (0.4 * b_mm)   # IS 456 §26.5.1.6
        Sv      = max(75.0, min(Sv_calc, Sv_min, 0.75*d, 300.0))
        Sv_mm   = max(spacing_round_base, math.floor(Sv/spacing_round_base)*spacing_round_base)
        shear_status = "Stirrups Required"
        notes.append(
            f"Shear: τv={tau_v:.3f} > k·τc={k_fac*tc:.3f} MPa. "
            f"Provide Ø{int(stir_dia_mm)} {stir_legs}-leg @ {Sv_mm} mm c/c "
            f"(IS 456 §40.4)."
        )
    else:
        # Minimum stirrups IS 456 §26.5.1.6
        fy_str = min(fy, 500)
        Sv_min = (Asv * fy_str * 0.87) / (0.4 * b_mm)
        Sv     = max(75.0, min(Sv_min, 0.75*d, 300.0))
        Sv_mm  = max(spacing_round_base, math.floor(Sv/spacing_round_base)*spacing_round_base)
        shear_status = "Minimum Stirrups"
        notes.append(
            f"Shear OK: τv={tau_v:.3f} ≤ k·τc={k_fac*tc:.3f} MPa. "
            f"Minimum Ø{int(stir_dia_mm)} {stir_legs}-leg @ {Sv_mm} mm c/c "
            f"(IS 456 §26.5.1.6)."
        )

    # ── Torsion: additional link area (IS 456 §41.4) ─────────────────────────
    Sv_tors_note = ""
    if Tu_kNm > 0 and Sv_mm:
        b1 = b_mm - 2*cover_mm - stir_dia_mm
        d1 = D_mm - 2*cover_mm - stir_dia_mm
        fy_str = min(fy, 500)
        Asv_t = (Tu_kNm * 1e6 * Sv_mm) / (b1 * d1 * 0.87 * fy_str) if (b1*d1) > 0 else 0
        n_tors_legs = math.ceil(Asv_t / (math.pi * stir_dia_mm**2 / 4.0))
        Sv_tors_note = (
            f"Torsion: additional Asv/leg={Asv_t:.1f} mm² per link. "
            f"Use {max(stir_legs, n_tors_legs)}-leg closed stirrups (IS 456 §41.4). "
            f"Side-face bars: Ø{int(main_bar_dia_mm*0.7):.0f}–{int(main_bar_dia_mm*0.85):.0f} mm "
            f"@ 300 mm each face."
        )
        if Sv_tors_note:
            notes.append(Sv_tors_note)

    # ── Deflection check (IS 456 §23.2) ──────────────────────────────────────
    defl_result = None
    if span_m > 0:
        ld_basic = {
            "Simply Supported": 20, "Cantilever": 7,
            "Fixed-Fixed": 26, "Propped Cantilever": 20,
            "Continuous": 26,
        }.get(support_type, 20)

        # Service steel stress fs: IS 456 §23.2 (Cl. note 1)
        Ast_serv  = max(Ast_req, Ast_min)
        fs_serv   = min(0.58 * fy * (Ast_serv / max(Ast_prov, 1e-9)), 0.58 * fy)
        # kt from IS 456 Figure 4
        pt_serv   = min(100 * Ast_prov / (b_mm * d), 2.8)
        fs_cl     = max(120.0, min(290.0, fs_serv))
        fs_idx    = min(range(len(_KT_FS)), key=lambda i: abs(_KT_FS[i] - fs_cl))
        kt        = min(_interp(pt_serv, _KT_PT, _KT_VALS[fs_idx]), 2.0)
        # kc (compression steel factor IS 456 §23.2)
        kc = 1.0
        if doubly_res:
            pt_comp = 100 * doubly_res["Asc_prov_mm2"] / (b_mm * d)
            kc      = min(1.0 + pt_comp / (3.0 + pt_comp), 1.5)
        # kf (flange factor IS 456 §23.2 note 2)
        kf = 0.8 if beam_type != "Rectangular" else 1.0
        ld_allow  = ld_basic * kt * kc * kf
        ld_prov   = span_m * 1000 / d
        defl_ok   = ld_prov <= ld_allow
        defl_result = {
            "ld_basic":    ld_basic,
            "fs_serv":     round(fs_serv, 1),
            "kt":          round(kt, 3),
            "kc":          round(kc, 3),
            "kf":          round(kf, 2),
            "ld_allow":    round(ld_allow, 2),
            "ld_prov":     round(ld_prov, 2),
            "ok":          defl_ok,
        }
        if not defl_ok:
            d_need = math.ceil(span_m * 1000 / ld_allow)
            notes.append(
                f"⚠ Deflection: L/d={ld_prov:.1f} > {ld_allow:.1f}. "
                f"Increase d to ≥ {d_need} mm (D≈{d_need+int(cover_mm+main_bar_dia_mm/2)+5} mm) "
                f"(IS 456 §23.2, kt={kt:.2f}, kc={kc:.2f}, kf={kf:.2f})."
            )
        else:
            notes.append(
                f"Deflection: L/d={ld_prov:.1f} ≤ {ld_allow:.1f} "
                f"(basic={ld_basic}, kt={kt:.2f}, kc={kc:.2f}, kf={kf:.2f})  ✓"
            )

    # ── Development length (IS 456 §26.2.1) ──────────────────────────────────
    tau_bd = _TAU_BD.get(int(fck), 1.2)
    Ld_mm  = (0.87 * fy * main_bar_dia_mm) / (4.0 * tau_bd)
    notes.append(
        f"Development length: Ld = {Ld_mm:.0f} mm "
        f"(Ø{main_bar_dia_mm:.0f}, fck={fck:.0f}, fy={fy:.0f}) — IS 456 §26.2.1."
    )

    # ── Service stress / crack width guidance (IS 456 §35.3) ─────────────────
    if span_m > 0 and (wdl_kNm > 0 or wll_kNm > 0):
        M_serv = (wdl_kNm + wll_kNm) * span_m**2 / 8.0   # approx for SS
        z_serv = 0.9 * d
        fs_act = M_serv * 1e6 / (Ast_prov * z_serv) if Ast_prov > 0 else 0
        crack_ok = fs_act < 240.0
        notes.append(
            f"Service steel stress ≈ {fs_act:.0f} MPa "
            f"({'< 240 MPa — crack width likely acceptable' if crack_ok else '> 240 MPa — calculate crack width per IS 456 Annex F'}) "
            "(IS 456 §35.3)."
        )

    # ── Summary ───────────────────────────────────────────────────────────────
    notes.append(
        f"Section: {b_mm:.0f}×{D_mm:.0f} mm, d={d:.1f} mm. "
        f"Ast,req={Ast_req:.1f} mm², Ast,min={Ast_min:.1f} mm². "
        f"Provided: {no_bars}×Ø{main_bar_dia_mm:.0f} = {Ast_prov:.1f} mm²."
    )
    if Ast_prov > Ast_max:
        notes.append(f"⚠ Ast,prov={Ast_prov:.0f} > Ast,max={Ast_max:.0f} mm² (4%bD). Increase section.")

    return {
        # Geometry
        "d_eff_mm":       round(d, 2),
        "bf_mm":          round(bf, 0),
        # Design loads (after torsion equivalence)
        "Mu_design_kNm":  round(Mu_design, 3),
        "Vu_design_kN":   round(Vu_design, 3),
        # Flexure
        "Mu_lim_kNm":     round(Mu_lim, 3),
        "is_doubly":      doubly_res is not None,
        "doubly":         doubly_res,
        # Reinforcement
        "Ast_req_mm2":    round(Ast_req, 2),
        "Ast_min_mm2":    round(Ast_min, 2),
        "Ast_max_mm2":    round(Ast_max, 2),
        "no_of_bars":     no_bars,
        "spacing_mm":     round(spacing_prov, 1),
        "Ast_prov_mm2":   round(Ast_prov, 2),
        # Shear
        "shear": {
            "tau_v":   round(tau_v, 3),
            "tau_c":   round(k_fac * tc, 3),
            "tau_c_max": round(tau_c_max, 3),
            "status":  shear_status,
            "Sv_mm":   Sv_mm,
            "stir_dia": stir_dia_mm,
            "stir_legs": stir_legs,
        },
        # Development length
        "Ld_mm": round(Ld_mm, 0),
        # Deflection
        "deflection": defl_result,
        "notes": notes,
    }
