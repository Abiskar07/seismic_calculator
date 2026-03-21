"""
constants/load_data.py
───────────────────────
Imposed (live) load tables from IS 875 Part 2.
"""

LIVE_LOAD_DATA: dict = {
    "Residential Buildings": {
        "Dwelling houses": {
            "All rooms and kitchens":                     {"udl": 2.0,  "cl": 1.8},
            "Toilet and bath rooms":                      {"udl": 2.0,  "cl": None},
            "Corridors, passages, staircases, store rooms":{"udl": 3.0, "cl": 4.5},
            "Balconies":                                  {"udl": 3.0,  "cl": "1.5 per metre run"},
        },
        "Dwelling units (IS:8888)": {
            "Habitable rooms, kitchens, toilet, bathrooms":{"udl": 1.5,  "cl": 1.4},
            "Corridors, passages, staircases":             {"udl": 1.5,  "cl": 1.4},
            "Balconies":                                   {"udl": 3.0,  "cl": "1.5 per metre run"},
        },
        "Hotels, hostels, lodging houses, dormitories": {
            "Living rooms, bed rooms, dormitories":       {"udl": 2.0,  "cl": 1.8},
            "Kitchens and laundries":                     {"udl": 3.0,  "cl": 4.5},
            "Billiards room and public lounges":          {"udl": 2.0,  "cl": 2.7},
            "Store rooms":                                {"udl": 5.0,  "cl": 4.5},
            "Dining rooms, cafeterias, restaurants":      {"udl": 4.0,  "cl": 2.7},
            "Office rooms":                               {"udl": 2.5,  "cl": 2.7},
            "Rooms for indoor games":                     {"udl": 3.0,  "cl": 1.8},
            "Baths and toilets":                          {"udl": 2.0,  "cl": None},
            "Corridors, passages, staircases (min 4.0)":  {"udl": "Same as floor serviced", "cl": 4.5},
            "Balconies":                                  {"udl": "Same as rooms (min 4.0)", "cl": "1.5 per metre run"},
        },
        "Boiler rooms and plant rooms": {
            "To be calculated (min 5.0)":                 {"udl": 5.0,  "cl": 6.7},
        },
        "Garages": {
            "Passenger cars (<2.5 tonnes)":               {"udl": 2.5,  "cl": 9.0},
            "Vehicles (<4.0 tonnes)":                     {"udl": 5.0,  "cl": 9.0},
        },
    },
    "Educational Buildings": {
        "General": {
            "Class rooms and lecture rooms":              {"udl": 3.0,  "cl": 2.7},
            "Dining rooms, cafeterias, restaurants":      {"udl": 3.0,  "cl": 2.7},
            "Offices, lounges, staff rooms":              {"udl": 2.5,  "cl": 2.7},
            "Dormitories":                                {"udl": 2.0,  "cl": 1.8},
            "Projection rooms":                           {"udl": 5.0,  "cl": None},
            "Kitchens":                                   {"udl": 3.0,  "cl": 4.5},
            "Toilets and bathrooms":                      {"udl": 2.0,  "cl": None},
            "Store rooms":                                {"udl": 5.0,  "cl": 4.5},
        },
        "Libraries and Archives": {
            "Stack room/area":                            {"udl": "6.0 + 2.0/m over 2.2m", "cl": 4.5},
            "Reading rooms (no separate storage)":        {"udl": 3.0,  "cl": 4.5},
            "Reading rooms (with separate storage)":      {"udl": 4.0,  "cl": 4.5},
        },
        "Boiler rooms and plant rooms": {
            "To be calculated (min 4.0)":                 {"udl": 4.0,  "cl": 4.5},
        },
        "Corridors, Passages, Balconies": {
            "Corridors, passages, lobbies, staircases (min 4.0)": {"udl": "Same as floor serviced", "cl": 4.5},
            "Balconies":                                  {"udl": 4.0,  "cl": "1.5 per metre run"},
        },
    },
    "Institutional Buildings": {
        "Wards, Rooms, and General Use": {
            "Bed rooms, wards, dressing rooms, dormitories, lounges": {"udl": 2.0, "cl": 1.8},
            "Kitchens, laundries, laboratories":          {"udl": 3.0,  "cl": 4.5},
            "Dining rooms, cafeterias, restaurants":      {"udl": 3.0,  "cl": 2.7},
            "Toilets and bathrooms":                      {"udl": 2.0,  "cl": None},
            "X-ray, operating, general storage (min 3.0)":{"udl": 3.0,  "cl": 4.5},
            "Office rooms and OPD rooms":                 {"udl": 2.5,  "cl": 2.7},
        },
        "Circulation and Plant Areas": {
            "Corridors, passages, lobbies, staircases (min 4.0)": {"udl": "Same as floor serviced", "cl": 4.5},
            "Boiler rooms and plant rooms (min 5.0)":     {"udl": 5.0,  "cl": 4.5},
            "Balconies":                                  {"udl": "Same as rooms (min 4.0)", "cl": "1.5 per metre run"},
        },
    },
    "Assembly Buildings": {
        "Main Areas": {
            "Assembly with fixed seats":                  {"udl": 4.0,  "cl": 3.6},
            "Assembly without fixed seats":               {"udl": 5.0,  "cl": 3.6},
            "Restaurants, museums, art galleries, gymnasia": {"udl": 4.0, "cl": 4.5},
            "Projection rooms":                           {"udl": 5.0,  "cl": None},
            "Stages":                                     {"udl": 5.0,  "cl": 4.5},
        },
        "Ancillary Areas": {
            "Office rooms, kitchens, laundries":          {"udl": 3.0,  "cl": 2.7},
            "Dressing rooms":                             {"udl": 2.0,  "cl": 1.8},
            "Lounges and billiards rooms":                {"udl": 2.0,  "cl": 2.7},
            "Toilets and bathrooms":                      {"udl": 2.0,  "cl": None},
        },
        "Circulation and Plant Areas": {
            "Corridors, passages, staircases (min 4.0)":  {"udl": 4.0,  "cl": 4.5},
            "Balconies":                                  {"udl": "Same as rooms (min 4.0)", "cl": "1.5 per metre run"},
            "Boiler rooms and plant rooms":               {"udl": 7.5,  "cl": 4.5},
            "Corridors with vehicle/trolley loads":       {"udl": 5.0,  "cl": 4.5},
        },
    },
    "Business and Office Buildings": {
        "Office and Room Types": {
            "Rooms for general use with separate storage": {"udl": 2.5, "cl": 2.7},
            "Rooms without separate storage":             {"udl": 4.0,  "cl": 4.5},
            "Banking halls":                              {"udl": 3.0,  "cl": 2.7},
            "Business computing machine rooms":           {"udl": 3.5,  "cl": 4.5},
            "Records/files store rooms":                  {"udl": 5.0,  "cl": 4.5},
            "Vaults and strong rooms (min 5.0)":          {"udl": 5.0,  "cl": 4.5},
            "Cafeterias and dining rooms":                {"udl": 3.0,  "cl": 2.7},
            "Kitchens":                                   {"udl": 3.0,  "cl": 2.7},
            "Bath and toilet rooms":                      {"udl": 2.0,  "cl": None},
        },
        "Circulation and Plant Areas": {
            "Corridors, passages, lobbies, staircases (min 4.0)": {"udl": 4.0, "cl": 4.5},
            "Balconies":                                  {"udl": "Same as rooms (min 4.0)", "cl": "1.5 per metre run"},
            "Boiler rooms and plant rooms (min 5.0)":     {"udl": 5.0,  "cl": 6.7},
        },
    },
    "Mercantile Buildings": {
        "Shop and Office Areas": {
            "Retail shops":                               {"udl": 4.0,  "cl": 3.6},
            "Wholesale shops (min 6.0)":                  {"udl": 6.0,  "cl": 4.5},
            "Office rooms":                               {"udl": 2.5,  "cl": 2.7},
            "Dining rooms, restaurants, cafeterias":      {"udl": 3.0,  "cl": 2.7},
            "Toilets":                                    {"udl": 2.0,  "cl": None},
            "Kitchens and laundries":                     {"udl": 3.0,  "cl": 4.5},
        },
        "Circulation and Plant Areas": {
            "Boiler rooms and plant rooms (min 5.0)":     {"udl": 5.0,  "cl": 6.7},
            "Corridors, passages, staircases (min 4.0)":  {"udl": 4.0,  "cl": 4.5},
            "Corridors with vehicle/trolley loads":       {"udl": 5.0,  "cl": 4.5},
            "Balconies":                                  {"udl": "Same as rooms (min 4.0)", "cl": "1.5 per metre run"},
        },
    },
    "Industrial Buildings": {
        "Work and Ancillary Areas": {
            "Work areas without machinery/equipment":     {"udl": 2.5,  "cl": 4.5},
            "Work areas - Light duty machinery":          {"udl": 5.0,  "cl": 4.5},
            "Work areas - Medium duty machinery":         {"udl": 7.0,  "cl": 4.5},
            "Work areas - Heavy duty machinery":          {"udl": 10.0, "cl": 4.5},
            "Cafeterias and dining rooms":                {"udl": 3.0,  "cl": 2.7},
            "Kitchens":                                   {"udl": 3.0,  "cl": 4.5},
            "Toilets and bathrooms":                      {"udl": 2.0,  "cl": None},
        },
        "Circulation and Plant Areas": {
            "Boiler rooms and plant rooms (min 5.0)":     {"udl": 5.0,  "cl": 6.7},
            "Corridors, passages, staircases":            {"udl": 4.0,  "cl": 4.5},
            "Corridors with vehicle/machine loads (min 5.0)": {"udl": 5.0, "cl": 4.5},
        },
    },
    "Storage Buildings": {
        "Storage and Plant Areas": {
            "Storage rooms (other than cold storage)":    {"udl": "2.4/m height (min 7.5)", "cl": 7.0},
            "Cold storage":                               {"udl": "5.0/m height (min 15.0)", "cl": 9.0},
            "Boiler rooms and plant rooms":               {"udl": 7.5,  "cl": 4.5},
        },
        "Circulation Areas": {
            "Corridors, passages, staircases (min 4.0)":  {"udl": 4.0,  "cl": 4.5},
            "Corridors with vehicle/trolley loads":       {"udl": 5.0,  "cl": 4.5},
        },
    },
}
