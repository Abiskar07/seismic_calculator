import math
from constants.is456_data import DEFLECTION_KT_DATA

def interp(x, xs, ys):
    if x <= xs[0]: return ys[0]
    if x >= xs[-1]: return ys[-1]
    for i in range(len(xs)-1):
        if xs[i] <= x <= xs[i+1]:
            return ys[i] + (ys[i+1]-ys[i]) * (x - xs[i]) / (xs[i+1]-xs[i])
    return ys[-1]

def verify_slab(lx, ly, D, cover, dia, fy, fck, ll, support_condition):
    print(f"=== Verification for Slab ===")
    print(f"Lx: {lx} m, Ly: {ly} m")
    print(f"D: {D} mm, cover: {cover} mm, dia: {dia} mm")
    print(f"fy: {fy} MPa, fck: {fck} MPa, LL: {ll} kN/m2")
    
    # 1. Deflection check
    d = D - cover - dia / 2.0
    print(f"Effective depth d: {d} mm")
    
    basic = 20 if support_condition != "Four edges discontinuous" else 20 # Simplified for test
    # If simply supported, 20. If continuous, 26. Let's assume simply supported for worst case.
    
    # Let's assume some Ast required and provided
    req_ast = 200.0
    prov_ast = 250.0
    
    fs = 0.58 * fy * (req_ast / prov_ast)
    pt = 100 * prov_ast / (1000 * d)
    
    print(f"Calculated fs: {fs:.2f} MPa, pt: {pt:.2f}%")
    
    closest_fs = min(DEFLECTION_KT_DATA.keys(), key=lambda k: abs(k-fs))
    xs = list(DEFLECTION_KT_DATA[closest_fs].keys())
    ys = list(DEFLECTION_KT_DATA[closest_fs].values())
    kt = interp(pt, xs, ys)
    
    print(f"kt modification factor: {kt:.3f} (using closest fs curve {closest_fs})")
    
    ld_max = basic * kt
    ld_prov = (lx * 1000) / d
    
    print(f"L/d max: {ld_max:.2f}")
    print(f"L/d prov: {ld_prov:.2f}")
    
    if ld_prov <= ld_max:
        print("Deflection: OK")
    else:
        print("Deflection: REVISE")
        
    print("\n=== Torsional Reinforcement Check ===")
    TORSION_CORNERS = {
        "Interior panels": (0, 0),
        "One short edge discontinuous": (0, 2),
        "One long edge discontinuous": (0, 2),
        "Two adjacent edges discontinuous": (1, 2),
        "Two short edges discontinuous": (0, 4),
        "Two long edges discontinuous": (0, 4),
        "Three edges discontinuous (one long continuous)": (2, 2),
        "Three edges discontinuous (one short continuous)": (2, 2),
        "Four edges discontinuous": (4, 0),
    }
    
    ast_max = prov_ast # Simplifying for test
    c2, c1 = TORSION_CORNERS.get(support_condition, (0, 0))
    L_torsion = lx / 5.0
    
    if c2 > 0 or c1 > 0:
        print(f"Distance from edges: {L_torsion:.2f} m")
        if c2 > 0:
            ast_torsion = 0.75 * ast_max
            print(f"At {c2} corner(s) (two discontinuous edges): {ast_torsion:.1f} mm2/m in 4 layers")
        if c1 > 0:
            ast_torsion_half = 0.375 * ast_max
            print(f"At {c1} corner(s) (one discontinuous edge): {ast_torsion_half:.1f} mm2/m in 4 layers")
    else:
        print("Not required for interior panels.")
        
verify_slab(4.0, 5.0, 150, 20, 10, 415, 20, 4.0, "Two adjacent edges discontinuous")
