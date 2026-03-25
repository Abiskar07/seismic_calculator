# Structural Calculator v1.0.0

A comprehensive, open-source structural engineering calculator built in Python and PyQt6. Designed for speed, accuracy, and professional reporting, this application implements the latest provisions of **NBC 105:2025 (Second Revision)** and **IS 456:2000 (Indian Standard)** for RCC design.

> **Note:** NBC 105 takes priority for seismic base shear and structural analysis, while IS 456:2000 governs the concrete component design and detailing where NBC is silent..

---

## ✨ Key Features

- **Multi-Module Analysis**: Dedicated calculation engines for Seismic, Wind, Slabs, Beams, Columns, Staircases, and Foundations (Isolated & Combined).
- **Automated Code Compliance**: Built-in tables and data from IS 456:2000 (Table 19, Figure 4, Annex D-1.8) and NBC 105:2025.
- **Professional Reporting**: Export beautifully formatted, calculation-rich reports directly to **Microsoft Word (.docx)** and **Excel (.xlsx)**.
- **Unified UI Status Indicators**: Instantly identify passing or failing checks with standardized color-coded status badges (`OK ✓`, `REVISE ✗`, `WARN ⚠`).
- **Dark/Light Themes**: A modern, responsive Qt-based interface designed to reduce eye strain during long design sessions.

---

## 🚀 Recent Updates & Structural Audit

In the latest major release, the application underwent a rigorous structural audit and refinement process:
- **Slab Design**: Implemented strict deflection checks according to IS 456 §24.1 (with precise $k_t$ modification factor interpolation from Figure 4) and automated torsional reinforcement detailing at corners per Annex D-1.8.
- **Combined & Eccentric Footings**: Added support for eccentric loading and combined footing logic, ensuring gross vs. net soil pressures are calculated correctly for SBC checks and structural shear/bending.
- **Column Interaction**: Upgraded the column capacity engine to perform exact uniaxial equilibrium checks, accounting for tension-face steel compression resistance.
- **UI Consistency**: Standardized the rendering of all results tables across all modules to ensure a unified user experience.

---

## 📐 Supported Design Modules

| Module | Standard | Capabilities |
|--------|----------|--------------|
| 🌍 **Seismic (Base Shear)** | `NBC 105:2025` | Equivalent Static Method (ESM), Spectral Shape Factor, Story Force Distribution, Deflection scaling. |
| 🌪️ **Wind Load** | `IS 875 Part 3` | Basic wind speed, terrain category, topography factors, design wind pressure calculations. |
| 📦 **Load Calc** | `IS 875 Part 2` | Wall line loads, floor finishes, live loads mapping based on building type. |
| ▦ **Slab Design** | `IS 456:2000` | Two-way coefficient method, bending moments, $A_{st}$, deflection checks, and corner torsional detailing. |
| ━ **Beam Design** | `IS 456:2000` | Singly & doubly reinforced sections, T/L-beams, shear/torsion design, development length, crack width. |
| ⬛ **Column Design** | `IS 456:2000` | Biaxial interaction, slenderness effects, tie spacing, and ductile detailing limits. |
| 🏗️ **Staircase** | `IS 456:2000` | Dog-legged/open-well geometry, effective span calculation, loading, and flexural design. |
| 🪨 **Foundation** | `IS 456:2000` | Isolated and Combined footings. Bearing pressure, bending moment, one-way shear, and two-way (punching) shear. |

---

## 🛠️ Installation & Quick Start

The application requires **Python 3.10+**.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/seismic_calculator.git
   cd seismic_calculator
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Main dependencies include `PyQt6` for the GUI and `python-docx` / `openpyxl` for report generation).*

3. **Run the application:**
   ```bash
   python main.py
   ```

---

## 📄 Reporting & Export

Press `Ctrl+E` or use the **File > Export Report** menu to generate a complete design package.
The application bundles all active tab results, design inputs, structural notes, and warnings into:
- **Microsoft Word (.docx)**: Perfect for submission to municipalities or peer review.
- **Microsoft Excel (.xlsx)**: Ideal for spreadsheet integration and BOQ estimation.
- **Plain Text (.txt)**: For quick copy-pasting into other software.

---

## 🚧 Known Limitations (Future Work)

- One-way slab design (auto-detect Ly/Lx > 2)
- Flat slab (IS 456 §31.5)
- Pile cap foundation
- Spiral column (IS 456 §26.5.3.2)
- Retaining wall design

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+1...7` | Instantly switch between design modules |
| `Ctrl+N / O / S` | New / Open / Save project configuration |
| `Ctrl+E` | Open Export Dialog |
| `F1` | Open Help Documentation |

---

## 📁 Architecture Overview

The codebase is strictly separated into UI rendering, calculation engines, and code-mandated constants to ensure testability and reliability.

```text
seismic_calculator/
├── main.py                        ← Application entry point
├── README.md                      ← Documentation
├── requirements.txt               ← Dependencies
├── constants/                     ← Immutable code data (No UI dependencies)
│   ├── is456_data.py              ← Material properties, shear tables, $k_t$ curves
│   ├── load_data.py               ← Live loads and imposed load data
│   ├── nbc105_2025_data.py        ← Seismic zones, soil params, building specs
│   └── structural_systems.py      ← NBC 105 structural system constants
├── core/                          ← Headless calculation engines (Unit-testable)
│   ├── beam_engine.py             
│   ├── column_engine.py           
│   ├── eccentric_footing_engine.py
│   ├── foundation_engine.py       
│   ├── seismic_engine.py          
│   ├── staircase_engine.py        
│   └── wind_engine.py             
├── export/                        ← Report generation logic
│   ├── excel_exporter.py          
│   └── word_exporter.py           
└── ui/                            ← PyQt6 interface
    ├── main_window.py             ← Main layout and state management
    ├── stylesheets.py             ← Dark (Nord) & Light themes
    ├── dialogs/                   ← Pop-ups (Export, Settings, Help)
    ├── widgets/                   ← Reusable UI components
    └── tabs/                      ← Module-specific interface layouts (Slab logic is also embedded here)
```

---

### Disclaimer
*This software is intended for educational, preliminary design, and reference use. It is not a substitute for professional engineering judgement. Always verify the results against current code provisions and manual calculations before utilizing them in a real-world structural project.*