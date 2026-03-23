"""
constants/structural_systems.py
─────────────────────────────────
Structural system parameters: Rμ, Ωu, Ωs and deflection-amplification factors.
Source: NBC 105:2025 Tables 5-2 and 6-1.
"""

# ── Structural Systems – Table 5-2 ───────────────────────────────────────────
# Kt_key references KT_VALUES in nbc105_2025_data.py
STRUCTURAL_SYSTEMS: dict[str, dict] = {
    "Moment Resisting Frame Systems": {
        "(Steel Moment Resisting Frame)": {
            "Ru": 4, "Ωu": 1.5, "Ωs": 1.25,
            "Kt_key": "For Moment Resisting Steel Frame",          # 2025: 0.085
        },
        "(Reinforced Concrete Moment Resisting Frame)": {
            "Ru": 4, "Ωu": 1.5, "Ωs": 1.25,
            "Kt_key": "For Moment Resisting Concrete Frame",       # 0.075
        },
        "(Steel + RC Composite Moment Resisting Frame)": {
            "Ru": 4, "Ωu": 1.5, "Ωs": 1.25,
            "Kt_key": "For all other structural system",           # 0.05
        },
    },
    "Braced Frame Systems": {
        "(Steel Eccentrically Braced Frame)": {
            "Ru": 4, "Ωu": 1.5, "Ωs": 1.25,
            "Kt_key": "For Eccentrically Braced Structural Steel Frame",  # 0.075 (2025 fix)
        },
        "(Steel + RC Composite Eccentrically Braced Frame)": {
            "Ru": 4, "Ωu": 1.5, "Ωs": 1.25,
            "Kt_key": "For all other structural system",
        },
        "(Steel Concentric Braced Frame)": {
            "Ru": 3, "Ωu": 1.3, "Ωs": 1.15,
            "Kt_key": "For all other structural system",
        },
        "(Steel + RC Composite Concentric Braced Frame)": {
            "Ru": 3, "Ωu": 1.3, "Ωs": 1.15,
            "Kt_key": "For all other structural system",
        },
        "(Steel Buckling Restrained Braces)": {
            "Ru": 4, "Ωu": 1.5, "Ωs": 1.25,
            "Kt_key": "For all other structural system",
        },
    },
    "Structural Wall Systems": {
        "(RC Shear Wall)": {
            "Ru": 3, "Ωu": 1.3, "Ωs": 1.15,
            "Kt_key": "For all other structural system",
        },
        "(Steel + RC Composite Shear Wall)": {
            "Ru": 3, "Ωu": 1.3, "Ωs": 1.15,
            "Kt_key": "For all other structural system",
        },
        "(Reinforced Masonry Shear Wall)": {
            "Ru": 2.5, "Ωu": 1.2, "Ωs": 1.1,
            "Kt_key": "For all other structural system",
        },
        "(Confined Masonry Shear Wall)": {
            "Ru": 2.5, "Ωu": 1.2, "Ωs": 1.1,
            "Kt_key": "For all other structural system",
        },
        "(Unreinforced Masonry Wall with Horizontal Bands & Vertical Bars)": {
            "Ru": 2.0, "Ωu": 1.2, "Ωs": 1.1,
            "Kt_key": "For all other structural system",
        },
    },
    "Dual Systems": {
        "(Steel Eccentrically Braced Frame)": {
            "Ru": 4, "Ωu": 1.5, "Ωs": 1.25,
            "Kt_key": "For Eccentrically Braced Structural Steel Frame",
        },
        "(Steel + RC Composite Eccentrically Braced Frame)": {
            "Ru": 4, "Ωu": 1.5, "Ωs": 1.25,
            "Kt_key": "For all other structural system",
        },
        "(Steel Concentric Braced Frame)": {
            "Ru": 3.5, "Ωu": 1.4, "Ωs": 1.2,
            "Kt_key": "For all other structural system",
        },
        "(Steel + RC Composite Concentric Braced Frame)": {
            "Ru": 3.5, "Ωu": 1.4, "Ωs": 1.2,
            "Kt_key": "For all other structural system",
        },
        "(Steel Buckling Restrained Braces)": {
            "Ru": 4, "Ωu": 1.5, "Ωs": 1.25,
            "Kt_key": "For all other structural system",
        },
        "(RC Shear Wall)": {
            "Ru": 3.5, "Ωu": 1.4, "Ωs": 1.2,
            "Kt_key": "For all other structural system",
        },
        "(Steel + RC Composite Shear Wall)": {
            "Ru": 3.5, "Ωu": 1.4, "Ωs": 1.2,
            "Kt_key": "For all other structural system",
        },
        "(Reinforced Masonry Shear Wall)": {
            "Ru": 2.5, "Ωu": 1.2, "Ωs": 1.1,
            "Kt_key": "For all other structural system",
        },
    },
}

# ── Deflection Amplification Factors – for lateral deflection checks ─────────
# Cd (deflection amplification) per system type.
DEFLECTION_AMPLIFICATION: dict[str, dict[str, float]] = {
    "Moment Resisting Frame Systems": {
        "(Steel Moment Resisting Frame)":             4.0,
        "(Reinforced Concrete Moment Resisting Frame)": 4.0,
        "(Steel + RC Composite Moment Resisting Frame)": 4.0,
    },
    "Braced Frame Systems": {
        "(Steel Eccentrically Braced Frame)":          4.0,
        "(Steel + RC Composite Eccentrically Braced Frame)": 4.0,
        "(Steel Concentric Braced Frame)":             3.0,
        "(Steel + RC Composite Concentric Braced Frame)": 3.0,
        "(Steel Buckling Restrained Braces)":          4.0,
    },
    "Structural Wall Systems": {
        "(RC Shear Wall)":                             2.5,
        "(Steel + RC Composite Shear Wall)":           2.5,
        "(Reinforced Masonry Shear Wall)":             2.5,
        "(Confined Masonry Shear Wall)":               2.0,
        "(Unreinforced Masonry Wall with Horizontal Bands & Vertical Bars)": 1.5,
    },
    "Dual Systems": {
        "(Steel Eccentrically Braced Frame)":          3.5,
        "(Steel + RC Composite Eccentrically Braced Frame)": 3.5,
        "(Steel Concentric Braced Frame)":             3.5,
        "(Steel + RC Composite Concentric Braced Frame)": 3.5,
        "(Steel Buckling Restrained Braces)":          3.5,
        "(RC Shear Wall)":                             3.5,
        "(Steel + RC Composite Shear Wall)":           3.5,
        "(Reinforced Masonry Shear Wall)":             2.5,
    },
}
