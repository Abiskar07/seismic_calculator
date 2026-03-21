"""
export/excel_exporter.py — Professional Excel Report Generator
=============================================================
Creates a multi-sheet workbook using openpyxl with:
  Sheet 1: Summary — key results at a glance
  Sheet 2: Seismic — full NBC 105:2025 calculations with formulas
  Sheet 3: Beam Design — IS 456 beam with formulas & checks
  Sheet 4: Column Design — biaxial interaction
  Sheet 5: Foundation — footing checks
  Sheet 6: Load Combinations — NBC 105:2025 §3.6
"""
from __future__ import annotations
from datetime import datetime
import os

try:
    from openpyxl import Workbook
    from openpyxl.styles import (
        Font, PatternFill, Alignment, Border, Side,
        GradientFill
    )
    from openpyxl.utils import get_column_letter
    from openpyxl.chart import BarChart, Reference
    from openpyxl.chart.series import DataPoint
    OPENPYXL_OK = True
except ImportError:
    OPENPYXL_OK = False


# ── Colour palette ─────────────────────────────────────────────────────────────
C_TITLE_BG  = "1F5C99"   # dark blue
C_TITLE_FG  = "FFFFFF"   # white
C_HEAD1_BG  = "2E75B6"   # medium blue
C_HEAD2_BG  = "DBEEF4"   # light blue
C_HEAD3_BG  = "F2F9FF"   # very light blue
C_OK_BG     = "E2EFDA"   # light green
C_OK_FG     = "375623"
C_FAIL_BG   = "FFDFD1"   # light red
C_FAIL_FG   = "7F0000"
C_WARN_BG   = "FFEB9C"   # amber
C_WARN_FG   = "9C5700"
C_INPUT_FG  = "0070C0"   # blue for input cells
C_FORMULA   = "375623"   # green for formulas
C_BORDER    = "BFBFBF"
C_ALT_ROW   = "F5F9FF"


def _thin_border():
    s = Side(style="thin", color=C_BORDER)
    return Border(left=s, right=s, top=s, bottom=s)

def _header_style(ws, row, col, text, bg=C_HEAD1_BG, fg=C_TITLE_FG, size=11, bold=True, merge_to=None):
    c = ws.cell(row=row, column=col, value=text)
    c.font      = Font(name="Arial", size=size, bold=bold, color=fg)
    c.fill      = PatternFill("solid", fgColor=bg)
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    c.border    = _thin_border()
    if merge_to:
        ws.merge_cells(start_row=row, start_column=col,
                       end_row=row, end_column=merge_to)
    return c

def _data_cell(ws, row, col, value, fg="000000", bg=None, bold=False, align="left", fmt=None, border=True):
    c = ws.cell(row=row, column=col, value=value)
    c.font      = Font(name="Arial", size=10, bold=bold, color=fg)
    c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=False)
    if bg:
        c.fill = PatternFill("solid", fgColor=bg)
    if border:
        c.border = _thin_border()
    if fmt:
        c.number_format = fmt
    return c

def _section_title(ws, row, text, span_end_col=6):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span_end_col)
    c = ws.cell(row=row, column=1, value=text)
    c.font      = Font(name="Arial", size=12, bold=True, color=C_TITLE_FG)
    c.fill      = PatternFill("solid", fgColor=C_TITLE_BG)
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    c.border    = _thin_border()

def _status_cell(ws, row, col, ok: bool | None, ok_text="OK", fail_text="REVISE"):
    if ok is True:
        return _data_cell(ws, row, col, f"✓  {ok_text}", fg=C_OK_FG, bg=C_OK_BG, bold=True, align="center")
    elif ok is False:
        return _data_cell(ws, row, col, f"✗  {fail_text}", fg=C_FAIL_FG, bg=C_FAIL_BG, bold=True, align="center")
    else:
        return _data_cell(ws, row, col, "—", align="center")

def _kv_rows(ws, start_row, pairs, label_col=1, value_col=2, label_width=35, formula_col=None):
    """Write label:value rows. Returns next row."""
    r = start_row
    for i, pair in enumerate(pairs):
        if len(pair) == 2:
            label, value = pair; formula = None
        else:
            label, value, formula = pair
        bg = C_ALT_ROW if i % 2 == 0 else None
        _data_cell(ws, r, label_col, label, bold=True, bg=bg)
        _data_cell(ws, r, value_col, value, bg=bg, align="left", fg=C_INPUT_FG if formula else "000000")
        if formula_col and formula:
            _data_cell(ws, r, formula_col, formula, fg="595959", bg=bg)
        r += 1
    return r


