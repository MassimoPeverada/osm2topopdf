from topo_labels_config import EXCLUDED_AMENITIES, EXCLUDED_SHOPS
import pandas as pd


def _val(row, col):
  v = row.get(col)
  return "" if pd.isna(v) else str(v).strip()


def classify_feature(row, is_node=False):
  """Replicates the KHARTUM classification engine and returns (maintag, text1, text2)."""
  name = _val(row, "clean_name")
  ele = _val(row, "ele")
  ref = _val(row, "ref")
  route = _val(row, "route")
  geom = row.geometry

  if is_node:
    place = _val(row, "place")
    if place in (
        "city",
        "town",
        "village",
        "suburb",
        "hamlet",
        "isolated_dwelling",
        "farm",
        "locality",
    ):
      return f"place_{place}", name, ""

    nat = _val(row, "natural")
    if nat in ("peak", "saddle"):
      return f"natural_{nat}", name, f"{ele} m" if ele else ""
    if nat == "cliff":
      return ("natural_cliff", name, "") if name else (None, "", "")
    if nat in ("water", "cave_entrance", "spring"):
      return (
          ("spring" if nat == "spring" else f"natural_{nat}"),
          name,
          "",
      )

    if _val(row, "highway") == "mini_roundabout":
      return "highway_mini_roundabout", "", ""
    if _val(row, "highway") == "passing_place":
      return "highway_passing_place", name, ""

    if _val(row, "railway") == "station":
      if _val(row, "station") == "subway":
        return "station_subway", name, ""
      return "railway_station", name, ""

    hist = _val(row, "historic")
    if hist in ("castle", "memorial", "wayside_shrine", "wayside_cross"):
      tag_h = (
          "historic_wayside_shrine"
          if "wayside" in hist
          else f"historic_{hist}"
      )
      return tag_h, name, ""
    if hist in ("ruins", "city_gate", "monument", "archaeological_site") and name:
      return "historic", name, ""

    amen = _val(row, "amenity")
    if amen in ("drinking_water", "place_of_worship", "fountain"):
      return f"amenity_{amen}", name, ""
    if amen == "hospital":
      return "hospital", name, ""

    if _val(row, "barrier") == "gate":
      return "barrier_gate", name, ""

    tour = _val(row, "tourism")
    if tour in ("viewpoint", "camp_site", "alpine_hut"):
      return (
          f"tourism_{tour}" if tour == "viewpoint" else tour,
          name,
          "",
      )
    if tour in ("attraction", "zoo") and name:
      return "tourism_attraction", name, ""

    aero = _val(row, "aeroway")
    if aero in ("helipad", "aerodrome"):
      return aero, name, ""

    if _val(row, "waterway") == "weir":
      return "weir", name, ""

    if (
        _val(row, "man_made") == "tower"
        and _val(row, "tower:type") == "communication"
    ):
      return "tower_communication", name, ""

    if _val(row, "ford") == "yes" and name:
      return "ford", name, ""

    return None, "", ""

  # --- WAYS / POLYGONS ---
  geom_type = geom.geom_type
  is_area = geom_type in ("Polygon", "MultiPolygon")

  if not is_area:
    length = geom.length
    ww = _val(row, "waterway")
    if (
        ww in ("river", "drain", "ditch", "canal", "stream")
        and length >= 200
        and name
    ):
      return f"waterway_{ww}", name, ""
    if _val(row, "aerialway") and length >= 200 and name:
      return "aerialway", name, ""

    bridge = _val(row, "bridge")
    if bridge in ("yes", "viaduct") and name and (
        "ponte" in name.lower() or "bridge" in name.lower()
    ):
      return "highway_bridge", name, ""

    if route == "hiking" and length >= 200 and ref:
      return "TextHiking3", ref, ""
    if route in ("mtb", "bicycle") and length >= 200 and ref:
      return "TextBike3", ref, ""
    if route == "road" and length >= 800 and ref:
      return "TextRoad", ref, ""
    return None, "", ""

  # AREAS / POLYGONS
  area = geom.area
  lu = _val(row, "landuse")
  nat = _val(row, "natural")
  leis = _val(row, "leisure")
  amen = _val(row, "amenity")
  bld = _val(row, "building")
  shop = _val(row, "shop")
  office = _val(row, "office")
  tour = _val(row, "tourism")
  hist = _val(row, "historic")

  if amen == "parking":
    return ("icon_parking", "", "") if area >= 200 else (None, "", "")
  if amen == "prison":
    return ("prison", name, "") if name else (None, "", "")

  if (
      bld
      and bld != "no"
      and (
          shop in EXCLUDED_SHOPS
          or amen in EXCLUDED_AMENITIES
          or office == "insurance"
          or tour == "artwork"
      )
  ):
    return None, "", ""

  if bld in ("church", "chapel") or amen == "place_of_worship" or hist == "monastery":
    return "amenity_place_of_worship", name, ""
  if hist == "castle":
    return "historic_castle", name, ""
  if hist in ("ruins", "archaeological_site") and name:
    return "historic", name, ""
  if tour == "alpine_hut":
    return "alpine_hut", name, ""
  if tour == "camp_site":
    return "camp_site", name, ""
  if tour == "zoo" and name:
    return "tourism_attraction", name, ""
  if _val(row, "boundary") == "protected_area" and name:
    return "boundary_protected_area", name, ""
  if _val(row, "power") == "generator" and name:
    return "power_generator_area", name, ""
  if (leis == "park" or leis == "garden") and area > 4000 and name:
    return f"leisure_{leis}", name, ""
  if lu == "landfill" and area > 4000:
    return "landuse_landfill", name, ""
  if leis in (
      "sports_centre",
      "golf_course",
      "stadium",
      "water_park",
  ) and (name or leis == "golf_course"):
    return f"leisure_{leis}", name, ""
  if leis == "pitch" and name:
    return "leisure_pitch", name, ""
  if nat in ("water", "wetland") and name:
    return f"natural_{nat}", name, ""
  if (lu == "cemetery" or amen == "grave_yard") and name:
    return "landuse_cemetery", name, ""
  if lu in (
      "military",
      "quarry",
      "industrial",
      "commercial",
      "retail",
      "farmyard",
      "residential",
      "forest",
  ) and (name or lu == "quarry"):
    return f"landuse_{lu}", name, ""
  if _val(row, "aeroway") == "aerodrome" and name:
    return "aerodrome", name, ""
  if amen == "hospital" or bld == "hospital":
    return "hospital", name, ""
  if bld == "train_station":
    return "railway_station", name, ""
  if bld and bld != "no" and name:
    return "building_stadium", name, ""

  return None, "", ""
