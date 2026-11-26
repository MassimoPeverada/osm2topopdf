import os
import re
from topo_symbols import TOPO_MARKERS

TOPO_FONT_STYLES = {
    "Text4": (4.0, "normal", "normal", "#000000"),
    "Text4B": (5.5, "normal", "italic", "#0054ff"),
    "Text4G": (5.5, "normal", "normal", "#006100"),
    "Text5": (5.0, "bold", "normal", "#000000"),
    "Text6": (6.0, "bold", "normal", "#000000"),
    "Text8": (9.0, "bold", "normal", "#000000"),
    "Text12G": (10.5, "bold", "normal", "#006100"),
    "TextRoad": (5.5, "bold", "normal", "#000000"),
    "TextHiking3": (5.5, "bold", "normal", "#ff0000"),
    "TextBike3": (5.5, "bold", "normal", "#8e007a"),
}

# (priority, font, marker, size_pt, has_icon)
KHARTUM_RULES = {
    "place_city": (180, "Text8", None, 0, False),
    "boundary_protected_area": (179, "Text4G", None, 0, False),
    "place_town": (178, "Text8", None, 0, False),
    "place_village": (176, "Text6", None, 0, False),
    "place_suburb": (174, "Text6", None, 0, False),
    "place_hamlet": (172, "Text5", None, 0, False),
    "place_isolated_dwelling": (170, "Text4", None, 0, False),
    "place_farm": (169, "Text4", None, 0, False),
    "place_locality": (168, "Text4", None, 0, False),
    "building_stadium": (167, "Text4", None, 0, False),
    "highway_passing_place": (166, "Text4", None, 0, False),
    "aerodrome": (145, "Text6", TOPO_MARKERS["airplane"], 52, True),
    "railway_station": (140, "Text4", TOPO_MARKERS["train"], 24, True),
    "station_subway": (139, "Text4", TOPO_MARKERS["train"], 22, True),
    "natural_water": (138, "Text4B", None, 0, False),
    "waterway_river": (136, "Text4B", None, 0, False),
    "hospital": (134, "Text4", "s", 32, True),
    "historic_castle": (140, "Text5", TOPO_MARKERS["castle"], 26, True),
    "amenity_place_of_worship": (120, "Text4", TOPO_MARKERS["church"], 26, True),
    "waterway_canal": (115, "Text4B", None, 0, False),
    "waterway_stream": (114, "Text4B", None, 0, False),
    "waterway_drain": (113, "Text4B", None, 0, False),
    "waterway_ditch": (112, "Text4B", None, 0, False),
    "weir": (112, "Text4", "_", 14, False),
    "landuse_quarry": (111, "Text4", TOPO_MARKERS["quarry"], 18, True),
    "camp_site": (110, "Text4", TOPO_MARKERS["tent"], 24, True),
    "landuse_residential": (109, "Text4", None, 0, False),
    "landuse_forest": (108, "Text4G", None, 0, False),
    "landuse_military": (107, "Text4", None, 0, False),
    "prison": (106, "Text4", None, 0, False),
    "landuse_commercial": (106, "Text4", None, 0, False),
    "landuse_retail": (105, "Text4", None, 0, False),
    "landuse_industrial": (104, "Text4", None, 0, False),
    "landuse_cemetery": (103, "Text4", None, 0, False),
    "landuse_farmyard": (102, "Text4", None, 0, False),
    "landuse_farmland": (101, "Text4", None, 0, False),
    "leisure_water_park": (99, "Text4B", None, 0, False),
    "landuse_landfill": (98, "Text4", TOPO_MARKERS["landfill"], 20, True),
    "leisure_stadium": (97, "Text4", None, 0, False),
    "alpine_hut": (96, "Text4", TOPO_MARKERS["alpine_hut"], 26, True),
    "leisure_golf_course": (95, "Text4G", TOPO_MARKERS["golf"], 22, True),
    "natural_wetland": (93, "Text4B", None, 0, False),
    "leisure_park": (91, "Text4G", None, 0, False),
    "leisure_garden": (90, "Text4G", None, 0, False),
    "leisure_sports_centre": (89, "Text4", None, 0, False),
    "power_generator_area": (88, "Text4", None, 0, False),
    "natural_peak": (87, "Text4", "^", 18, True),
    "natural_cliff": (86, "Text4", None, 0, False),
    "natural_saddle": (85, "Text4", TOPO_MARKERS["saddle"], 20, True),
    "natural_cave_entrance": (84, "Text4", TOPO_MARKERS["cave"], 20, True),
    "barrier_gate": (81, "Text4", TOPO_MARKERS["gate"], 28, True),
    "highway_bridge": (76, "Text4", None, 0, False),
    "leisure_pitch": (71, "Text4", None, 0, False),
    "highway_mini_roundabout": (70, "Text4", "o", 12, True),
    "tourism_attraction": (66, "Text4", "*", 18, True),
    "tourism_viewpoint": (63, "Text4", TOPO_MARKERS["viewpoint"], 22, True),
    "historic_wayside_shrine": (62, "Text4", TOPO_MARKERS["wayside_cross"], 20, True),
    "historic": (61, "Text4", "o", 14, True),
    "historic_memorial": (60, "Text4", None, 12, True),
    "tower_communication": (59, "Text4", TOPO_MARKERS["antenna"], 22, True),
    "spring": (58, "Text4B", "o", 15, True),
    "ford": (57, "Text4B", TOPO_MARKERS["ford"], 18, True),
    "amenity_fountain": (56, "Text4B", TOPO_MARKERS["drop"], 18, True),
    "amenity_drinking_water": (55, "Text4B", TOPO_MARKERS["drop"], 18, True),
    "helipad": (54, "Text4", "o", 32, True),
    "icon_parking": (50, "Text4", "s", 32, True),
    "TextRoad": (10, "TextRoad", None, 0, False),
    "TextHiking3": (9, "TextHiking3", None, 0, False),
    "TextBike3": (8, "TextBike3", None, 0, False),
}

