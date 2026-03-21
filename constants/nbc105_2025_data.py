"""
constants/nbc105_2025_data.py
──────────────────────────────
All seismic-hazard data mandated by NBC 105:2025 (Second Revision).

Key changes vs NBC 105:2020
────────────────────────────
* K (shear-stiffness) parameter REMOVED from soil table (Table 4-1).
* Spectral shape factor formula updated: velocity-sensitive plateau between
  Tc and Td uses  Ch(T) = α·Tc / T  (not the old K-based expression).
* Kt for Eccentrically Braced Steel Frame corrected to 0.075 (was 0.085).
* Kt for Moment Resisting STEEL Frame is now explicitly 0.085.
* Approximate period T1 = kt · H^(3/4) must be multiplied by 1.25 (§ 5.1.3).
* Accidental eccentricity reduced to ±0.05b.
* Soil Type D no longer defined by municipality name; now defined by Vs,30
  (Table 4-2). Kathmandu-valley ward-level table still provided for defaults.
* Deflection scale factors kd added (Table 6-1).
* Cs(T) = 0.20 · C(T)  (unchanged from 2020).
"""

# ── Zone Factors (Z) ──────────────────────────────────────────────────────────
# PGA for 475-year return period, from Annex C / Table C-1
ZONE_FACTOR_DATA: dict[str, float] = {
    "Baglung": 0.30, "Beni": 0.30, "Besishar": 0.30, "Bharatpur": 0.40,
    "Bhimdatta": 0.30, "Bhimshwor": 0.35, "Bhojpur": 0.30, "Bidur": 0.35,
    "Biratnagar": 0.30, "Birendranagar": 0.30, "Birgunj": 0.30, "Butwal": 0.30,
    "Chainpur": 0.35, "Chame": 0.35, "Chautara": 0.35, "Dadeldhura": 0.30,
    "Dailekh": 0.30, "Damak": 0.30, "Damauli": 0.35, "Darchula": 0.30,
    "Dasharathchand": 0.30, "Dhading": 0.35, "Dhangadi": 0.30, "Dhankuta": 0.30,
    "Dharan": 0.30, "Dhulikhel": 0.35, "Dhunche": 0.35, "Diktel": 0.35,
    "Dipayal": 0.30, "Dunai": 0.30, "Gamgadhi": 0.30, "Gaur": 0.35,
    "Gorkha": 0.35, "Gulariya": 0.30, "Hetauda": 0.35, "Illam": 0.30,
    "Jaleshwor": 0.30, "Jomsom": 0.30, "Jumla": 0.30, "Kalaiya": 0.40,
    "Kamalamai": 0.35, "Kapilbastu": 0.30, "Kathmandu": 0.35, "Khalanga": 0.30,
    "Khandbari": 0.35, "Kusma": 0.30, "Lahan": 0.30, "Lalitpur": 0.35,
    "Libang": 0.30, "Malangwa": 0.35, "Mangalsen": 0.30, "Manma": 0.30,
    "Manthali": 0.35, "Martadi": 0.30, "Musikot": 0.30, "Myanglung": 0.30,
    "Nepalgunj": 0.30, "Okhaldhunga": 0.35, "Phidim": 0.30, "Pokhara": 0.35,
    "Pyuthan": 0.30, "Rajbiraj": 0.30, "Ramgram": 0.30, "Salleri": 0.35,
    "Salyan": 0.30, "Sandhikharka": 0.30, "Simikot": 0.30, "Tamghas": 0.30,
    "Tansen": 0.30, "Taplejung": 0.35, "Triyuga": 0.30, "Tulsipur": 0.30,
    "Waling": 0.35,
}

# ── Importance Factors (Table 4-4) ────────────────────────────────────────────
IMPORTANCE_FACTORS: dict[str, float] = {
    # Class I – Ordinary
    "Residential Building": 1.0,
    # Class II
    "Schools": 1.25,
    "Colleges": 1.25,
    "Cinemas": 1.25,
    "Assembly Buildings": 1.25,
    "Shopping Malls": 1.25,
    "Convention Halls": 1.25,
    "Temples": 1.25,
    "Monumental Structures": 1.25,
    "Police Stations": 1.25,
    "Emergency Vehicle shelters/garages": 1.25,
    "Food Storage Structures": 1.25,
    "Emergency relief stores": 1.25,
    "Water works and water towers": 1.25,
    "Radio and Television facilities": 1.25,
    "Telephone exchanges and transmission": 1.25,
    "Offices and residential quarters for services": 1.25,
    # Class III
    "Hospitals": 1.5,
    "Fire Stations": 1.5,
    "Police Headquarters": 1.5,
    "Power Stations (including standby power)": 1.5,
    "Distribution facilities for gas or petroleum": 1.5,
    "Structures for support or containment of hazardous materials": 1.5,
}

