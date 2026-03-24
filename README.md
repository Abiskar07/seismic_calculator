# Structural Calculator v1.0.0
**Standards: NBC 105:2025 (Second Revision) · IS 456:2000 · IS 875 Part 1 & 2**


> NBC 105:2025 takes priority; IS 456:2000 applies where NBC is silent.

---

## Quick Start

```bash
pip install PyQt6
python main.py
```
Requires **Python 3.10+**

---

## Tabs & Features

| Tab | Engine | Key Features |
|-----|--------|-------------|
| 🌍 **Base Shear (NBC 105)** | `core/seismic_engine.py` | ESM/MRSM, 3-zone Ch(T), story force distribution, load combinations §3.6, Cv(T), kd |
| 📦 **Load Calc** | — | IS 875 Pt 2 live loads, wall line loads, floor finish/tank/partition |
| ▦ **Slab Design** | `core/` (IS 456) | Two-way coefficient method, moment, Ast, deflection, shear, min steel |
| ━ **Beam Design** | `core/beam_engine.py` | Singly + doubly, torsion §41, T/L-beam, deflection kt/kc/kf, dev length, crack width |
| ⬛ **Column Design** | `core/column_engine.py` | Biaxial interaction (equilibrium), slender §39.7, ties, NBC 105 Annex A ductile detailing |
| ⬛ **Footing Design** | `core/foundation_engine.py` | Bearing, bending, 1-way shear, punching, dev length, col-ftg bearing, seismic SBC +50% |
| ⚙ **Settings** | — | Theme, spacing rounding, export folder, unit weights — saved to disk |

---

## NBC 105:2025 Implementation

| Section | Description | Status |
|---------|-------------|--------|
| §4.1.2 | Spectral shape factor Ch(T) — 3-zone formula | ✅ |
| §4.2 | SLS spectra: Cs(T) = 0.20·C(T) | ✅ |
| §4.3 | Vertical spectra: Cv(Tv) = 2/3·Z | ✅ |
| §5.1.3 | Period amplification ×1.25 | ✅ |
| §5.2 | Seismic weight per floor | ✅ |
| §5.3 | Structural systems: Rμ, Ωu, Ωs (Table 5-2) | ✅ |
| §5.4 | Irregularity: weak/soft/mass story, torsional | ✅ |
| §5.5.2 | Building separation SRSS: Δgap=√(Δ1²+Δ2²) | ✅ |
| §5.6 | Accidental eccentricity ±0.05b | ✅ |
| §6.1 | Base shear coefficients ULS + SLS | ✅ |
| §6.3 | Story force distribution Fi = V·Wi·hi^k/ΣWj·hj^k | ✅ |
| §6.5 | Deflection scale factors kd (Table 6-1) | ✅ |
| §3.6 | Load combinations LSM (8 combos) | ✅ |
| §3.7 | WSM load combinations (3 combos) | ✅ |
| §3.8 | Seismic SBC increase +50% for footings | ✅ |
| §10 | Parts & components Fp formula | ✅ |
| Annex A | Ductile RC column detailing (confinement, ties, hoops) | ✅ |
| Table 4-1 | Soil parameters Ta, Tc, Td, α (K removed 2025) | ✅ |
| Table 4-3 | KTM valley Soil Type D ward mapping (warning) | ✅ |
| Table 5-2 | All structural systems Rμ/Ωu/Ωs | ✅ |

---

## IS 456:2000 Implementation

| Clause | Description | Status |
|--------|-------------|--------|
| §23.2 | Deflection: basic L/d × kt × kc × kf | ✅ |
| §26.2.1 | Development length (Table 5 τ_bd by fck) | ✅ |
| §26.3 / Annex B | T-beam/L-beam effective flange width | ✅ |
| §26.5.1 | Min/max steel, side face (D>750mm) | ✅ |
| §26.5.3 | Column ties: spacing, multi-leg for >4 bars | ✅ |
| §38–39 | Singly + doubly reinforced beam design | ✅ |
| §39.6 | Biaxial column interaction (equilibrium method) | ✅ |
| §39.7 | Additional moments for slender columns | ✅ |
| §40 | Shear stirrup design | ✅ |
| §41.3/41.4 | Torsion — equivalent Ve, Me, closed links | ✅ |
| §34 | Isolated footing — bearing, bending, shear, punching, Ld | ✅ |
| §34.1.3 | Minimum footing depth 300mm | ✅ |
| §34.4.4 | Column-footing bearing stress check | ✅ |
| §35.3 | Crack width (service stress check) | ✅ |
| Annex G | Doubly-reinforced beam design (Asc, fsc, εsc) | ✅ |

---

## Known Limitations (future work)

- One-way slab design (auto-detect Ly/Lx > 2)
- Flat slab (IS 456 §31.5)
- Combined footing / pile cap
- Spiral column (IS 456 §26.5.3.2)
- RC staircase design
- Retaining wall design
- Wind load (IS 875 Pt 3) — placeholder in load combinations

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+1…7` | Jump to tab |
| `Ctrl+N/O/S` | New / Open / Save project |
| `Ctrl+E` | Export results |
| `F5` | Run all calculations |
| `F1` | Help |

---

## Architecture

```
seismic_calculator/
├── main.py                        ← entry point
├── constants/                     ← all code data (no Qt dependency)
│   ├── nbc105_2025_data.py        ← Zone Z, soil Table 4-1, Kt, kd, eccentricity
│   ├── structural_systems.py      ← Table 5-2: Rμ, Ωu, Ωs
│   ├── is456_data.py              ← slab coefficients, shear table, beam coefficients
│   └── load_data.py               ← IS 875 Pt 2 imposed loads
├── core/                          ← headless engines (unit-testable, no Qt)
│   ├── seismic_engine.py          ← NBC 105:2025 full ESM
│   ├── beam_engine.py             ← IS 456 singly/doubly/T-beam/torsion
│   ├── column_engine.py           ← IS 456 + NBC 105 Annex A columns
│   └── foundation_engine.py       ← IS 456 §34 isolated footing
└── ui/
    ├── main_window.py             ← 7 tabs, menus, file I/O, export
    ├── stylesheets.py             ← Dark (Nord) + Light themes
    ├── widgets/                   ← UnitLineEdit, ProjectInfoBar
    ├── dialogs/                   ← Help, About, Export, Settings
    └── tabs/                      ← SeismicTab, LoadTab, SlabTab, BeamTab,
                                      ColumnTab, FoundationTab, SettingsTab
```

---

*For educational and reference use. Not a substitute for professional engineering judgement. Always verify against current code provisions.*
