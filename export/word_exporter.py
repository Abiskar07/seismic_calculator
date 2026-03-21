"""
export/word_exporter.py — Professional Word Report Generator
============================================================
Generates .docx reports using docx-js (Node.js).
Two modes: 'summary' (1–2 pages) and 'detailed' (full manual with formulas).
"""
from __future__ import annotations
import json, os, subprocess, tempfile, textwrap
from datetime import datetime


def _run_node(js_code: str, output_path: str) -> None:
    """Write JS code to temp file, run with node, verify output."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".cjs", delete=False) as f:
        f.write(js_code)
        tmp = f.name
    try:
        result = subprocess.run(
            ["node", tmp],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Node.js failed:\n{result.stderr[:2000]}"
            )
    finally:
        os.unlink(tmp)


def generate_word_report(
    data: dict,
    output_path: str,
    mode: str = "detailed",  # "summary" | "detailed"
) -> str:
    """
    Generate a professional Word (.docx) structural engineering report.

    Parameters
    ----------
    data : dict  — collected from all tabs (see collect_report_data())
    output_path : str — where to write the .docx
    mode : "summary" | "detailed"
    """
    pi    = data.get("project_info", {})
    seism = data.get("seismic", {})
    beam  = data.get("beam", {})
    col   = data.get("column", {})
    fndg  = data.get("foundation", {})
    slab  = data.get("slab", {})

    # Escape strings for JS
    def j(v):
        if v is None: return '""'
        return json.dumps(str(v))

    def _row_js(cells, is_header=False, bg_color=None):
        """Generate a JS TableRow."""
        shading = f", shading: {{ fill: '{bg_color}', type: ShadingType.CLEAR }}" if bg_color else ""
        cell_strs = []
        for txt in cells:
            bold_prop = "bold: true, " if is_header else ""
            cell_strs.append(
                f"""new TableCell({{
                  borders: cellBorders, width: {{size:{9360//len(cells)}, type: WidthType.DXA}},
                  margins: {{top:80,bottom:80,left:120,right:120}}{shading},
                  children:[new Paragraph({{children:[new TextRun({{text:{j(txt)},{bold_prop}size:20,font:"Arial"}})]}})]
                }})"""
            )
        shade_row = ', shading: { val: "clear", fill: "DBEEF4" }' if is_header else ""
        return f"new TableRow({{cantSplit:true{shade_row}, children:[{','.join(cell_strs)}]}})"

    def _table_js(headers, rows, col_widths=None):
        n = len(headers)
        widths = col_widths or [9360 // n] * n
        header_row = _row_js(headers, is_header=True, bg_color="1F5C99")
        data_rows  = [_row_js(r) for r in rows]
        all_rows   = [header_row] + data_rows
        col_w_str  = ",".join(str(w) for w in widths)
        return (
            f"new Table({{"
            f"  width:{{size:9360,type:WidthType.DXA}},"
            f"  columnWidths:[{col_w_str}],"
            f"  rows:[{','.join(all_rows)}]"
            f"}})"
        )

    def _h1(text):
        return f"new Paragraph({{heading:HeadingLevel.HEADING_1,children:[new TextRun({{text:{j(text)},bold:true,size:32,font:'Arial',color:'1F5C99'}})]}})"

    def _h2(text):
        return f"new Paragraph({{heading:HeadingLevel.HEADING_2,children:[new TextRun({{text:{j(text)},bold:true,size:26,font:'Arial',color:'2E75B6'}})]}})"

    def _h3(text):
        return f"new Paragraph({{heading:HeadingLevel.HEADING_3,children:[new TextRun({{text:{j(text)},bold:true,size:22,font:'Arial',color:'31849B'}})]}})"

    def _p(text, italic=False, size=20, color="000000"):
        it = "italics:true," if italic else ""
        return f"new Paragraph({{children:[new TextRun({{text:{j(text)},{it}size:{size},font:'Arial',color:'{color}'}})]}})"

    def _formula_p(text):
        """Paragraph for formula display — monospace style."""
        return f"new Paragraph({{indent:{{left:720}},children:[new TextRun({{text:{j(text)},font:'Courier New',size:18,color:'1F5C99'}})]}})"

    def _clause_p(text):
        return f"new Paragraph({{indent:{{left:720}},children:[new TextRun({{text:{j(text)},italics:true,size:18,font:'Arial',color:'595959'}})]}})"

    def _blank():
        return 'new Paragraph({children:[new TextRun({text:"",size:20})]})'

    # ══════════════════════════════════════════════════════════════════════════
    # BUILD CONTENT
    # ══════════════════════════════════════════════════════════════════════════
    children = []

    # ── Cover / title block ────────────────────────────────────────────────────
    proj_name = pi.get('project', 'Structural Design Report')
    children += [
        f"new Paragraph({{alignment:AlignmentType.CENTER,spacing:{{before:1440,after:360}},children:[new TextRun({{text:{j(proj_name)},bold:true,size:56,font:'Arial',color:'1F5C99'}})]}})",
        f"new Paragraph({{alignment:AlignmentType.CENTER,spacing:{{after:120}},children:[new TextRun({{text:'STRUCTURAL DESIGN CALCULATIONS',bold:true,size:28,font:'Arial',color:'2E75B6'}})]}})",
        f"new Paragraph({{alignment:AlignmentType.CENTER,spacing:{{after:120}},children:[new TextRun({{text:'NBC 105:2025 (2nd Revision)  ·  IS 456:2000  ·  IS 875',size:22,font:'Arial',color:'595959'}})]}})",
        _blank(),
        _table_js(
            ["Field", "Details"],
            [
                ["Project",      pi.get('project', '—')],
                ["Engineer",     pi.get('engineer', '—')],
                ["Checked By",   pi.get('checked_by', '—')],
                ["Job No.",      pi.get('job_no', '—')],
                ["Date",         pi.get('date', datetime.now().strftime('%Y-%m-%d'))],
                ["Report Type",  f"{'Detailed Design Report' if mode=='detailed' else 'Summary Report'}"],
            ],
            [2800, 6560],
        ),
        _blank(),
        f"new Paragraph({{pageBreakBefore:true}})",
    ]

    # ── Table of Contents placeholder ─────────────────────────────────────────
    if mode == "detailed":
        children += [
            _h1("Table of Contents"),
            _p("(Update this field after opening in Word: right-click → Update Field)", italic=True, color="595959"),
            f"new TableOfContents('Table of Contents', {{hyperlink:true, headingStyleRange:'1-3', stylesWithLevels:[{{styleName:'Heading 1',level:1}},{{styleName:'Heading 2',level:2}}]}})",
            f"new Paragraph({{pageBreakBefore:true}})",
        ]

    # ── 1. Seismic Design ─────────────────────────────────────────────────────
    if seism:
        children.append(_h1("1. Seismic Design  —  NBC 105:2025"))

        if mode == "detailed":
            children += [
                _h2("1.1 Design Parameters"),
                _clause_p("Reference: NBC 105:2025 §4 (Seismic Hazard), §5 (Dynamic Characteristics)"),
                _blank(),
            ]

        params = [
            ["Zone / Municipality",     str(seism.get('zone_name',''))],
            ["Seismic Zone Factor Z",   f"{seism.get('Z',0):.2f}  (PGA for 475-yr return)"],
            ["Importance Factor I",      f"{seism.get('I',0):.2f}  (Importance Class {'' if seism.get('I',1)==1 else 'II' if seism.get('I',1)==1.25 else 'III'})"],
            ["Soil Type",               f"{seism.get('soil_type','')}  — {seism.get('alpha',0):.2f}α, Tc={seism.get('Tc',0):.1f}s, Td={seism.get('Td',0):.1f}s"],
            ["Building Height H",       f"{seism.get('H',0):.2f} m"],
            ["Number of Stories",       str(seism.get('num_stories',''))],
            ["Structural System",       str(seism.get('struct_sub',''))],
            ["Analysis Method",         str(seism.get('method',''))],
        ]
        children += [_table_js(["Parameter", "Value"], params, [4500, 4860]), _blank()]

        if mode == "detailed":
            children += [
                _h2("1.2 Fundamental Period"),
                _clause_p("NBC 105:2025 §5.1.2 Eq.(5.1.2): T₁ = kt × H^(3/4)"),
                _clause_p("NBC 105:2025 §5.1.3: Amplification factor = 1.25"),
                _formula_p(f"T_approx = {seism.get('kt',0):.4f} × {seism.get('H',0):.2f}^(3/4) = {seism.get('T_approx',0):.4f} s"),
                _formula_p(f"T_design = 1.25 × T_approx = {seism.get('T',0):.4f} s"),
                _blank(),
                _h2("1.3 Spectral Shape Factor Ch(T)"),
                _clause_p("NBC 105:2025 §4.1.2 Eq.(4.1.2): 3-zone formula"),
                _formula_p(f"For T = {seism.get('T',0):.4f}s vs Tc = {seism.get('Tc',0):.1f}s, Td = {seism.get('Td',0):.1f}s:"),
                _formula_p(f"Ch(T) = {seism.get('Ch_T',0):.4f}  (α = {seism.get('alpha',0):.2f})"),
                _blank(),
                _h2("1.4 Elastic Site Spectra"),
                _clause_p("NBC 105:2025 §4.1.1 Eq.(4.1.1): C(T) = Ch(T) × Z × I"),
                _formula_p(f"C(T) = {seism.get('Ch_T',0):.4f} × {seism.get('Z',0):.2f} × {seism.get('I',0):.2f} = {seism.get('C_T',0):.4f}"),
                _clause_p("NBC 105:2025 §4.2 Eq.(4.2.1): Cs(T) = 0.20 × C(T)  [SLS]"),
                _formula_p(f"Cs(T) = 0.20 × {seism.get('C_T',0):.4f} = {seism.get('Cs_T',0):.4f}"),
                _clause_p("NBC 105:2025 §4.3: Cv(Tv) = 2/3 × Z  [Vertical]"),
                _formula_p(f"Cv(Tv) = 2/3 × {seism.get('Z',0):.2f} = {seism.get('Cv_T',0):.4f}"),
                _blank(),
                _h2("1.5 Base Shear Coefficients"),
                _clause_p(f"NBC 105:2025 §6.1.1: Cd(T) = C(T) / (Rμ × Ωu)"),
                _formula_p(f"Cd(T)_ULS = {seism.get('C_T',0):.4f} / ({seism.get('Ru',0):.2f} × {seism.get('O_u',0):.2f}) = {seism.get('Cd_ULS',0):.4f}"),
                _clause_p("NBC 105:2025 §6.1.2: Cd(T) = Cs(T) / Ωs"),
                _formula_p(f"Cd(T)_SLS = {seism.get('Cs_T',0):.4f} / {seism.get('O_s',0):.2f} = {seism.get('Cd_SLS',0):.4f}"),
                _blank(),
            ]

        results = [
            ["Base Shear Coeff. Cd(T) ULS", f"{seism.get('Cd_ULS',0):.4f}"],
            ["Base Shear Coeff. Cd(T) SLS", f"{seism.get('Cd_SLS',0):.4f}"],
            ["Deflection Scale Factor kd",   f"{seism.get('kd',0):.2f}  (Table 6-1, {seism.get('num_stories','')} stories)"],
            ["Allowable Drift ULS",          "0.025 (inter-story)"],
            ["Allowable Drift SLS",          "0.006 (inter-story)"],
            ["Max. Displacement ULS",        f"{seism.get('Disp_ULS_mm',0):.1f} mm"],
            ["Max. Displacement SLS",        f"{seism.get('Disp_SLS_mm',0):.1f} mm"],
        ]
        children += [
            _h2("1.6 Design Results" if mode=="detailed" else "1.2 Design Results"),
            _table_js(["Result", "Value"], results, [5000,4360]), _blank()
        ]

        # Story forces table
        sf = seism.get("story_forces", [])
        if sf:
            children += [
                _h2("1.7 Story Force Distribution" if mode=="detailed" else ""),
                _clause_p("NBC 105:2025 §6.3: Fi = V × Wi×hi^k / Σ(Wj×hj^k)"),
            ] if mode=="detailed" else []
            sf_rows = [[str(f["floor"]), f"{f['W_kN']:.0f}", f"{f['h_m']:.1f}",
                        f"{f['Wh_k']:.0f}", f"{f['Fi_kN']:.1f}", f"{f['Vx_kN']:.1f}"]
                       for f in sf]
            children += [
                _table_js(["Floor","Wi (kN)","hi (m)","Wi·hi^k","Fi (kN)","Story Shear (kN)"],
                           sf_rows, [800,1200,1000,1800,1600,2960]),
                _blank(),
            ]

    # ── 2. Beam Design ────────────────────────────────────────────────────────
    if beam:
        children += [_h1("2. Beam Design  —  IS 456:2000"), _blank()]
        if mode == "detailed":
            children += [
                _h2("2.1 Section Properties & Loading"),
                _clause_p("IS 456:2000 §23, §38–41"),
                _blank(),
            ]

        b_params = [
            ["Section b × D",        f"{beam.get('b','?')} × {beam.get('D','?')} mm"],
            ["Effective depth d",    f"{beam.get('d_eff_mm',0):.1f} mm"],
            ["Concrete grade fck",   f"M{beam.get('fck','')}  ({beam.get('fck','')} MPa)"],
            ["Steel grade fy",       f"Fe{beam.get('fy','')}  ({beam.get('fy','')} MPa)"],
            ["Span",                 f"{beam.get('span_m',0):.2f} m"],
            ["Support condition",    str(beam.get('support_type',''))],
        ]
        children += [_table_js(["Property","Value"], b_params, [4500,4860]), _blank()]

        if mode == "detailed":
            children += [
                _h2("2.2 Flexural Design"),
                _clause_p("IS 456:2000 §38.1: xu_max/d = 0.48 (Fe415), 0.46 (Fe500)"),
                _formula_p(f"Mu_lim = 0.36 × fck × b × xu_max × (d − 0.42 × xu_max)"),
                _formula_p(f"       = {beam.get('Mu_lim_kNm',0):.2f} kN·m"),
                _formula_p(f"Design Mu = {beam.get('Mu_design_kNm',0):.2f} kN·m"),
                _blank(),
            ]
            # Doubly reinforced
            dr = beam.get('doubly')
            if dr:
                children += [
                    _p("⚑ Mu > Mu,lim → Doubly Reinforced Section  (IS 456:2000 Annex G)", color="7F0000"),
                    _clause_p("IS 456 Annex G: Compression steel Asc designed for excess moment"),
                    _formula_p(f"Compression bar stress fsc = {dr.get('fsc_MPa',0):.0f} MPa  (εsc = {dr.get('eps_sc',0):.4f})"),
                    _formula_p(f"Asc required = {dr.get('Asc_req_mm2',0):.0f} mm²   →   {dr.get('no_comp_bars',0)} × Ø{int(dr.get('comp_bar_dia',0))} mm"),
                    _formula_p(f"Ast from balanced: {dr.get('Ast1_mm2',0):.0f} mm²   Extra tension Ast2: {dr.get('Ast2_mm2',0):.0f} mm²"),
                    _blank(),
                ]

        b_results = [
            ["Design Moment Mu",     f"{beam.get('Mu_design_kNm',0):.2f} kN·m"],
            ["Limiting Moment Mu,lim", f"{beam.get('Mu_lim_kNm',0):.2f} kN·m"],
            ["Section type",         "Doubly Reinforced" if beam.get('is_doubly') else "Singly Reinforced"],
            ["Ast required",         f"{beam.get('Ast_req_mm2',0):.0f} mm²"],
            ["Ast minimum",          f"{beam.get('Ast_min_mm2',0):.0f} mm²  (IS 456 §26.5.1.1)"],
            ["Bars provided",        f"{beam.get('no_of_bars',0)} × Ø{beam.get('main_dia','?')} mm"],
            ["Bar spacing",          f"{beam.get('spacing_mm',0):.0f} mm c/c"],
            ["Ast provided",         f"{beam.get('Ast_prov_mm2',0):.0f} mm²"],
            ["Shear stirrups",       f"Ø8 {beam.get('shear',{}).get('stir_legs',2)}-leg @ {beam.get('shear',{}).get('Sv_mm','?')} mm c/c"],
            ["Development length Ld",f"{beam.get('Ld_mm',0):.0f} mm  (IS 456 §26.2.1)"],
        ]
        children += [_table_js(["Result","Value"], b_results, [5000,4360]), _blank()]

        if mode == "detailed":
            dr = beam.get("deflection")
            if dr:
                children += [
                    _h2("2.3 Deflection Check"),
                    _clause_p("IS 456:2000 §23.2: Modification factors kt, kc, kf"),
                    _formula_p(f"Basic L/d = {dr.get('ld_basic',20)}   kt = {dr.get('kt',0):.3f}  (fs={dr.get('fs_serv',0):.0f} MPa)"),
                    _formula_p(f"kc = {dr.get('kc',1):.3f} (compression mod.)   kf = {dr.get('kf',1):.2f} (flange mod.)"),
                    _formula_p(f"Allowable L/d = {dr.get('ld_basic',20)} × {dr.get('kt',0):.3f} × {dr.get('kc',1):.3f} × {dr.get('kf',1):.2f} = {dr.get('ld_allow',0):.2f}"),
                    _formula_p(f"Provided L/d  = {dr.get('ld_prov',0):.2f}  → {'OK ✓' if dr.get('ok') else 'REVISE ✗'}"),
                    _blank(),
                ]
            shear_d = beam.get("shear", {})
            if mode == "detailed":
                children += [
                    _h2("2.4 Shear Design"),
                    _clause_p("IS 456:2000 §40: Design shear strength τc from Table 19"),
                    _formula_p(f"τv = Vu/(bd) = {shear_d.get('tau_v',0):.3f} MPa"),
                    _formula_p(f"τc = {shear_d.get('tau_c',0):.3f} MPa  →  Stirrups: {shear_d.get('status','')}"),
                    _blank(),
                ]

    # ── 3. Column Design ──────────────────────────────────────────────────────
    if col:
        children += [_h1("3. Column Design  —  IS 456:2000 + NBC 105:2025 Annex A"), _blank()]

        c_params = [
            ["Section b × D",        f"{col.get('b','?')} × {col.get('D','?')} mm"],
            ["Effective length lex",  f"{col.get('lex','?')} mm"],
            ["Effective length ley",  f"{col.get('ley','?')} mm"],
            ["Slenderness λx",       f"{col.get('lambda_x',0):.2f}  ({'Slender' if col.get('is_slender') else 'Short'})"],
            ["Slenderness λy",       f"{col.get('lambda_y',0):.2f}"],
            ["Factored load Pu",     f"{col.get('Pu_kN',0):.0f} kN"],
            ["Design Mux (incl. Madd)", f"{col.get('Mux_design_kNm',0):.2f} kN·m"],
            ["Design Muy (incl. Madd)", f"{col.get('Muy_design_kNm',0):.2f} kN·m"],
        ]
        children += [_table_js(["Property","Value"], c_params, [5000,4360]), _blank()]

        if mode == "detailed" and col.get('is_slender'):
            children += [
                _h2("3.1 Additional Moments — Slender Column"),
                _clause_p("IS 456:2000 §39.7: Ma = k × Pu × D × λ² / 2000"),
                _formula_p(f"Max = {col.get('Ma_x_kNm',0):.2f} kN·m   May = {col.get('Ma_y_kNm',0):.2f} kN·m"),
                _blank(),
            ]

        if mode == "detailed":
            children += [
                _h2("3.2 Biaxial Interaction  (IS 456:2000 §39.6)"),
                _clause_p("(Mux/Mux1)^αn + (Muy/Muy1)^αn ≤ 1.0"),
                _formula_p(f"Mux1 = {col.get('Mux1_kNm',0):.2f} kN·m   Muy1 = {col.get('Muy1_kNm',0):.2f} kN·m"),
                _formula_p(f"Puz = {col.get('Puz_kN',0):.0f} kN   αn = {col.get('alpha_n',0):.3f}"),
                _formula_p(f"Interaction = {col.get('interaction',0):.4f}  {'≤ 1.0 ✓ OK' if col.get('interaction',1)<=1 else '> 1.0 ✗ REVISE'}"),
                _blank(),
            ]

        c_results = [
            ["Biaxial interaction ratio", f"{col.get('interaction',0):.4f}  ({'OK ✓' if col.get('interaction',1)<=1 else 'REVISE ✗'})"],
            ["Ast required",             f"{col.get('Ast_req_mm2',0):.0f} mm²"],
            ["Steel percentage",         f"{col.get('steel_pct',0):.2f}%  (min 0.8%, max 4%)"],
            ["Bars provided",            f"{col.get('no_of_bars',0)} × Ø{int(col.get('bar_dia_mm',0))} mm"],
            ["Ast provided",             f"{col.get('Ast_prov_mm2',0):.0f} mm²"],
            ["Tie spacing (general)",    f"{col.get('tie_spacing_mm',0):.0f} mm c/c  (IS 456 §26.5.3.1)"],
            ["Confinement zone (NBC 105 Annex A)", f"{col.get('conf_zone_mm',0):.0f} mm (top & bottom)"],
            ["Tie spacing in conf. zone", f"{col.get('conf_tie_sp_mm',0):.0f} mm c/c  (135° hooks)"],
            ["Confinement hoop Ash",     f"Required: {col.get('Ash_req_mm2',0):.1f} mm²   Provided: {col.get('Ash_prov_mm2',0):.1f} mm²"],
        ]
        children += [_table_js(["Result","Value"], c_results, [5400,3960]), _blank()]

    # ── 4. Foundation Design ──────────────────────────────────────────────────
    if fndg:
        children += [_h1("4. Foundation Design  —  IS 456:2000 §34 + NBC 105:2025 §3.8"), _blank()]

        ftype = fndg.get("type", "concentric")
        if mode == "detailed":
            children += [
                _h2(f"4.1 Foundation Type: {'Eccentric' if ftype=='eccentric' else 'Combined' if ftype=='combined' else 'Concentric'} Isolated Footing"),
                _clause_p("IS 456:2000 §34.1.3: Minimum depth 300mm for RC footing"),
            ]
            if fndg.get("seismic_used"):
                children.append(_clause_p("NBC 105:2025 §3.8: SBC increased by 50% for seismic load combination"))
            children.append(_blank())

        f_params = [
            ["Plan size",           f"{fndg.get('L_mm',0)} × {fndg.get('B_mm',0)} mm"],
            ["Overall depth D",     f"{fndg.get('D_mm',0):.0f} mm  (min 300 mm, IS 456 §34.1.3)"],
            ["Effective depth d",   f"{fndg.get('d_mm',0):.0f} mm"],
            ["Design SBC",         f"{fndg.get('SBC_used_kPa',0):.0f} kN/m²"],
            ["q_max (service)",    f"{fndg.get('q_max_kPa',0):.2f} kN/m²  ({'OK ✓' if fndg.get('pressure_ok') else 'EXCEEDS ✗'})"],
            ["q_min (service)",    f"{fndg.get('q_min_kPa',0):.2f} kN/m²  ({'No tension ✓' if fndg.get('q_min_kPa',0)>=0 else 'Tension zone ✗'})"],
        ]
        if ftype == "eccentric":
            f_params += [
                ["Eccentricity ex",  f"{fndg.get('ex_m',0):.4f} m  (from My)"],
                ["Eccentricity ey",  f"{fndg.get('ey_m',0):.4f} m  (from Mx)"],
                ["Within kern",     "Yes ✓ (no uplift)" if fndg.get('kern_ok') else "No — effective area applied"],
            ]

        children += [_table_js(["Property","Value"], f_params, [5000,4360]), _blank()]

        if mode == "detailed":
            children += [
                _h2("4.2 Bending Moment & Reinforcement"),
                _clause_p("IS 456:2000 §34.4.1: Moment at face of column"),
                _formula_p(f"qu (factored) = 1.5 × q_avg = {fndg.get('qu_kPa',0):.2f} kN/m²"),
                _formula_p(f"Mu_L = qu × B × (overhang)²/2 = {fndg.get('Mu_L_kNm',0):.2f} kN·m"),
                _formula_p(f"Mu_B = qu × L × (overhang)²/2 = {fndg.get('Mu_B_kNm',0):.2f} kN·m"),
                _blank(),
                _h2("4.3 Shear Checks"),
                _clause_p("IS 456:2000 §34.4.2a: One-way shear at d from face"),
                _formula_p(f"τv_L = {fndg.get('tau_v_L',0):.3f} MPa  vs  τc_L = {fndg.get('tau_c_L',0):.3f} MPa  — {'OK ✓' if fndg.get('one_way_ok') else 'FAIL ✗'}"),
                _clause_p("IS 456:2000 §34.4.2b: Two-way (punching) at d/2 from column face"),
                _clause_p("τc,punch = 0.25√fck  (IS 456:2000 §31.6.3.1)"),
                _formula_p(f"τv,punch = {fndg.get('tau_v_punch',0):.3f} MPa  vs  τc,punch = {fndg.get('tau_c_punch',0):.3f} MPa  — {'OK ✓' if fndg.get('punch_ok') else 'FAIL ✗'}"),
                _blank(),
                _h2("4.4 Development Length"),
                _clause_p("IS 456:2000 §34.4.3 and §26.2.1"),
                _formula_p(f"Ld = 0.87fy×Ø / (4τbd) = {fndg.get('Ld_mm',0):.0f} mm"),
                _formula_p(f"Available = {fndg.get('avail_L_mm',fndg.get('avail_m',0)):.0f} mm — {'OK ✓' if fndg.get('dev_ok') else 'INSUFFICIENT ✗'}"),
                _blank(),
            ]

        f_results = [
            ["Ast in L direction",   f"{fndg.get('Ast_L_per_m_mm2',0):.0f} mm²/m  →  Ø{int(fndg.get('bar_dia_mm',12))} @ {fndg.get('sp_L_mm',0)} mm c/c"],
            ["Ast in B direction",   f"{fndg.get('Ast_B_per_m_mm2',0):.0f} mm²/m  →  Ø{int(fndg.get('bar_dia_mm',12))} @ {fndg.get('sp_B_mm',0)} mm c/c"],
            ["One-way shear",        "OK ✓" if fndg.get('one_way_ok') else "FAILS — Increase depth"],
            ["Punching shear",       "OK ✓" if fndg.get('punch_ok') else "FAILS — Increase depth"],
            ["Development length",   "OK ✓" if fndg.get('dev_ok') else "INSUFFICIENT — Check"],
            ["Col.-Ftg. bearing",    "OK ✓" if fndg.get('bear_ok',True) else "Provide dowels"],
        ]
        children += [_table_js(["Check","Result"], f_results, [5000,4360]), _blank()]

    # ── 5. Load Combinations ─────────────────────────────────────────────────
    if seism and seism.get("load_combos") and mode == "detailed":
        children += [
            _h1("5. Load Combinations  —  NBC 105:2025 §3.6"),
            _clause_p("Limit State Method (LSM). λ = live load factor for seismic combinations."),
            _clause_p(f"λ = {seism.get('lambda_ll',0.30):.2f}  (storage: 0.60, all others: 0.30)"),
            _blank(),
        ]
        combos = seism["load_combos"]
        combo_rows = [[c["label"], c["formula"],
                       f"{c['DL_fac']:.1f}",
                       f"{c['LL_fac']:.2f}" if isinstance(c['LL_fac'],float) else str(c['LL_fac']),
                       f"E_ULS×{c['E_ULS_fac']:.1f}" if c['E_ULS_fac']!=0 else
                       (f"E_SLS×{c['E_SLS_fac']:.1f}" if c['E_SLS_fac']!=0 else
                        (f"W×{c['W_fac']:.1f}" if c['W_fac']!=0 else "—"))]
                      for c in combos]
        children += [
            _table_js(["Combination","Formula","DL factor","LL factor","E/W factor"],
                      combo_rows, [2000,3000,1300,1300,1760]),
            _blank(),
        ]

    # ── Disclaimer ─────────────────────────────────────────────────────────────
    children += [
        _h1("Disclaimer"),
        _p("This report is generated by Structural Calculator v4.0 for reference purposes. "
           "All results must be independently verified by a qualified structural engineer "
           "before use in construction. The calculations are based on NBC 105:2025 (Second "
           "Revision) and IS 456:2000 as interpreted by the software. Local conditions, "
           "site-specific requirements, and professional judgement may require modifications.", italic=True),
        _blank(),
        _p(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Structural Calculator v4.0"),
    ]

    # ══════════════════════════════════════════════════════════════════════════
    # WRITE JS FILE
    # ══════════════════════════════════════════════════════════════════════════
    children_str = ",\n    ".join(children)

    js = f"""
const fs = require('fs');
const {{
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageNumberElement, TableOfContents,
  PageBreak, UnderlineType
}} = require('docx');

const cellBorders = {{
  top:    {{style: BorderStyle.SINGLE, size:1, color:"CCCCCC"}},
  bottom: {{style: BorderStyle.SINGLE, size:1, color:"CCCCCC"}},
  left:   {{style: BorderStyle.SINGLE, size:1, color:"CCCCCC"}},
  right:  {{style: BorderStyle.SINGLE, size:1, color:"CCCCCC"}},
}};

const doc = new Document({{
  features: {{ updateFields: true }},
  styles: {{
    default: {{ document: {{ run: {{ font: "Arial", size: 20 }} }} }},
    paragraphStyles: [
      {{ id:"Heading1", name:"Heading 1", basedOn:"Normal", next:"Normal", quickFormat:true,
         run:{{size:32,bold:true,font:"Arial",color:"1F5C99"}},
         paragraph:{{spacing:{{before:360,after:240}},outlineLevel:0}} }},
      {{ id:"Heading2", name:"Heading 2", basedOn:"Normal", next:"Normal", quickFormat:true,
         run:{{size:26,bold:true,font:"Arial",color:"2E75B6"}},
         paragraph:{{spacing:{{before:240,after:120}},outlineLevel:1}} }},
      {{ id:"Heading3", name:"Heading 3", basedOn:"Normal", next:"Normal", quickFormat:true,
         run:{{size:22,bold:true,font:"Arial",color:"31849B"}},
         paragraph:{{spacing:{{before:180,after:80}},outlineLevel:2}} }},
    ]
  }},
  sections: [{{
    properties: {{
      page: {{
        size: {{ width:11906, height:16838 }},
        margin: {{ top:1008, right:1008, bottom:1008, left:1440 }}
      }}
    }},
    headers: {{
      default: new Header({{
        children: [new Paragraph({{
          border: {{ bottom: {{ style:BorderStyle.SINGLE,size:6,color:"1F5C99",space:1 }} }},
          children: [
            new TextRun({{text:{j(proj_name)},bold:true,size:18,font:"Arial",color:"1F5C99"}}),
            new TextRun({{text:"  |  NBC 105:2025 · IS 456:2000",size:16,font:"Arial",color:"595959"}}),
          ]
        }})]
      }})
    }},
    footers: {{
      default: new Footer({{
        children: [new Paragraph({{
          border: {{ top: {{ style:BorderStyle.SINGLE,size:4,color:"1F5C99",space:1 }} }},
          children: [
            new TextRun({{text:"Structural Calculator v4.0  |  {pi.get('engineer','—')}  |  ",size:16,font:"Arial",color:"595959"}}),
            new TextRun({{text:"Page ",size:16,font:"Arial",color:"595959"}}),
            new TextRun({{children:[PageNumber.CURRENT],size:16,font:"Arial",color:"595959"}}),
          ]
        }})]
      }})
    }},
    children: [
      {children_str}
    ]
  }}]
}});

Packer.toBuffer(doc).then(buf => {{
  fs.writeFileSync({j(output_path)}, buf);
  console.log('Written: {output_path}');
}});
"""
    _run_node(js, output_path)
    return output_path