# ── Soil Parameters – NBC 105:2025 Table 4-1 ─────────────────────────────────
# NOTE: The 'K' (shear-stiffness) parameter is REMOVED in the 2025 revision.
# For the Equivalent Static Method, Ta is taken as 0 (§ 4.1.2 note 1).
SOIL_PARAMS: dict[str, dict] = {
    "A": {"Ta_table": 0.1, "Tc": 0.5,  "Td": 4.0, "alpha": 2.50,
          "description": "Rock or rock-like geological formation (Vs,30 > 800 m/s)"},
    "B": {"Ta_table": 0.1, "Tc": 0.7,  "Td": 4.0, "alpha": 2.50,
          "description": "Very dense sand/gravel or very stiff clay (350 < Vs,30 ≤ 800 m/s)"},
    "C": {"Ta_table": 0.1, "Tc": 1.0,  "Td": 4.0, "alpha": 2.50,
          "description": "Dense/medium-dense sand, gravel or stiff clay (150 < Vs,30 ≤ 350 m/s)"},
    "D": {"Ta_table": 0.5, "Tc": 2.0,  "Td": 5.0, "alpha": 2.25,
          "description": "Loose-to-medium cohesionless or soft-to-firm cohesive soil (Vs,30 ≤ 150 m/s)"},
}

# ── Empirical Period Coefficients (§ 5.1.2 + § 5.1.3) ────────────────────────
# T_approx = kt * H^(3/4);  T_design = 1.25 * T_approx  (amplification per § 5.1.3)
# Fixed 2025 correction: Eccentrically Braced STEEL Frame → 0.075 (not 0.085).
# 0.085 applies ONLY to Moment Resisting STEEL frame.
KT_VALUES: dict[str, float] = {
    "For Moment Resisting Concrete Frame":          0.075,
    "For Moment Resisting Steel Frame":             0.085,
    "For Eccentrically Braced Structural Steel Frame": 0.075,   # corrected 2025
    "For all other structural system":              0.050,
}

# Amplification factor for empirical period (§ 5.1.3)
PERIOD_AMPLIFICATION_FACTOR: float = 1.25

# ── Accidental Eccentricity (§ 5.6) ──────────────────────────────────────────
# Reduced from ±0.10b (2020) to ±0.05b (2025)
ACCIDENTAL_ECCENTRICITY: float = 0.05

# ── Deflection Scale Factors – Table 6-1 ─────────────────────────────────────
# Applied to ULS deflections obtained from ESM to get more rational values.
DEFLECTION_SCALE_FACTORS_KD: dict[int, float] = {
    1: 1.00,
    2: 0.97,
    3: 0.94,
    4: 0.91,
    5: 0.88,
    6: 0.85,   # "6 or more" → conservative use of 0.85
}

# ── Seismic Weight Live-Load Fractions – Table 5-1 ───────────────────────────
SEISMIC_LIVE_LOAD_FACTORS: dict[str, float] = {
    "Storage buildings (including warehouses)": 0.60,
    "All other occupancies":                    0.30,
    "Roof areas (all buildings)":               0.00,
}

# ── Kathmandu-Valley Soil-Type-D Wards (Table 4-3) ───────────────────────────
# Municipalities whose listed ward numbers are classified as Soil Type D by
# default unless Vs,30 testing proves otherwise.  Used for informational
# warnings in the UI; not used for automatic selection (per 2025 revision).
KTM_VALLEY_SOIL_D: dict[str, object] = {
    "Budhanilkantha Municipality":    "All",
    "Chandragiri Municipality":       "All",
    "Gokarneswor Municipality":       "All",
    "Kageswori Manahara Municipality": [8, 9],
    "Kathmandu Metropolitan City":    [1,2,5,9,10,11,12,13,14,15,16,17,18,19,
                                        20,21,22,23,24,25,26,27,28,29,30,31,32],
    "Kirtipur Municipality":          [10],
    "Nagarjun Municipality":          [2,4,9],
    "Sankharapur Municipality":       "All",
    "Tarakeswor Municipality":        [4,8,9,10,11],
    "Tokha Municipality":             [4,5,6,7,8,9,10,11],
    "Bagmati Rural Municipality":     "All",
    "Dakshinkali Municipality":       "All",
    "Godawari Municipality":          "All",
    "Konjyosom Rural Municipality":   "All",
    "Lalitpur Metropolitan City":     [1,2,3,4,6,7,8,9,10,11,12,13,16,17,19,20],
    "Mahalaxmi Municipality":         [1,2,3,4,5,7],
    "Mahankal Rural Municipality":    "All",
    "Bhaktapur Municipality":         "All",
    "Changunarayan Municipality":     [2],
    "Madhyapur Thimi Municipality":   "All",
    "Suryabinayak Municipality":      [2,3,5,6],
}