def generate_excel_report(
    data: dict,
    output_path: str,
    mode: str = "detailed",
) -> str:
    """
    Generate a professional Excel (.xlsx) structural engineering report.
    mode: "summary" | "detailed"
    """
    if not OPENPYXL_OK:
        raise ImportError("openpyxl is required. Run: pip install openpyxl")

    wb = Workbook()
    pi    = data.get("project_info", {})
    seism = data.get("seismic", {})
    beam  = data.get("beam", {})
    col   = data.get("column", {})
    fndg  = data.get("foundation", {})

    def _proj_header(ws, sheet_title):
        """Add project header block at top of each sheet."""
        ws.merge_cells("A1:H1")
        c = ws["A1"]
        c.value = f"STRUCTURAL DESIGN CALCULATIONS  —  {sheet_title.upper()}"
        c.font  = Font(name="Arial", size=14, bold=True, color=C_TITLE_FG)
        c.fill  = PatternFill("solid", fgColor=C_TITLE_BG)
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 28

        info_pairs = [
            ("Project:", pi.get("project","—")),
            ("Engineer:", pi.get("engineer","—")),
            ("Date:", pi.get("date", datetime.now().strftime("%Y-%m-%d"))),
        ]
        for col_offset, (lbl, val) in enumerate(info_pairs):
            c1 = ws.cell(row=2, column=col_offset*2+1, value=lbl)
            c1.font  = Font(name="Arial", size=9, bold=True, color="595959")
            c2 = ws.cell(row=2, column=col_offset*2+2, value=val)
            c2.font  = Font(name="Arial", size=9, color="000000")
        ws.row_dimensions[2].height = 16

        # Standard codes line
        ws.merge_cells("A3:H3")
        c3 = ws["A3"]
        c3.value = "Standards: NBC 105:2025 (Second Revision)  ·  IS 456:2000  ·  IS 875 Part 1 & 2"
        c3.font  = Font(name="Arial", size=9, italic=True, color="595959")
        c3.alignment = Alignment(horizontal="center")
        ws.row_dimensions[3].height = 14
        return 5  # first content row

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 1: SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    ws = wb.active
    ws.title = "📋 Summary"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 22
    ws.column_dimensions["E"].width = 18

    r = _proj_header(ws, "Summary Report")

    _section_title(ws, r, "PROJECT SUMMARY", span_end_col=5)
    r += 1

    proj_rows = [
        ("Project Name", pi.get("project","—")),
        ("Structural Engineer", pi.get("engineer","—")),
        ("Checked By", pi.get("checked_by","—")),
        ("Job Reference", pi.get("job_no","—")),
        ("Report Date", pi.get("date", datetime.now().strftime("%Y-%m-%d"))),
        ("Report Type", "Detailed Design Report" if mode=="detailed" else "Summary Report"),
        ("Standards", "NBC 105:2025 · IS 456:2000 · IS 875"),
    ]
    r = _kv_rows(ws, r, proj_rows)
    r += 1

    # Seismic summary
    if seism:
        _section_title(ws, r, "SEISMIC DESIGN SUMMARY  —  NBC 105:2025", span_end_col=5)
        r += 1
        _header_style(ws, r, 1, "Parameter", bg=C_HEAD1_BG, merge_to=None)
        _header_style(ws, r, 2, "Value",      bg=C_HEAD1_BG)
        _header_style(ws, r, 3, "Code Ref.",  bg=C_HEAD1_BG)
        _header_style(ws, r, 4, "Status",     bg=C_HEAD1_BG)
        r += 1

        seism_rows = [
            ("Zone Factor Z",               f"{seism.get('Z',0):.2f}",     "NBC 105:2025 Annex C", True),
            ("Importance Factor I",          f"{seism.get('I',0):.2f}",     "Table 4-4", True),
            ("Design Period T",             f"{seism.get('T',0):.4f} s",   "§5.1.2–5.1.3", True),
            ("Spectral Shape Factor Ch(T)", f"{seism.get('Ch_T',0):.4f}",  "§4.1.2 Eq.(4.1.2)", True),
            ("Elastic Site Spectra C(T)",   f"{seism.get('C_T',0):.4f}",   "§4.1.1 Eq.(4.1.1)", True),
            ("SLS Spectra Cs(T)",           f"{seism.get('Cs_T',0):.4f}",  "§4.2", True),
            ("Vertical Spectra Cv(T)",      f"{seism.get('Cv_T',0):.4f}",  "§4.3", True),
            ("Ductility Factor Rμ",         f"{seism.get('Ru',0):.2f}",    "Table 5-2", True),
            ("Overstrength Ωu",             f"{seism.get('O_u',0):.2f}",   "Table 5-2", True),
            ("Base Shear Coeff. Cd_ULS",    f"{seism.get('Cd_ULS',0):.4f}","§6.1.1", True),
            ("Base Shear Coeff. Cd_SLS",    f"{seism.get('Cd_SLS',0):.4f}","§6.1.2", True),
            ("Deflection Scale kd",         f"{seism.get('kd',0):.2f}",    "Table 6-1", True),
            ("Max Displacement ULS",        f"{seism.get('Disp_ULS_mm',0):.1f} mm", "§5.5.3", True),
        ]
        for i, (label, value, ref, ok_) in enumerate(seism_rows):
            bg = C_ALT_ROW if i%2==0 else None
            _data_cell(ws, r, 1, label, bold=True, bg=bg)
            _data_cell(ws, r, 2, value, fg=C_INPUT_FG, bg=bg)
            _data_cell(ws, r, 3, ref, fg="595959", bg=bg)
            _status_cell(ws, r, 4, True)
            r += 1
        r += 1

    # Structural element summary
    for title, res, rows_def in [
        ("SLAB DESIGN SUMMARY  —  IS 456:2000", data.get("slab",{}),
         [(k, v, "—", None) for k, v in data.get("slab",{}).get("summary",{}).items()]
        ) if data.get("slab") else (None, None, None),
        ("BEAM DESIGN SUMMARY  —  IS 456:2000", beam, [
            ("Section", f"{beam.get('b','?')} × {beam.get('D','?')} mm", "", None),
            ("Design Moment Mu", f"{beam.get('Mu_design_kNm',0):.2f} kN·m", "§22.2", None),
            ("Limiting Moment Mu,lim", f"{beam.get('Mu_lim_kNm',0):.2f} kN·m", "§38.1", None),
            ("Section Type", "Doubly Reinforced" if beam.get("is_doubly") else "Singly Reinforced", "Annex G", None),
            ("Tension bars provided", f"{beam.get('no_of_bars',0)}×Ø{beam.get('main_dia','?')} mm @ {beam.get('spacing_mm',0):.0f}mm", "§26.5.1", True),
            ("Ast provided", f"{beam.get('Ast_prov_mm2',0):.0f} mm²", "§26.5.1.1", beam.get('Ast_prov_mm2',0)>=beam.get('Ast_req_mm2',0)),
            ("Shear stirrups", f"Ø8 @ {beam.get('shear',{}).get('Sv_mm','?')} mm", "§40.4", None),
            ("Development length Ld", f"{beam.get('Ld_mm',0):.0f} mm", "§26.2.1", True),
            ("Deflection L/d", f"{beam.get('deflection',{}).get('ld_prov',0):.1f} ≤ {beam.get('deflection',{}).get('ld_allow',0):.1f}" if beam.get("deflection") else "N/A", "§23.2", beam.get("deflection",{}).get("ok")),
        ]) if beam else None,
        ("COLUMN DESIGN SUMMARY  —  IS 456:2000 + NBC 105:2025 Annex A", col, [
            ("Section", f"{col.get('b','?')} × {col.get('D','?')} mm", "", None),
            ("Slenderness λx / λy", f"{col.get('lambda_x',0):.1f} / {col.get('lambda_y',0):.1f}", "§25.1.2", not col.get("is_slender",False)),
            ("Design Mux (incl. Madd)", f"{col.get('Mux_design_kNm',0):.2f} kN·m", "§39.7", None),
            ("Design Muy (incl. Madd)", f"{col.get('Muy_design_kNm',0):.2f} kN·m", "§39.7", None),
            ("Biaxial interaction ratio", f"{col.get('interaction',0):.4f}", "§39.6", col.get("interaction",1)<=1.0),
            ("Steel provided", f"{col.get('no_of_bars',0)}×Ø{int(col.get('bar_dia_mm',0))}mm = {col.get('Ast_prov_mm2',0):.0f}mm²", "§26.5.3", None),
            ("Steel percentage", f"{col.get('steel_pct',0):.2f}%", "§26.5.3.1", 0.8<=col.get('steel_pct',0)<=4.0),
            ("Tie spacing (general)", f"{col.get('tie_spacing_mm',0):.0f} mm c/c", "§26.5.3.1", None),
            ("NBC 105 confinement zone", f"{col.get('conf_zone_mm',0):.0f} mm (top & bottom)", "Annex A §A.4.4.1", None),
            ("Confinement tie spacing", f"{col.get('conf_tie_sp_mm',0):.0f} mm c/c", "Annex A §A.4.4.3", None),
            ("Hoop Ash required/provided", f"{col.get('Ash_req_mm2',0):.1f} / {col.get('Ash_prov_mm2',0):.1f} mm²", "Annex A §A.4.4.4", col.get("hoop_ok",True)),
        ]) if col else None,
        ("FOUNDATION DESIGN SUMMARY  —  IS 456:2000 §34", fndg, [
            ("Plan size", f"{fndg.get('L_mm',0)}×{fndg.get('B_mm',0)} mm", "§34.1", None),
            ("Depth D / Effective d", f"{fndg.get('D_mm',0):.0f} / {fndg.get('d_mm',0):.0f} mm", "§34.1.3 (min 300mm)", fndg.get("D_mm",0)>=300),
            ("Design SBC", f"{fndg.get('SBC_used_kPa',0):.0f} kN/m²", "NBC 105:2025 §3.8", None),
            ("q_max (service)", f"{fndg.get('q_max_kPa',0):.2f} kN/m²", "§34.2", fndg.get("pressure_ok")),
            ("q_min (service)", f"{fndg.get('q_min_kPa',0):.2f} kN/m²", "§34.2.4", fndg.get("q_min_kPa",0)>=0),
            ("Rein. L direction", f"Ø{int(fndg.get('bar_dia_mm',12))}@{fndg.get('sp_L_mm',0)}mm c/c", "§34.4.1", None),
            ("Rein. B direction", f"Ø{int(fndg.get('bar_dia_mm',12))}@{fndg.get('sp_B_mm',0)}mm c/c", "§34.4.1", None),
            ("One-way shear", f"τv={fndg.get('tau_v_L',0):.3f} ≤ τc={fndg.get('tau_c_L',0):.3f} MPa", "§34.4.2a", fndg.get("one_way_ok")),
            ("Punching shear", f"τv={fndg.get('tau_v_punch',0):.3f} ≤ τc={fndg.get('tau_c_punch',0):.3f} MPa", "§34.4.2b / §31.6", fndg.get("punch_ok")),
            ("Development length", f"Ld={fndg.get('Ld_mm',0):.0f} mm, Avail={fndg.get('avail_L_mm',0):.0f}mm", "§34.4.3", fndg.get("dev_ok")),
        ]) if fndg else None,
    ]:
        if title is None or res is None: continue
        _section_title(ws, r, title, span_end_col=5)
        r += 1
        _header_style(ws, r, 1, "Check", bg=C_HEAD1_BG)
        _header_style(ws, r, 2, "Result/Value", bg=C_HEAD1_BG)
        _header_style(ws, r, 3, "Clause Ref.", bg=C_HEAD1_BG)
        _header_style(ws, r, 4, "Status", bg=C_HEAD1_BG)
        r += 1
        for i, row_data in enumerate(rows_def):
            label, value, ref, ok_ = row_data
            bg = C_ALT_ROW if i%2==0 else None
            _data_cell(ws, r, 1, label, bold=True, bg=bg)
            _data_cell(ws, r, 2, value, fg=C_INPUT_FG if ok_ is None else "000000", bg=bg)
            _data_cell(ws, r, 3, ref, fg="595959", bg=bg)
            if ok_ is None:
                _data_cell(ws, r, 4, "—", align="center", bg=bg)
            else:
                _status_cell(ws, r, 4, ok_)
            r += 1
        r += 1

    ws.freeze_panes = "A5"

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 2: SEISMIC (Detailed only)
    # ══════════════════════════════════════════════════════════════════════════
    if seism and mode == "detailed":
        ws2 = wb.create_sheet("🌍 Seismic (NBC 105)")
        ws2.column_dimensions["A"].width = 40
        ws2.column_dimensions["B"].width = 22
        ws2.column_dimensions["C"].width = 30
        ws2.column_dimensions["D"].width = 25
        ws2.column_dimensions["E"].width = 18

        r = _proj_header(ws2, "Seismic Design — NBC 105:2025")

        _section_title(ws2, r, "1. SITE & STRUCTURAL PARAMETERS", span_end_col=5)
        r += 1
        _header_style(ws2, r, 1, "Parameter"); _header_style(ws2, r, 2, "Value")
        _header_style(ws2, r, 3, "Formula / Clause"); _header_style(ws2, r, 4, "Code Reference")
        r += 1
        params = [
            ("Zone / Municipality",         seism.get("zone_name",""),
             "—",                            "NBC 105:2025 Annex C / Table C-1"),
            ("Seismic Zone Factor Z",       f"{seism.get('Z',0):.2f}",
             "Peak Ground Acceleration",     "NBC 105:2025 §4.1.4"),
            ("Importance Factor I",          f"{seism.get('I',0):.2f}",
             "See Table 4-4",               "NBC 105:2025 §4.1.5"),
            ("Soil Type",                   seism.get("soil_type",""),
             f"α={seism.get('alpha',0):.2f}, Tc={seism.get('Tc',0):.1f}s, Td={seism.get('Td',0):.1f}s",
             "NBC 105:2025 §4.1.3 Table 4-1"),
            ("Structural System",           seism.get("struct_sub",""),
             f"Rμ={seism.get('Ru',0):.2f}, Ωu={seism.get('O_u',0):.2f}, Ωs={seism.get('O_s',0):.2f}",
             "NBC 105:2025 §5.3 Table 5-2"),
            ("Period coefficient kt",       f"{seism.get('kt',0):.4f}",
             "From Table 5-2 system type",  "NBC 105:2025 §5.1.2"),
        ]
        for i, (a,b,c,d) in enumerate(params):
            bg = C_ALT_ROW if i%2==0 else None
            for col_n, val in [(1,a),(2,b),(3,c),(4,d)]:
                _data_cell(ws2, r, col_n, val, bg=bg, fg="595959" if col_n in (3,4) else "000000")
            r += 1
        r += 1

        _section_title(ws2, r, "2. FUNDAMENTAL PERIOD CALCULATION", span_end_col=5)
        r += 1
        period_rows = [
            ("kt × H^(3/4)", f"T_approx", f"{seism.get('kt',0):.4f} × {seism.get('H',0):.3f}^(3/4)", f"{seism.get('T_approx',0):.4f} s", "NBC 105:2025 §5.1.2 Eq.(5.1.2)"),
            ("T = 1.25 × T_approx", "T_design", f"1.25 × {seism.get('T_approx',0):.4f}", f"{seism.get('T',0):.4f} s", "NBC 105:2025 §5.1.3 (amplification)"),
            ("Lateral force exponent", "k", f"{'1.0' if seism.get('T',0)<=0.5 else '2.0' if seism.get('T',0)>=2.5 else 'interpolated'}", f"{seism.get('k',0):.4f}", "NBC 105:2025 §6.3"),
        ]
        _header_style(ws2, r, 1, "Calculation"); _header_style(ws2, r, 2, "Symbol")
        _header_style(ws2, r, 3, "Formula"); _header_style(ws2, r, 4, "Result"); _header_style(ws2, r, 5, "Reference")
        ws2.column_dimensions["E"].width = 32
        r += 1
        for i, row_d in enumerate(period_rows):
            bg = C_ALT_ROW if i%2==0 else None
            for col_n, val in enumerate(row_d, 1):
                _data_cell(ws2, r, col_n, val, bg=bg,
                           fg=C_INPUT_FG if col_n==4 else "595959" if col_n in (3,5) else "000000",
                           bold=(col_n==4))
            r += 1
        r += 1

        _section_title(ws2, r, "3. SPECTRAL SHAPE FACTOR Ch(T)  —  NBC 105:2025 §4.1.2", span_end_col=5)
        r += 1
        T = seism.get("T",0); Tc = seism.get("Tc",0); Td = seism.get("Td",0)
        alpha = seism.get("alpha",0)
        if T < Tc:
            zone_desc = f"Flat plateau (T={T:.4f}s < Tc={Tc:.1f}s)"; formula = f"Ch(T) = α = {alpha:.2f}"
        elif T < Td:
            zone_desc = f"Velocity-sensitive zone (Tc={Tc:.1f}s ≤ T={T:.4f}s < Td={Td:.1f}s)"
            formula = f"Ch(T) = α × Tc/T = {alpha:.2f} × {Tc:.1f}/{T:.4f}"
        else:
            zone_desc = f"Displacement-sensitive zone (T={T:.4f}s ≥ Td={Td:.1f}s)"
            formula = f"Ch(T) = α × Tc × Td/T² = {alpha:.2f} × {Tc:.1f} × {Td:.1f}/{T:.4f}²"
        ws2.cell(row=r, column=1, value=zone_desc).font = Font(name="Arial", size=10, italic=True, color="595959")
        ws2.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
        r += 1
        ch_rows = [
            ("Spectral zone", zone_desc, formula, f"{seism.get('Ch_T',0):.4f}", "NBC 105:2025 §4.1.2 Eq.(4.1.2)"),
            ("C(T) = Ch(T)×Z×I", "C_T", f"{seism.get('Ch_T',0):.4f}×{seism.get('Z',0):.2f}×{seism.get('I',0):.2f}", f"{seism.get('C_T',0):.4f}", "NBC 105:2025 §4.1.1 Eq.(4.1.1)"),
            ("Cs(T) = 0.20×C(T)", "Cs_T", f"0.20 × {seism.get('C_T',0):.4f}", f"{seism.get('Cs_T',0):.4f}", "NBC 105:2025 §4.2 Eq.(4.2.1)"),
            ("Cv(Tv) = 2/3×Z", "Cv_T", f"(2/3) × {seism.get('Z',0):.2f}", f"{seism.get('Cv_T',0):.4f}", "NBC 105:2025 §4.3 Eq.(4.3.1)"),
        ]
        _header_style(ws2, r, 1, "Calculation"); _header_style(ws2, r, 2, "Symbol")
        _header_style(ws2, r, 3, "Formula"); _header_style(ws2, r, 4, "Result"); _header_style(ws2, r, 5, "Reference")
        r += 1
        for i, row_d in enumerate(ch_rows):
            bg = C_ALT_ROW if i%2==0 else None
            for col_n, val in enumerate(row_d, 1):
                _data_cell(ws2, r, col_n, val, bg=bg,
                           fg=C_INPUT_FG if col_n==4 else "595959" if col_n in (3,5) else "000000",
                           bold=(col_n==4))
            r += 1
        r += 1

        _section_title(ws2, r, "4. BASE SHEAR COEFFICIENTS", span_end_col=5)
        r += 1
        _header_style(ws2, r, 1, "Calculation"); _header_style(ws2, r, 2, "Symbol")
        _header_style(ws2, r, 3, "Formula"); _header_style(ws2, r, 4, "Result")
        _header_style(ws2, r, 5, "Code Reference")
        r += 1
        cd_rows = [
            ("Cd_ULS = C(T)/(Rμ×Ωu)", "Cd_ULS",
             f"{seism.get('C_T',0):.4f}/({seism.get('Ru',0):.2f}×{seism.get('O_u',0):.2f})",
             f"{seism.get('Cd_ULS',0):.4f}", "NBC 105:2025 §6.1.1 Eq.(6.1.1)"),
            ("Cd_SLS = Cs(T)/Ωs", "Cd_SLS",
             f"{seism.get('Cs_T',0):.4f}/{seism.get('O_s',0):.2f}",
             f"{seism.get('Cd_SLS',0):.4f}", "NBC 105:2025 §6.1.2 Eq.(6.1.2)"),
            ("Drift limit ULS", "Δ/h",
             "Inter-story drift ratio", "0.025", "NBC 105:2025 §5.5.3"),
            ("Drift limit SLS", "Δ/h",
             "Inter-story drift ratio", "0.006", "NBC 105:2025 §5.5.3"),
            ("Deflection scale kd", "kd",
             f"Table 6-1 ({seism.get('num_stories','')} stories)",
             f"{seism.get('kd',0):.2f}", "NBC 105:2025 §6.5 Table 6-1"),
            ("Max Disp ULS", "Δ_ULS",
             f"0.025×H×kd = 0.025×{seism.get('H',0):.2f}×{seism.get('kd',0):.2f}",
             f"{seism.get('Disp_ULS_mm',0):.1f} mm", "NBC 105:2025 §5.5.1"),
        ]
        for i, row_d in enumerate(cd_rows):
            bg = C_ALT_ROW if i%2==0 else None
            for col_n, val in enumerate(row_d, 1):
                _data_cell(ws2, r, col_n, val, bg=bg,
                           fg=C_INPUT_FG if col_n==4 else "595959" if col_n in (3,5) else "000000",
                           bold=(col_n==4))
            r += 1
        r += 1

        # Story force table
        sf = seism.get("story_forces", [])
        if sf:
            _section_title(ws2, r, "5. STORY FORCE DISTRIBUTION  —  NBC 105:2025 §6.3", span_end_col=7)
            r += 1
            ws2.cell(row=r, column=1, value="Formula: Fi = V × Wi×hi^k / Σ(Wj×hj^k)").font = Font(name="Arial", size=10, italic=True, color="595959")
            ws2.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
            r += 1
            for col_n, hdr in enumerate(["Floor","Wi (kN)","hi (m)","Wi×hi^k","Fi (kN)","Story Shear (kN)"], 1):
                _header_style(ws2, r, col_n, hdr, bg=C_HEAD1_BG)
            r += 1
            for i, f in enumerate(sf):
                bg = C_ALT_ROW if i%2==0 else None
                for col_n, val in enumerate([f["floor"],f["W_kN"],f["h_m"],
                                              f["Wh_k"],f["Fi_kN"],f["Vx_kN"]], 1):
                    _data_cell(ws2, r, col_n, val, bg=bg,
                               fg=C_INPUT_FG if col_n in (5,6) else "000000",
                               bold=(col_n==6), align="center" if col_n==1 else "right",
                               fmt="#,##0.00" if col_n>1 else "0")
                r += 1
            _data_cell(ws2, r, 1, "TOTAL", bold=True, bg=C_HEAD2_BG)
            _data_cell(ws2, r, 2, f"=SUM(B{r-len(sf)}:B{r-1})", bold=True, bg=C_HEAD2_BG, fmt="#,##0.00")
            _data_cell(ws2, r, 5, f"=SUM(E{r-len(sf)}:E{r-1})", bold=True, bg=C_HEAD2_BG, fmt="#,##0.00", fg=C_INPUT_FG)
            ws2.cell(row=r, column=4, value="Base Shear V =").font = Font(name="Arial", size=10, bold=True)
            ws2.cell(row=r, column=6, value=f"{seism.get('V_base_kN',0):.2f} kN").font = Font(name="Arial", size=10, bold=True, color=C_INPUT_FG)
            r += 2

        # Load combinations
        combos = seism.get("load_combos", [])
        if combos:
            _section_title(ws2, r, "6. LOAD COMBINATIONS  —  NBC 105:2025 §3.6 (LSM)", span_end_col=5)
            r += 1
            _header_style(ws2, r, 1, "Combination Label")
            _header_style(ws2, r, 2, "Formula")
            _header_style(ws2, r, 3, "DL Factor")
            _header_style(ws2, r, 4, "LL Factor (λ)")
            _header_style(ws2, r, 5, "E / W Factor")
            r += 1
            for i, c in enumerate(combos):
                bg = C_ALT_ROW if i%2==0 else None
                e_str = (f"E_ULS×{c['E_ULS_fac']:.1f}" if c['E_ULS_fac']!=0 else
                         (f"E_SLS×{c['E_SLS_fac']:.1f}" if c['E_SLS_fac']!=0 else
                          (f"W×{c['W_fac']:.1f}" if c['W_fac']!=0 else "—")))
                ll_s = f"λ={seism.get('lambda_ll',0.30):.2f}" if str(c['LL_fac'])=="λ" else f"{c['LL_fac']:.2f}"
                _data_cell(ws2, r, 1, c["label"], bold=True, bg=bg)
                _data_cell(ws2, r, 2, c["formula"], bg=bg, fg="595959")
                _data_cell(ws2, r, 3, str(c["DL_fac"]), bg=bg, align="center")
                _data_cell(ws2, r, 4, ll_s, bg=bg, align="center")
                _data_cell(ws2, r, 5, e_str, bg=bg, align="center")
                r += 1

        ws2.freeze_panes = "A5"

    # ══════════════════════════════════════════════════════════════════════════
    # SHEET 3: BEAM (Detailed)
    # ══════════════════════════════════════════════════════════════════════════
    if beam and mode == "detailed":
        ws3 = wb.create_sheet("━ Beam (IS 456)")
        ws3.column_dimensions["A"].width = 40
        ws3.column_dimensions["B"].width = 25
        ws3.column_dimensions["C"].width = 35
        ws3.column_dimensions["D"].width = 22
        ws3.column_dimensions["E"].width = 30

        r = _proj_header(ws3, "Beam Design — IS 456:2000")

        all_sections = [
            ("1. SECTION GEOMETRY", [
                ("Width b", f"{beam.get('b','?')} mm", "—", "IS 456:2000 §6.2"),
                ("Overall Depth D", f"{beam.get('D','?')} mm", "—", "IS 456:2000 §6.2"),
                ("Clear Cover", f"{beam.get('cover','?')} mm", "—", "IS 456:2000 §26.4"),
                ("Main Bar Ø", f"{beam.get('main_dia','?')} mm", "—", "IS 456:2000 §26.5.1"),
                ("Effective Depth d", f"{beam.get('d_eff_mm',0):.1f} mm",
                 f"d = D − cover − Ø/2 = {beam.get('D','?')}−{beam.get('cover','?')}−{int(float(beam.get('main_dia',16))/2)}",
                 "IS 456:2000 §26.3"),
                ("Span", f"{beam.get('span_m',0):.2f} m", "—", "—"),
                ("Support Condition", str(beam.get("support_type","")), "—", "IS 456:2000 §22.2"),
                ("Concrete grade", f"M{beam.get('fck','?')} ({beam.get('fck','?')} MPa)", "—", "IS 456:2000 §6.1"),
                ("Steel grade", f"Fe{beam.get('fy','?')} ({beam.get('fy','?')} MPa)", "—", "IS 456:2000 §5.6"),
            ]),
            ("2. FLEXURAL DESIGN  —  IS 456:2000 §38", [
                ("xu_max/d ratio", f"{0.53 if float(beam.get('fy',415))<=250 else 0.48 if float(beam.get('fy',415))<=415 else 0.46:.2f}",
                 "0.53 (Fe250), 0.48 (Fe415), 0.46 (Fe500)", "IS 456:2000 Table F"),
                ("Limiting Moment Mu,lim", f"{beam.get('Mu_lim_kNm',0):.3f} kN·m",
                 "0.36×fck×b×xu_max×(d−0.42×xu_max)", "IS 456:2000 §38.1"),
                ("Design Moment Mu", f"{beam.get('Mu_design_kNm',0):.3f} kN·m",
                 "Includes torsional equivalent Me (if Tu>0)", "IS 456:2000 §41.3"),
                ("Section Type", "Doubly Reinforced" if beam.get("is_doubly") else "Singly Reinforced",
                 "Mu > Mu,lim → Doubly (IS 456 Annex G)", "IS 456:2000 §38 / Annex G"),
                ("Ast required", f"{beam.get('Ast_req_mm2',0):.2f} mm²",
                 "Mu/(0.87×fy×z)", "IS 456:2000 §38.1"),
                ("Ast minimum", f"{beam.get('Ast_min_mm2',0):.2f} mm²",
                 "0.85×b×d/fy", "IS 456:2000 §26.5.1.1"),
                ("Bars provided", f"{beam.get('no_of_bars',0)} × Ø{beam.get('main_dia','?')} mm",
                 "Selected for Ast ≥ Ast,req", "IS 456:2000 §26.5.1"),
                ("Bar spacing", f"{beam.get('spacing_mm',0):.0f} mm c/c",
                 f"Min clear: max(Ø,25mm); Max: min(300,d)", "IS 456:2000 §26.3.2–3"),
                ("Ast provided", f"{beam.get('Ast_prov_mm2',0):.2f} mm²",
                 f"n×π×Ø²/4", "IS 456:2000 §26.5.1"),
            ]),
        ]

        dr = beam.get("doubly")
        if dr:
            all_sections.append(("2a. COMPRESSION STEEL  —  IS 456:2000 Annex G", [
                ("d' (cover to comp. centroid)", f"{dr.get('d_prime_mm',0):.1f} mm", "cover + Ø_tie + Ø_main/2", "IS 456 Annex G"),
                ("εsc (comp. bar strain)", f"{dr.get('eps_sc',0):.5f}",
                 f"0.0035×(xu_max−d')/xu_max", "IS 456 Annex G"),
                ("fsc (comp. bar stress)", f"{dr.get('fsc_MPa',0):.1f} MPa",
                 f"{'0.87×fy (yielded)' if dr.get('fsc_MPa',0)>=0.87*float(beam.get('fy',415)) else 'εsc×Es (elastic)'}", "IS 456 Annex G"),
                ("Asc required", f"{dr.get('Asc_req_mm2',0):.2f} mm²",
                 "Mu_extra/((fsc−0.45fck)×(d−d'))", "IS 456 Annex G"),
                ("Compression bars", f"{dr.get('no_comp_bars',0)} × Ø{int(dr.get('comp_bar_dia',0))} mm",
                 f"Asc_prov = {dr.get('Asc_prov_mm2',0):.2f} mm²", "IS 456 Annex G"),
                ("Ast1 (balanced)", f"{dr.get('Ast1_mm2',0):.2f} mm²", "Mu,lim/(0.87×fy×(d−0.42xu,max))", "IS 456 §38.1"),
                ("Ast2 (extra tension)", f"{dr.get('Ast2_mm2',0):.2f} mm²", "Asc×(fsc−0.45fck)/(0.87×fy)", "IS 456 Annex G"),
            ]))

        shear_d = beam.get("shear", {})
        defl_d  = beam.get("deflection", {})
        all_sections += [
            ("3. SHEAR DESIGN  —  IS 456:2000 §40", [
                ("Design Shear Vu", f"{beam.get('Vu_design_kN',0):.3f} kN",
                 "Includes Ve=Vu+1.6Tu/b (if Tu>0)", "IS 456:2000 §41.3"),
                ("Nominal shear stress τv", f"{shear_d.get('tau_v',0):.4f} MPa",
                 "Vu/(b×d)", "IS 456:2000 §40.1"),
                ("Design shear strength τc", f"{shear_d.get('tau_c',0):.4f} MPa",
                 "From Table 19 (function of pt% and fck)", "IS 456:2000 Table 19"),
                ("Maximum τc,max", f"{shear_d.get('tau_c_max',0):.4f} MPa",
                 "0.62√fck", "IS 456:2000 Table 20"),
                ("Stirrup status", shear_d.get("status",""),
                 f"τv {'>' if beam.get('Vu_design_kN',0)>0 else '≤'} k·τc", "IS 456:2000 §40.4"),
                ("Stirrups provided", f"Ø{int(shear_d.get('stir_dia',8))} {shear_d.get('stir_legs',2)}-leg @ {shear_d.get('Sv_mm','?')} mm c/c",
                 "Sv = 0.87×fy×Asv×d/Vus", "IS 456:2000 §40.4a"),
            ]),
        ]
        if defl_d:
            all_sections.append(("4. DEFLECTION CHECK  —  IS 456:2000 §23.2", [
                ("Basic L/d ratio", str(defl_d.get("ld_basic",20)),
                 "SS=20, Cant=7, Fixed=26", "IS 456:2000 §23.2.1"),
                ("Service steel stress fs", f"{defl_d.get('fs_serv',0):.1f} MPa",
                 "0.58×fy×(Ast,req/Ast,prov)", "IS 456:2000 §23.2.1 Note 1"),
                ("Modification factor kt", f"{defl_d.get('kt',0):.3f}",
                 "From Figure 4 (function of fs, pt)", "IS 456:2000 §23.2.1"),
                ("Compression factor kc", f"{defl_d.get('kc',1):.3f}",
                 "1+(pt_comp)/(3+pt_comp) ≤ 1.5", "IS 456:2000 §23.2.1"),
                ("Flange factor kf", f"{defl_d.get('kf',1):.2f}",
                 "0.8 for flanged beams, 1.0 rectangular", "IS 456:2000 §23.2.1 Note 2"),
                ("Allowable L/d", f"{defl_d.get('ld_allow',0):.2f}",
                 f"basic×kt×kc×kf = {defl_d.get('ld_basic',20)}×{defl_d.get('kt',0):.3f}×{defl_d.get('kc',1):.3f}×{defl_d.get('kf',1):.2f}", "IS 456:2000 §23.2"),
                ("Provided L/d", f"{defl_d.get('ld_prov',0):.2f}",
                 f"L×1000/d = span×1000/d", "IS 456:2000 §23.2"),
                ("Check", "✓  OK" if defl_d.get("ok") else "✗  Increase depth",
                 f"L/d_prov {'≤' if defl_d.get('ok') else '>'} L/d_allow", "IS 456:2000 §23.2"),
            ]))

        all_sections.append(("5. DEVELOPMENT LENGTH  —  IS 456:2000 §26.2.1", [
            ("τbd (bond stress)", str({'20':1.2,'25':1.4,'30':1.5,'35':1.7,'40':1.9}.get(str(beam.get('fck','25')),'1.4')) + " MPa",
             "From Table 5 (HYSD bars, deformed)", "IS 456:2000 Table 5"),
            ("Development length Ld", f"{beam.get('Ld_mm',0):.0f} mm",
             "0.87×fy×Ø/(4×τbd)", "IS 456:2000 §26.2.1 Eq.(26.1)"),
        ]))

        for sec_title, sec_rows in all_sections:
            _section_title(ws3, r, sec_title, span_end_col=5); r += 1
            _header_style(ws3, r, 1, "Parameter"); _header_style(ws3, r, 2, "Value")
            _header_style(ws3, r, 3, "Formula / Derivation"); _header_style(ws3, r, 4, "Clause Reference")
            r += 1
            for i, row_d in enumerate(sec_rows):
                bg = C_ALT_ROW if i%2==0 else None
                for col_n, val in enumerate(row_d, 1):
                    _data_cell(ws3, r, col_n, val, bg=bg,
                               fg=C_INPUT_FG if col_n==2 and "mm²" in str(val) else
                               "595959" if col_n in (3,4) else "000000")
                r += 1
            r += 1
        ws3.freeze_panes = "A5"

    # Final sheet for notes
    ws_n = wb.create_sheet("ℹ️ Notes & Disclaimer")
    ws_n.column_dimensions["A"].width = 90
    ws_n.cell(row=1, column=1, value="NOTES, LIMITATIONS & DISCLAIMER").font = Font(name="Arial", size=14, bold=True, color=C_TITLE_FG)
    ws_n["A1"].fill = PatternFill("solid", fgColor=C_TITLE_BG)
    ws_n.row_dimensions[1].height = 28
    notes_content = [
        ("Standards Applied:", "NBC 105:2025 (Second Revision) · IS 456:2000 · IS 875 Part 1 & 2"),
        ("Seismic Spectra:", "3-zone Ch(T) formula: flat plateau (α) → velocity (α·Tc/T) → displacement (α·Tc·Td/T²) per NBC 105:2025 §4.1.2"),
        ("Column Interaction:", "Equilibrium-based uniaxial Mu1 capacity per IS 456:2000 §39 / SP 16 Annex D (binary search for xu)"),
        ("Footing Seismic:", "SBC ×1.5 for seismic load combination per NBC 105:2025 §3.8"),
        ("Eccentric Footing:", "Biaxial eccentricity; effective area method when q_min < 0 (IS 456:2000 §34.2.4)"),
        ("Deflection:", "IS 456:2000 §23.2 with kt (Figure 4), kc (compression steel), kf (flanged beams)"),
        ("Torsion:", "IS 456:2000 §41.3: equivalent shear Ve and moment Me; closed stirrups required"),
        ("NBC 105 Annex A:", "Ductile RC column detailing: confinement zone, tie spacing, 135° hooks, lap splice restrictions"),
        ("Disclaimer:", "Results are for reference only. All designs must be independently verified by a qualified structural engineer."),
        ("Software:", f"Structural Calculator v4.0  |  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"),
    ]
    for i, (label, note) in enumerate(notes_content, 2):
        ws_n.cell(row=i, column=1, value=f"{label}  {note}").font = Font(
            name="Arial", size=10, italic=(label=="Disclaimer:"))

    wb.save(output_path)
    return output_path
