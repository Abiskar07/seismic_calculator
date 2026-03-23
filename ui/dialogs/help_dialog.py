"""ui/dialogs/help_dialog.py — Complete help documentation."""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QTabWidget # type: ignore

HELP_TABS = {
"Overview & Quick Start": """
<style>
body{font-family:'Segoe UI',Arial,sans-serif;font-size:10pt;line-height:1.5;}
h2{color:#2E75B6;border-bottom:2px solid #2E75B6;padding-bottom:4px;}
h3{color:#31849B;margin-top:12px;}
code{background:#E8F0F8;padding:1px 5px;border-radius:3px;font-family:Consolas,monospace;}
table{border-collapse:collapse;width:100%;margin:8px 0;}
th{background:#2E75B6;color:#fff;padding:5px 10px;text-align:left;}
td{padding:4px 10px;border:1px solid #C8D8E8;}tr:nth-child(even){background:#F0F7FF;}
.ok{color:#1B5E20;font-weight:bold;}.fail{color:#7F0000;font-weight:bold;}
.info{color:#0D47A1;font-weight:bold;}
</style>
<h2>{app_name} {app_version} — Help Documentation</h2>
<p><b>Standards:</b> NBC 105:2025 (Second Revision) · IS 456:2000 · IS 875 Part 1, 2 &amp; 3</p>
<p><b>Priority:</b> NBC 105:2025 takes precedence; IS codes apply where NBC is silent.</p>

<h3>Quick Start</h3>
<ol>
<li>Fill in <b>Project Information</b> at the top (Project name, Engineer, Job No.)</li>
<li>Go to <b>Base Shear</b> tab → select zone, soil, system → results auto-update</li>
<li>Enter floor weights (comma-separated) to get <b>Story Force Distribution</b></li>
<li>Design beam, column, footing in their respective tabs</li>
<li><code>Ctrl+E</code> → Export Report → choose <b>Detailed</b> or <b>Summary</b>, <b>Excel</b> or <b>Word</b></li>
</ol>

<h3>Application Tabs</h3>
<table>
<tr><th>Tab</th><th>Standard</th><th>Purpose</th></tr>
<tr><td>Base Shear</td><td>NBC 105:2025</td>
    <td>ESM base shear, period, spectral shape, story force distribution, load combinations</td></tr>
<tr><td>Load Calc</td><td>IS 875 Pt 1 &amp; 2</td>
    <td>Dead loads (wall, slab, finish), imposed live loads by occupancy</td></tr>
<tr><td>Slab Design</td><td>IS 456:2000</td>
    <td>Two-way slab coefficients (Table 26), Ast, deflection, shear checks</td></tr>
<tr><td>Beam Design</td><td>IS 456:2000</td>
    <td>Singly/doubly reinforced, T-beam, torsion §41, deflection, development length</td></tr>
<tr><td>Column Design</td><td>IS 456:2000 + NBC 105 Annex A</td>
    <td>Biaxial interaction (equilibrium method), slender columns, ductile detailing</td></tr>
<tr><td>Footing Design</td><td>IS 456:2000 §34 + NBC 105:2025 §3.8</td>
    <td>Concentric, <b>eccentric</b>, and <b>combined</b> footings; punching, shear, Ld</td></tr>
<tr><td>Staircase</td><td>IS 456:2000 §33</td>
    <td>Dog-legged staircase (waist-slab method), step geometry, Ast, deflection</td></tr>
<tr><td>Wind Load</td><td>IS 875 Part 3:2015</td>
    <td>Design wind speed Vz, pressure pz, pd, Cpe coefficients, story wind forces</td></tr>
<tr><td>Settings</td><td>—</td>
    <td>Theme, rounding, auto-calculate, export folder — saved to disk</td></tr>
</table>

<h3>Export Formats</h3>
<table>
<tr><th>Format</th><th>Mode</th><th>Contents</th></tr>
<tr><td rowspan=2>Excel (.xlsx)</td>
    <td>Detailed</td><td>6 sheets: Summary + Seismic (full formulas + story forces + load combos) + Beam + Column + Foundation + Notes</td></tr>
<tr><td>Summary</td><td>1 sheet: all key results with status indicators and clause references</td></tr>
<tr><td rowspan=2>Word (.docx)</td>
    <td>Detailed</td><td>Cover page + TOC + full calculations with formula derivations per clause. Suitable for design report submission.</td></tr>
<tr><td>Summary</td><td>Cover page + compact result tables. Quick review format.</td></tr>
<tr><td>Text (.txt)</td><td>Both</td><td>Plain ASCII report with story force table included</td></tr>
</table>

""",

"NBC 105:2025 Implementation": """
<style>
body{font-family:'Segoe UI',Arial,sans-serif;font-size:10pt;line-height:1.5;}
h2{color:#2E75B6;border-bottom:2px solid #2E75B6;padding-bottom:4px;}
h3{color:#31849B;margin-top:12px;}
code{background:#E8F0F8;padding:1px 5px;border-radius:3px;font-family:Consolas,monospace;}
table{border-collapse:collapse;width:100%;margin:8px 0;}
th{background:#2E75B6;color:#fff;padding:5px 10px;}
td{padding:4px 10px;border:1px solid #C8D8E8;}tr:nth-child(even){background:#F0F7FF;}
</style>
<h2>NBC 105:2025 Second Revision — Implementation Details</h2>

<h3>Fully Implemented Clauses</h3>
<table>
<tr><th>Clause</th><th>Description</th><th>Formula / Note</th></tr>
<tr><td>§4.1.2</td><td>Spectral shape factor Ch(T)</td>
    <td>3-zone: flat (T&lt;Tc) → α; velocity (Tc≤T&lt;Td) → α·Tc/T; displacement (T≥Td) → α·Tc·Td/T²</td></tr>
<tr><td>§4.2</td><td>SLS elastic site spectra</td><td>Cs(T) = 0.20 × C(T)</td></tr>
<tr><td>§4.3</td><td>Vertical elastic spectra</td><td>Cv(Tv) = 2/3 × Z</td></tr>
<tr><td>§5.1.2–3</td><td>Fundamental period</td><td>T = 1.25 × kt × H^(3/4)</td></tr>
<tr><td>§5.1.2–3</td><td>Fundamental period</td><td>T = 1.25 × kt × H^(3/4)  (§5.1.3 amplification)</td></tr>
<tr><td>§5.3</td><td>Structural system properties</td><td>All systems: Rμ, Ωu, Ωs, kt (Table 5-2)</td></tr>
<tr><td>§5.4.1.1–2</td><td>Vertical irregularity</td><td>Weak story (&lt;80%), soft story (&lt;70%)</td></tr>
<tr><td>§5.4.1.5</td><td>Mass irregularity</td><td>Adjacent mass ratio &gt;1.5 → irregular</td></tr>
<tr><td>§5.4.2.1–2</td><td>Torsional irregularity</td><td>&gt;1.5 → irregular; &gt;2.5 → extreme (not permitted)</td></tr>
<tr><td>§5.5.2</td><td>Building separation</td><td>Δgap = √(Δ1² + Δ2²)  SRSS method</td></tr>
<tr><td>§5.5.3</td><td>Drift limits</td><td>ULS: 0.025; SLS: 0.006 (inter-story ratio)</td></tr>
<tr><td>§5.6</td><td>Accidental eccentricity</td><td>±0.05b (reduced from ±0.10b in old code)</td></tr>
<tr><td>§6.1.1–2</td><td>Base shear coefficients</td><td>Cd_ULS = C(T)/(Rμ·Ωu); Cd_SLS = Cs(T)/Ωs</td></tr>
<tr><td>§6.3</td><td>Story force distribution</td><td>Fi = V · Wi·hi^k / Σ(Wj·hj^k)</td></tr>
<tr><td>§6.5</td><td>Deflection scale factor kd</td><td>Table 6-1 by number of stories</td></tr>
<tr><td>§3.6</td><td>LSM load combinations</td><td>8 combinations including 0.9DL±E, 1.4DL, 1.2DL+1.6LL</td></tr>
<tr><td>§3.7</td><td>WSM load combinations</td><td>3 combinations</td></tr>
<tr><td>§3.8</td><td>Seismic SBC allowance</td><td>Footing SBC × 1.5 for seismic combinations</td></tr>
<tr><td>§10</td><td>Parts &amp; components force</td><td>Fp = Cd(T)·Cp·(1+z/H)·Ip/μp·Wp</td></tr>
<tr><td>Annex A</td><td>Ductile RC detailing — Columns</td>
    <td>Confinement zone lo, tie spacing sc, Ash ≥ 0.09·s·h"·fck/fy, 135° hooks, lap restrictions</td></tr>
<tr><td>Table 4-1</td><td>Soil parameters (K removed)</td>
    <td>Ta, Tc, Td, α only; K parameter discontinued in 2025 revision</td></tr>
<tr><td>Table 4-3</td><td>KTM valley Soil D zones</td><td>Ward-level warning if Soil D not confirmed by Vs30</td></tr>
<tr><td>Table 5-2</td><td>All structural systems</td><td>Complete: MRF, Wall, Dual, Gravity, Masonry systems</td></tr>
</table>

<h3>Key Changes vs. NBC 105:2020 (First Revision)</h3>
<table>
<tr><th>#</th><th>Change</th><th>Impact</th></tr>
<tr><td>1</td><td>Spectral shape factor — 3-zone formula replaces 2-zone</td><td>Displacement-sensitive zone added for long-period structures</td></tr>
<tr><td>2</td><td>K parameter removed from Table 4-1</td><td>Simplified soil characterisation; old calcs with K are invalid</td></tr>
<tr><td>3</td><td>Period amplification ×1.25 mandatory</td><td>T_design = 1.25 × T_approx</td></tr>
<tr><td>4</td><td>Accidental eccentricity: ±0.10b → ±0.05b</td><td>Reduced torsional demand</td></tr>
<tr><td>5</td><td>Eccentrically Braced Steel Frame kt: 0.085 → 0.075</td><td>Longer computed period</td></tr>
<tr><td>6</td><td>Masonry wall naming update</td><td>"…with Horizontal Bands &amp; Vertical Bars"</td></tr>
</table>
""",

"IS 456:2000 Coverage": """
<style>
body{font-family:'Segoe UI',Arial,sans-serif;font-size:10pt;line-height:1.5;}
h2{color:#2E75B6;border-bottom:2px solid #2E75B6;padding-bottom:4px;}
h3{color:#31849B;margin-top:12px;}
code{background:#E8F0F8;padding:1px 5px;border-radius:3px;}
table{border-collapse:collapse;width:100%;margin:8px 0;}
th{background:#2E75B6;color:#fff;padding:5px 10px;}
td{padding:4px 10px;border:1px solid #C8D8E8;}tr:nth-child(even){background:#F0F7FF;}
</style>
<h2>IS 456:2000 — Implementation Coverage</h2>

<h3>Beam Design</h3>
<table>
<tr><th>Clause</th><th>Description</th><th>Status</th></tr>
<tr><td>§23.2</td><td>Deflection: basic L/d × kt × kc × kf</td><td>✅ Full (kt Fig.4, kc, kf for flanged)</td></tr>
<tr><td>§26.2.1</td><td>Development length Ld</td><td>✅ τbd by fck from Table 5</td></tr>
<tr><td>§26.3 / Annex B</td><td>T-beam/L-beam effective flange width bf</td><td>✅</td></tr>
<tr><td>§26.5.1.1</td><td>Min/Max longitudinal steel</td><td>✅ 0.85/fy to 4%</td></tr>
<tr><td>§26.5.1.3</td><td>Side face reinforcement (D&gt;750mm)</td><td>✅</td></tr>
<tr><td>§38.1</td><td>Neutral axis depth, Mu,lim</td><td>✅ xu,max/d = 0.53/0.48/0.46</td></tr>
<tr><td>Annex G</td><td>Doubly-reinforced beam design</td><td>✅ εsc, fsc, Asc, Ast1+Ast2</td></tr>
<tr><td>§40</td><td>Shear: stirrup design</td><td>✅ τc Table 19, τc,max Table 20</td></tr>
<tr><td>§41.3–4</td><td>Torsion: Ve, Me, closed links</td><td>✅</td></tr>
<tr><td>§35.3</td><td>Crack width check (service stress)</td><td>✅ fs vs 240 MPa guidance</td></tr>
</table>

<h3>Column Design</h3>
<table>
<tr><th>Clause</th><th>Description</th><th>Status</th></tr>
<tr><td>§25.1.2</td><td>Slenderness classification (λ&gt;12 = slender)</td><td>✅</td></tr>
<tr><td>§25.4</td><td>Minimum eccentricity</td><td>✅ emin = max(L/500+D/30, 20mm)</td></tr>
<tr><td>§39.3</td><td>Pure axial capacity Pu,max</td><td>✅</td></tr>
<tr><td>§39.6</td><td>Biaxial interaction (Mux/Mux1)^αn + (Muy/Muy1)^αn ≤ 1</td>
    <td>✅ Equilibrium-based Mu1 (binary search for xu)</td></tr>
<tr><td>§39.7</td><td>Additional moments for slender columns</td><td>✅ Ma = k·Pu·D·λ²/2000</td></tr>
<tr><td>§26.5.3.1</td><td>Lateral ties: spacing, multi-leg arrangement</td><td>✅ Cross-tie count for &gt;4/6/8 bars</td></tr>
<tr><td>NBC 105 Annex A</td><td>Confinement zone lo, sc, Ash check</td><td>✅</td></tr>
</table>

<h3>Foundation Design</h3>
<table>
<tr><th>Clause</th><th>Description</th><th>Status</th></tr>
<tr><td>§34.1.3</td><td>Min. depth 300mm (RC)</td><td>✅ Enforced</td></tr>
<tr><td>§34.2.4</td><td>Effective area method (tension zone)</td><td>✅ Eccentric footing</td></tr>
<tr><td>§34.4.1</td><td>Bending moment at column face</td><td>✅ Both directions</td></tr>
<tr><td>§34.4.2a</td><td>One-way shear at d from face</td><td>✅</td></tr>
<tr><td>§31.6 / §34.4.2b</td><td>Punching shear at d/2 from face</td><td>✅ τc=0.25√fck</td></tr>
<tr><td>§34.4.3</td><td>Development length check</td><td>✅</td></tr>
<tr><td>§34.4.4</td><td>Column-footing bearing stress</td><td>✅ √(A1/A2) factor</td></tr>
<tr><td>NBC 105:2025 §3.8</td><td>Seismic SBC +50%</td><td>✅</td></tr>
</table>

<h3>Staircase Design</h3>
<table>
<tr><th>Clause</th><th>Description</th><th>Status</th></tr>
<tr><td>§33.1</td><td>Effective span (dog-legged)</td><td>✅</td></tr>
<tr><td>§33.2</td><td>Self-weight of steps (0.5×R×γ)</td><td>✅</td></tr>
<tr><td>§23.2</td><td>Deflection check</td><td>✅</td></tr>
<tr><td>§26.5.2</td><td>Distribution steel: 0.12%bD (Fe415)</td><td>✅</td></tr>
</table>
""",

"Keyboard Shortcuts": """
<style>
body{font-family:'Segoe UI',Arial,sans-serif;font-size:10pt;line-height:1.6;}
h2{color:#2E75B6;border-bottom:2px solid #2E75B6;padding-bottom:4px;}
h3{color:#31849B;margin-top:12px;}
code{background:#E8F0F8;padding:3px 8px;border-radius:4px;font-family:Consolas,monospace;font-size:10pt;}
table{border-collapse:collapse;width:100%;margin:8px 0;}
th{background:#2E75B6;color:#fff;padding:5px 12px;text-align:left;}
td{padding:5px 12px;border:1px solid #C8D8E8;}tr:nth-child(even){background:#F0F7FF;}
</style>
<h2>Keyboard Shortcuts</h2>
<table>
<tr><th>Shortcut</th><th>Action</th></tr>
<tr><td><code>Ctrl+1</code>…<code>Ctrl+9</code></td><td>Jump to tab 1–9</td></tr>
<tr><td><code>Ctrl+N</code></td><td>New project (clear all inputs)</td></tr>
<tr><td><code>Ctrl+O</code></td><td>Open project (JSON file)</td></tr>
<tr><td><code>Ctrl+S</code></td><td>Save project (JSON file)</td></tr>
<tr><td><code>Ctrl+E</code></td><td>Export report (Excel / Word / Text)</td></tr>
<tr><td><code>F5</code></td><td>Run all calculations</td></tr>
<tr><td><code>F1</code></td><td>This help dialog</td></tr>
<tr><td><code>Ctrl+H</code></td><td>About dialog</td></tr>
<tr><td><code>Ctrl+Q</code></td><td>Exit application</td></tr>
</table>

<h3>ft′in″ Dimension Input</h3>
<p>Any field labelled <b>[m]</b> or <b>[mm]</b> accepts imperial input. Press <code>Enter</code> to convert:</p>
<table>
<tr><th>You type</th><th>Converts to</th></tr>
<tr><td><code>5'6"</code></td><td>1.676 m</td></tr>
<tr><td><code>6'</code></td><td>1.829 m</td></tr>
<tr><td><code>12"</code></td><td>304.8 mm</td></tr>
<tr><td><code>8"</code></td><td>203.2 mm</td></tr>
</table>

<h3>Story Force Input</h3>
<p>On the <b>Base Shear</b> tab, enter per-floor seismic weights in the 
<b>Floor Weights</b> field as comma-separated values (bottom → top):</p>
<p><code>1200, 1200, 1200, 1000</code> → 4-story building, 3 floors × 1200 kN + roof 1000 kN</p>
<p>This unlocks the <b>Story Force Distribution table</b> per NBC 105:2025 §6.3.</p>

<h3>Footing Modes</h3>
<p>The <b>Footing Design</b> tab has three modes selectable by radio button:</p>
<ul>
<li><b>Concentric Isolated</b> — axial load only, symmetric pressure</li>
<li><b>Eccentric Isolated</b> — biaxial moments, kern check, effective area for uplift (IS 456 §34.2.4)</li>
<li><b>Combined Footing</b> — two columns, resultant centring, BMD, longitudinal + transverse Ast</li>
</ul>
""",
}


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        from constants import APP_NAME, APP_VERSION # type: ignore
        super().__init__(parent)
        self.setWindowTitle(f"Help — {APP_NAME} {APP_VERSION}")
        self.setModal(True)
        self.resize(860, 680)
        if parent and hasattr(parent, "styleSheet"):
            self.setStyleSheet(parent.styleSheet())
        lay = QVBoxLayout(self)
        tabs = QTabWidget()
        for title, html in HELP_TABS.items():
            txt = QTextEdit(readOnly=True)
            txt.setHtml(html.replace("{app_name}", APP_NAME).replace("{app_version}", APP_VERSION))
            tabs.addTab(txt, title)
        lay.addWidget(tabs)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        lay.addWidget(close)