EXCLUDED_SHOPS = {
    "car",
    "car_parts",
    "bicycle",
    "bakery",
    "gambling",
    "car_repair",
    "musical_instrument",
    "newsagent",
    "convenience",
    "lightning",
}

EXCLUDED_AMENITIES = {
    "ice_cream",
    "dojo",
    "fast_food",
    "restaurant",
    "cafe",
    "bar",
    "bank",
}

ICON_ALIASES = {
    "cycle_route": "TextBike3",
    "bike_route": "TextBike3",
    "bike": "TextBike3",
    "hiking_route": "TextHiking3",
    "trail_route": "TextHiking3",
    "hiking": "TextHiking3",
    "road": "TextRoad",
    "road_ref": "TextRoad",
    "peak": "natural_peak",
    "hut": "alpine_hut",
    "shelter": "alpine_hut",
    "saddle": "natural_saddle",
    "pass": "natural_saddle",
    "spring": "spring",
    "cave": "natural_cave_entrance",
    "viewpoint": "tourism_viewpoint",
    "castle": "historic_castle",
    "church": "amenity_place_of_worship",
}


def load_label_overrides(overrides_path="labels.txt"):
  overrides, custom_priorities = [], {}
  if not os.path.exists(overrides_path):
    return overrides, custom_priorities

  curr_mod, curr_prio = None, None
  with open(overrides_path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
      line = line.strip()
      if not line or line.startswith("'"):
        continue
      mk = re.search(r'k="([^"]+)"', line)
      mv = re.search(r'v="([^"]+)"', line)
      if not mk or not mv:
        continue
      k, v = mk.group(1), mv.group(1)

      if k == "ifname":
        curr_prio = None
        curr_mod = {
            "name": v,
            "icon": "",
            "offsetlat": 0.0,
            "offsetlon": 0.0,
            "setlat": 0.0,
            "setlon": 0.0,
            "replacename": "",
        }
        overrides.append(curr_mod)
      elif curr_mod is not None and k in ("ificon", "icon"):
        curr_mod["icon"] = ICON_ALIASES.get(v.strip().lower(), v.strip())
      elif curr_mod is not None and k in curr_mod:
        curr_mod[k] = v if k == "replacename" else float(v)
      elif k == "priority" and curr_mod is not None and curr_prio is None:
        custom_priorities[curr_mod["name"]] = int(v)
      elif k == "priorityname":
        curr_mod = None
        curr_prio = v
      elif k == "priority" and curr_prio:
        custom_priorities[curr_prio] = int(v)
        curr_prio = None

  return overrides, custom_priorities
