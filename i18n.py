import json
import os

DEFAULT_STRINGS = {
    "east_label": "East [m]",
    "north_label": "North [m]",
    "scale_prefix": "Scale 1:",
    "author_prefix": "Author:",
    "date_prefix": "Date:",
    "pdf_subject": "Topographic map Scale 1:{scale} ({utm})",
    "default_credits": (
        "Generated with osm2topopdf v{version}\n"
        "Map data: © OpenStreetMap contributors (ODbL License)\n"
        "Contour lines (eq. {dtmsec} m) based on Digital Terrain Model...\n"
        "Projection: WGS 84 / {utm}"
    ),
    "legend_itinerary": "Itinerary track",
    "legend_start": "Track start",
    "legend_variant": "Itinerary variant",
    "legend_hiking_route": "Marked hiking trail",
    "legend_bike_route": "Cycle / MTB route",
    "legend_motorway": "Motorway",
    "legend_motorway_tunnel": "Motorway tunnel",
    "legend_major_road": "Major road",
    "legend_major_road_tunnel": "Major road tunnel",
    "legend_local_road": "Residential / local road",
    "legend_local_road_tunnel": "Local road tunnel",
    "legend_track_norm": "Agricultural / forest track",
    "legend_track_rough": "Rough track (grade 4-5)",
    "legend_footpath": "Footpath / trail",
    "legend_cycleway": "Cycle path / trail",
    "legend_railway": "Railway",
    "legend_aerialway": "Cable car / funicular / ski lift",
    "legend_dam": "Dam / weir",
    "legend_waterway": "River / stream / creek",
    "legend_contour_major": "Index contour line ({dtmmain}m)",
    "legend_contour_minor": "Intermediate contour line ({dtmsec}m)",
    "legend_park": "Park / nature reserve",
    "legend_forest": "Forest / Woodland",
    "legend_meadow": "Meadow / Pasture / Grass",
    "legend_farmland": "Farmland / Orchard / Garden",
    "legend_scrub": "Scrub / Heath",
    "legend_sand": "Sand / Beach",
    "legend_glacier": "Glacier / Snowfield",
    "legend_rock": "Rock / Scree",
    "legend_water": "Lake / Pond / Reservoir",
    "legend_wetland": "Wetland / Marsh",
    "legend_sports": "Sports field / Ski slope",
    "legend_cemetery": "Cemetery",
    "legend_military": "Military area",
    "legend_building": "Building",
    "legend_urban": "Residential / industrial area",
    "legend_church": "Place of worship (church)",
    "legend_station": "Railway station",
    "legend_castle": "Castle or tower",
    "legend_hospital": "Hospital",
    "legend_aerodrome": "Airport / airfield",
    "legend_viewpoint": "Viewpoint",
    "legend_alpine_hut": "Alpine hut",
    "legend_golf": "Golf course",
    "legend_camp_site": "Campsite",
    "legend_landfill": "Landfill",
    "legend_quarry": "Quarry",
    "legend_tower": "Communication tower",
    "legend_wayside_cross": "Cross / wayside shrine",
    "legend_peak": "Mountain or peak",
    "legend_saddle": "Mountain pass / Saddle",
    "legend_parking": "Parking",
    "legend_fountain": "Fountain / drinking water",
    "legend_spring": "Spring",
    "legend_ford": "Ford",
    "legend_cave": "Cave",
    "legend_gate": "Barrier / gate",
    "legend_poi": "Point of interest",
    "legend_helipad": "Helipad",
}


def load_language(lang_code):
  strings = dict(DEFAULT_STRINGS)
  code = str(lang_code or "en").strip().lower()
  if code == "en":
    return strings, "en"

  base_dir = os.path.dirname(os.path.abspath(__file__))
  lang_file = os.path.join(base_dir, f"lang_{code}.json")
  if not os.path.exists(lang_file):
    print(
        f"[WARNING] Language file '{os.path.basename(lang_file)}' not found. "
        "Falling back to default English ('en').",
        flush=True,
    )
    return strings, "en"

  try:
    with open(lang_file, "r", encoding="utf-8") as f:
      data = json.load(f)
    if isinstance(data, dict):
      for k, v in data.items():
        if k in strings and isinstance(v, str) and v.strip():
          strings[k] = v
    return strings, code
  except Exception as exc:
    print(
        f"[WARNING] Failed to load language file '{os.path.basename(lang_file)}': {exc}. "
        "Falling back to default English ('en').",
        flush=True,
    )
    return strings, "en"
