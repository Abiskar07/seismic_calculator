# Seismic Calculator

A comprehensive structural design calculator for engineers working with NBC 105:2025 and IS codes. Whether you're designing beams, columns, foundations, or analyzing seismic and wind loads, this tool has you covered.

## What Can You Do With This?

- **Seismic Analysis** — Calculate seismic loads and forces based on IS 456:2000 and NBC 105:2025
- **Wind Load Design** — Determine wind pressures and their effects on structures
- **Beam Design** — Check capacity, calculate reinforcement, and optimize beam sections
- **Column Design** — Design columns for various load combinations
- **Foundation & Footings** — Size and analyze shallow and deep foundations
- **Slab Design** — Calculate one-way and two-way slab reinforcement
- **Staircase Design** — Design stair slabs with proper reinforcement
- **Export to Excel/Word** — Generate professional reports directly from your calculations

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip (usually comes with Python)

### Installation

1. Clone or download this project to your computer
2. Navigate to the project folder in your terminal
3. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
4. Activate it:
   - **Windows:** `.venv\Scripts\activate`
   - **Mac/Linux:** `source .venv/bin/activate`
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the App

Simply run:

```bash
python main.py
```

The calculator will open in a desktop window. Start with the **Load Tab** to define your project parameters, then move through the design tabs as needed.

## Project Structure

```
seismic_calculator/
├── core/              # The calculation engines for different structural elements
├── ui/                # Desktop interface built with PyQt6
├── constants/         # Building code data and structural system definitions
├── export/            # Excel and Word report generation
├── Building codes/    # Full text references (IS 456:2000, NBC 105:2025)
└── main.py           # Entry point
```

## Building Codes Supported

- **IS 456:2000** — Indian Standard Code of Practice for Plain and Reinforced Concrete
- **NBC 105:2025** — Nepal National Building Code

Tips for Best Results

- Always start by entering your project information and load details in the **Settings** and **Load** tabs
- The app will validate your inputs before calculations
- Export your results as Excel or Word documents for reports and documentation
- Check the **Help** dialog for specific calculation methodologies

## Technical Details

Built with:

- **PyQt6** — Modern desktop UI framework
- **openpyxl** — Excel report generation
- **python-docx** — Word document generation

## Questions or Issues?

If something doesn't work as expected, check the **Help** menu in the app for calculation details and unit conventions. Make sure all required inputs are filled in and values are within reasonable ranges.

---

**Developed by Abiskar Acharya**
v1.0.0
