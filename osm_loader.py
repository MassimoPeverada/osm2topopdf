import gc
import os
import xml.etree.ElementTree as ET
import geopandas as gpd
import numpy as np
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import linemerge, polygonize, unary_union

KEY_TAGS = {
    "name",
    "ele",
    "ref",
    "route",
    "type",
    "place",
    "natural",
    "highway",
    "railway",
    "station",
    "historic",
    "amenity",
    "barrier",
    "tourism",
    "aeroway",
    "waterway",
    "water",
    "man_made",
    "tower:type",
    "ford",
    "bridge",
    "tunnel",
    "tracktype",
    "aerialway",
    "landuse",
    "leisure",
    "building",
    "shop",
    "office",
    "boundary",
    "power",
    "sport",
    "contour",
    "elevation",
    "contour_ext",
}

_NODE_POI_TAGS = KEY_TAGS - {"ref", "type", "bridge", "tunnel", "tracktype"}
_NON_POI_HIGHWAY_VALS = {
    "street_lamp",
    "traffic_signals",
    "crossing",
    "give_way",
    "stop",
    "turning_circle",
    "bus_stop",
    "speed_camera",
}



# ==============================================================================
# Numeric condition helpers (area / scale)
# ==============================================================================
def _parse_numeric_cond(cond_str, prefix):
  rest = cond_str[len(prefix):].strip()
  if rest.startswith("<="):
    return "<=", float(rest[2:].strip())
  if rest.startswith(">="):
    return ">=", float(rest[2:].strip())
  if rest.startswith("<"):
    return "<", float(rest[1:].strip())
  if rest.startswith(">"):
    return ">", float(rest[1:].strip())
  raise ValueError("missing < or > operator")


def _check_numeric_cond(val, op, threshold):
  if op == "<":
    return val < threshold
  if op == "<=":
    return val <= threshold
  if op == ">":
    return val > threshold
  if op == ">=":
    return val >= threshold
  return False


# ==============================================================================
# Geometric & feature filters (osmfilters.txt)
# Syntax: key1=val1,val2; key2=val3; area < 1000; scale > 25000
# ==============================================================================
def load_osm_filters(filters_path="osmfilters.txt"):
  rules = []
  if not filters_path or not os.path.exists(filters_path):
    return rules

  with open(filters_path, "r", encoding="utf-8", errors="ignore") as f:
    for line_num, line in enumerate(f, start=1):
      s = line.strip()
      if not s or s.startswith("'") or s.startswith("#"):
        continue

      parts = [p.strip() for p in s.split(";") if p.strip()]
      if not parts:
        continue

      tag_conds = []
      area_conds = []
      scale_conds = []
      valid_rule = True

      for part in parts:
        p_low = part.lower()
        if p_low.startswith("area") and (len(p_low) == 4 or p_low[4] in " <>="):
          try:
            op, val = _parse_numeric_cond(p_low, "area")
            area_conds.append((op, val))
          except ValueError:
            print(
                f"[WARNING] {filters_path} (line {line_num}): invalid area condition '{part}'.",
                flush=True,
            )
            valid_rule = False
            break
        elif p_low.startswith("scale") and (len(p_low) == 5 or p_low[5] in " <>="):
          try:
            op, val = _parse_numeric_cond(p_low, "scale")
            scale_conds.append((op, val))
          except ValueError:
            print(
                f"[WARNING] {filters_path} (line {line_num}): invalid scale condition '{part}'.",
                flush=True,
            )
            valid_rule = False
            break
        elif "=" in part:
          k, v_str = part.split("=", 1)
          k = k.strip().lower()
          vals = {v.strip().lower() for v in v_str.split(",") if v.strip()}
          if not k or not vals:
            print(
                f"[WARNING] {filters_path} (line {line_num}): missing key or value in '{part}'.",
                flush=True,
            )
            valid_rule = False
            break
          KEY_TAGS.add(k)
          _NODE_POI_TAGS.add(k)
          tag_conds.append((k, vals))
        else:
          print(
              f"[WARNING] {filters_path} (line {line_num}): unrecognized condition '{part}'.",
              flush=True,
          )
          valid_rule = False
          break

      if valid_rule and (tag_conds or area_conds or scale_conds):
        rules.append({
            "tags": tag_conds,
            "area": area_conds,
            "scale": scale_conds,
        })

  return rules


def _is_feature_filtered(tags, filter_rules, geom=None, map_scale=25000):
  if not filter_rules:
    return False

  is_polygon = geom is not None and geom.geom_type in ("Polygon", "MultiPolygon")
  poly_area = None

  for rule in filter_rules:
    if rule["scale"]:
      if not all(_check_numeric_cond(map_scale, op, thr) for op, thr in rule["scale"]):
        continue

    tags_match = True
    for k, allowed_vals in rule["tags"]:
      tv = tags.get(k, "").strip().lower()
      if not tv or ("*" not in allowed_vals and tv not in allowed_vals):
        tags_match = False
        break
    if not tags_match:
      continue

    if rule["area"] and is_polygon:
      if poly_area is None:
        poly_area = geom.area
      if not all(_check_numeric_cond(poly_area, op, thr) for op, thr in rule["area"]):
        continue

    return True

  return False


# ==============================================================================
# Filter to exclude label names by text rules (begins/equals/contains) or by OSM tag values
# and polygon area/scale thresholds (syntax: @exclude: key=val1,val2 [; area<1000] [; scale>25000])
# ==============================================================================
def load_exclusion_rules(names_path="names.txt"):
  text_rules = []
  tag_rules = []
  if not names_path or not os.path.exists(names_path):
    return text_rules, tag_rules

  with open(names_path, "r", encoding="utf-8", errors="ignore") as f:
    for line_num, line in enumerate(f, start=1):
      s = line.strip()
      if not s or s.startswith("'") or s.startswith("#"):
        continue

      # Tag/area/scale exclusion syntax: @exclude: key1=val1,val2 [; key2=val3] [; area<1000] [; scale>25000]
      if s.startswith("@"):
        if not s.lower().startswith("@exclude:"):
          print(
              f"[WARNING] {names_path} (line {line_num}): invalid syntax '{s}' (expected '@exclude: key=val').",
              flush=True,
          )
          continue

        expr = s[9:].strip()
        parts = [p.strip() for p in expr.split(";") if p.strip()]
        tag_conds = []
        area_conds = []
        scale_conds = []
        valid_rule = True

        for part in parts:
          p_low = part.lower()
          if p_low.startswith("area") and (len(p_low) == 4 or p_low[4] in " <>="):
            try:
              op, val = _parse_numeric_cond(p_low, "area")
              area_conds.append((op, val))
            except ValueError:
              print(
                  f"[WARNING] {names_path} (line {line_num}): invalid area condition in '{s}'.",
                  flush=True,
              )
              valid_rule = False
              break
          elif p_low.startswith("scale") and (len(p_low) == 5 or p_low[5] in " <>="):
            try:
              op, val = _parse_numeric_cond(p_low, "scale")
              scale_conds.append((op, val))
            except ValueError:
              print(
                  f"[WARNING] {names_path} (line {line_num}): invalid scale condition in '{s}'.",
                  flush=True,
              )
              valid_rule = False
              break
          elif "=" in part:
            k, v_str = part.split("=", 1)
            k = k.strip().lower()
            vals = {v.strip().lower() for v in v_str.split(",") if v.strip()}
            if not k or not vals:
              print(
                  f"[WARNING] {names_path} (line {line_num}): missing key or value in '{s}'.",
                  flush=True,
              )
              valid_rule = False
              break
            KEY_TAGS.add(k)
            _NODE_POI_TAGS.add(k)
            tag_conds.append((k, vals))
          else:
            print(
                f"[WARNING] {names_path} (line {line_num}): invalid condition in '{s}'.",
                flush=True,
            )
            valid_rule = False
            break

        if valid_rule and tag_conds:
          tag_rules.append({
              "tags": tag_conds,
              "area": area_conds,
              "scale": scale_conds,
          })
        continue

      # Extended readable text rules: begins:, equals:, contains:
      if ":" in s:
        prefix, val = s.split(":", 1)
        p_low = prefix.strip().lower()
        val_low = val.strip().lower()
        if p_low == "begins" and val_low:
          text_rules.append(("b", val_low))
          continue
        if p_low == "equals" and val_low:
          text_rules.append(("e", val_low))
          continue
        if p_low == "contains" and val_low:
          text_rules.append(("i", val_low))
          continue

      print(
          f"[WARNING] {names_path} (line {line_num}): unrecognized rule '{s}'.",
          flush=True,
      )

  return text_rules, tag_rules


def clean_name(raw_name, exclusion_rules):
  if not raw_name:
    return ""
  name = str(raw_name).strip()
  if not name:
    return ""
  name_low = name.lower()
  for rule_type, text in exclusion_rules:
    if rule_type == "b" and name_low.startswith(text):
      return ""
    if rule_type == "e" and name_low == text:
      return ""
    if rule_type == "i" and text in name_low:
      return ""
  return name


def _filter_tag_name(raw_name, tags, excl_rules, tag_rules, geom=None, map_scale=25000):
  name = clean_name(raw_name, excl_rules)
  if not name or not tag_rules:
    return name

  is_polygon = geom is not None and geom.geom_type in ("Polygon", "MultiPolygon")
  poly_area = None

  for rule in tag_rules:
    if rule["scale"]:
      if not all(_check_numeric_cond(map_scale, op, thr) for op, thr in rule["scale"]):
        continue

    tags_match = True
    for k, allowed_vals in rule["tags"]:
      tv = tags.get(k, "").strip().lower()
      if not tv or ("*" not in allowed_vals and tv not in allowed_vals):
        tags_match = False
        break
    if not tags_match:
      continue

    if rule["area"] and is_polygon:
      if poly_area is None:
        poly_area = geom.area
      if not all(_check_numeric_cond(poly_area, op, thr) for op, thr in rule["area"]):
        continue

    return ""

  return name

def _extract_tags(elem):
  tags = {}
  for t in elem.findall("tag"):
    k = t.attrib.get("k", "")
    if k in KEY_TAGS:
      tags[k] = t.attrib.get("v", "")
  return tags


def _extract_relation_ways(rel_id, rel_map, visited=None):
  if visited is None:
    visited = set()
  if rel_id in visited:
    return []
  visited.add(rel_id)
  rel = rel_map.get(rel_id)
  if rel is None:
    return []
  result = []
  for mtype, mref, mrole in rel["members"]:
    if mtype == "way":
      result.append((mrole, mref))
    elif mtype == "relation":
      result.extend(_extract_relation_ways(mref, rel_map, visited))
  return result


def _close_open_segments_on_bbox(segments, utm_bbox):
  if not segments or utm_bbox is None:
    return []

  merged = linemerge(segments)
  if merged.is_empty:
    return []
  lines = [merged] if merged.geom_type == "LineString" else list(merged.geoms)

  minx, miny, maxx, maxy = utm_bbox.bounds
  diag = ((maxx - minx) ** 2 + (maxy - miny) ** 2) ** 0.5
  ext_len = max(500.0, diag * 0.1)

  clipped_lines = []
  for ls in lines:
    coords = list(ls.coords)
    if len(coords) < 2:
      continue
    it_coords = iter(coords)
    x0, y0 = next(it_coords)
    x1, y1 = next(it_coords)
    dx, dy = x0 - x1, y0 - y1
    d = (dx * dx + dy * dy) ** 0.5
    if d > 0 and utm_bbox.contains(Point(x0, y0)):
      coords.insert(0, (x0 + (dx / d) * ext_len, y0 + (dy / d) * ext_len))

    xn, yn = coords[-1]
    xp, yp = coords[-2]
    dx, dy = xn - xp, yn - yp
    d = (dx * dx + dy * dy) ** 0.5
    if d > 0 and utm_bbox.contains(Point(xn, yn)):
      coords.append((xn + (dx / d) * ext_len, yn + (dy / d) * ext_len))

    clipped = LineString(coords).intersection(utm_bbox)
    if clipped.is_empty:
      continue
    if clipped.geom_type == "LineString":
      clipped_lines.append(clipped)
    elif clipped.geom_type == "MultiLineString":
      clipped_lines.extend(clipped.geoms)

  if not clipped_lines:
    return []

  left_probes = []
  right_probes = []
  inner_box = utm_bbox.buffer(-2.0)
  for ls in lines:
    in_box = ls.intersection(inner_box)
    if in_box.is_empty:
      continue
    parts = [in_box] if in_box.geom_type == "LineString" else list(in_box.geoms)
    for part in parts:
      if part.length < 2.0:
        continue
      for frac in (0.25, 0.5, 0.75):
        dist = part.length * frac
        pt = part.interpolate(dist)
        p_a = part.interpolate(max(0.0, dist - 0.5))
        p_b = part.interpolate(min(part.length, dist + 0.5))
        dx, dy = p_b.x - p_a.x, p_b.y - p_a.y
        norm = (dx * dx + dy * dy) ** 0.5
        if norm > 0:
          nx, ny = -dy / norm, dx / norm
          left_probes.append(Point(pt.x + nx * 1.5, pt.y + ny * 1.5))
          right_probes.append(Point(pt.x - nx * 1.5, pt.y - ny * 1.5))

  if not left_probes:
    return []

  network = unary_union(clipped_lines + [utm_bbox.boundary])
  faces = list(polygonize(network))

  selected = []
  for face in faces:
    if not face.is_valid or face.is_empty:
      continue
    has_left = any(face.contains(pt) for pt in left_probes)
    has_right = any(face.contains(pt) for pt in right_probes)
    if has_left and not has_right:
      selected.append(face)

  return selected


def _build_relation_polygons(members, ways_coords, utm_bbox=None):
  outer_rings = []
  inner_rings = []
  outer_segments = []
  inner_segments = []

  for role, wid in members:
    coords = ways_coords.get(wid)
    if not coords or len(coords) < 2:
      continue
    is_inner = role == "inner"
    if coords[:1] == coords[-1:] and len(coords) >= 4:
      poly = Polygon(coords)
      if not poly.is_valid:
        poly = poly.buffer(0)
      if poly.is_valid and not poly.is_empty:
        if is_inner:
          inner_rings.append(poly)
        else:
          outer_rings.append(poly)
    else:
      ls = LineString(coords)
      if is_inner:
        inner_segments.append(ls)
      else:
        outer_segments.append(ls)

  if outer_segments:
    merged_out = linemerge(outer_segments)
    for p in polygonize(merged_out):
      if p.is_valid and not p.is_empty:
        outer_rings.append(p)
    if not outer_rings and utm_bbox is not None:
      outer_rings.extend(_close_open_segments_on_bbox(outer_segments, utm_bbox))

  if inner_segments:
    merged_in = linemerge(inner_segments)
    for p in polygonize(merged_in):
      if p.is_valid and not p.is_empty:
        inner_rings.append(p)
    if not inner_rings and utm_bbox is not None:
      inner_rings.extend(_close_open_segments_on_bbox(inner_segments, utm_bbox))

  if not outer_rings:
    return None

  geom_outer = unary_union(outer_rings)
  if inner_rings:
    geom_inner = unary_union(inner_rings)
    geom_final = geom_outer.difference(geom_inner)
  else:
    geom_final = geom_outer

  return geom_final if (geom_final and not geom_final.is_empty) else None
def load_osm_data(
    osm_file,
    utm_bbox,
    names_path="names.txt",
    filters_path="osmfilters.txt",
    map_scale=25000,
    utm_epsg="EPSG:32632",
    debug=False,
):
  excl_rules, tag_rules = load_exclusion_rules(names_path)
  if names_path and os.path.exists(names_path):
    print(f"Loaded exclusion rules from: {names_path}", flush=True)
  filter_rules = load_osm_filters(filters_path)
  if filters_path and os.path.exists(filters_path):
    print(f"Loaded OSM feature filters from: {filters_path}", flush=True)
  transformer = Transformer.from_crs("EPSG:4326", utm_epsg, always_xy=True)

  raw_nids = []
  raw_lons = []
  raw_lats = []
  poi_candidates = []
  raw_ways = []
  rel_map = {}

  # Stream XML with iterparse and clear elements immediately to keep RAM low
  context = ET.iterparse(osm_file, events=("end",))
  for _, elem in context:
    tag_name = elem.tag
    if tag_name == "node":
      nid = elem.attrib.get("id")
      raw_nids.append(nid)
      raw_lons.append(float(elem.attrib["lon"]))
      raw_lats.append(float(elem.attrib["lat"]))
      tags = _extract_tags(elem)
      if tags and any(k in _NODE_POI_TAGS for k in tags):
        # Skip standalone traffic/road furniture nodes (e.g. street lamps, crossings) to save RAM
        if not (len(tags) == 1 and tags.get("highway") in _NON_POI_HIGHWAY_VALS):
          poi_candidates.append((nid, tags))
      elem.clear()
    elif tag_name == "way":

      wid = elem.attrib.get("id")
      way_nids = [nd.attrib.get("ref") for nd in elem.findall("nd")]
      tags = _extract_tags(elem)
      raw_ways.append((wid, way_nids, tags))
      elem.clear()
    elif tag_name == "relation":
      rid = elem.attrib.get("id")
      tags = _extract_tags(elem)
      if tags:
        members = [
            (
                m.attrib.get("type"),
                m.attrib.get("ref"),
                m.attrib.get("role", ""),
            )
            for m in elem.findall("member")
        ]
        rel_map[rid] = {"tags": tags, "members": members}
      elem.clear()

  # Vectorized coordinate projection in one pass
  if raw_nids:
    xs, ys = transformer.transform(
        np.asarray(raw_lons, dtype=np.float64),
        np.asarray(raw_lats, dtype=np.float64),
    )
    nodes_xy = dict(zip(raw_nids, zip(xs.tolist(), ys.tolist())))
    del xs, ys
  else:
    nodes_xy = {}
  raw_nids.clear()
  raw_lons.clear()
  raw_lats.clear()

  point_records = []
  for nid, tags in poi_candidates:
    xy = nodes_xy.get(nid)
    if xy is None:
      continue
    pt = Point(xy)
    if utm_bbox.contains(pt):
      if _is_feature_filtered(tags, filter_rules, geom=pt, map_scale=map_scale):
        continue
      rec = dict(tags)
      rec["_nid"] = nid
      rec["clean_name"] = _filter_tag_name(
          tags.get("name", ""),
          tags,
          excl_rules,
          tag_rules,
          geom=pt,
          map_scale=map_scale,
      )
      rec["geometry"] = pt
      point_records.append(rec)
  poi_candidates.clear()

  ways_coords = {}
  line_records = []
  polygon_records = []
  rural_node_ids = set()

  for wid, way_nids, tags in raw_ways:
    coords = [nodes_xy[ref] for ref in way_nids if ref in nodes_xy]
    if len(coords) < 2:
      continue
    ways_coords[wid] = coords

    if not tags:
      continue

    if tags.get("highway") in ("track", "path", "footway", "bridleway", "cycleway"):
      rural_node_ids.update(way_nids)

    is_closed = coords[:1] == coords[-1:] and len(coords) >= 4
    has_area_tag = (
        (
            any(
                k in tags
                for k in (
                    "building",
                    "landuse",
                    "natural",
                    "leisure",
                    "amenity",
                    "aeroway",
                    "power",
                    "boundary",
                )
            )
            or tags.get("waterway") in ("riverbank", "dock", "boatyard")
        )
        and tags.get("highway") is None
        and tags.get("waterway") in (None, "riverbank", "dock", "boatyard")
        and tags.get("barrier") is None
    )

    if is_closed and has_area_tag:
      geom = Polygon(coords)
      if not geom.is_valid:
        geom = geom.buffer(0)
      if not geom.is_empty and geom.intersects(utm_bbox):
        if _is_feature_filtered(tags, filter_rules, geom=geom, map_scale=map_scale):
          continue
        rec = dict(tags)
        rec["clean_name"] = _filter_tag_name(
            tags.get("name", ""),
            tags,
            excl_rules,
            tag_rules,
            geom=geom,
            map_scale=map_scale,
        )
        rec["geometry"] = geom
        polygon_records.append(rec)
    else:
      geom = LineString(coords)
      if not geom.is_empty and geom.intersects(utm_bbox):
        if _is_feature_filtered(tags, filter_rules, geom=geom, map_scale=map_scale):
          continue
        rec = dict(tags)
        rec["clean_name"] = _filter_tag_name(
            tags.get("name", ""),
            tags,
            excl_rules,
            tag_rules,
            geom=geom,
            map_scale=map_scale,
        )
        rec["geometry"] = geom
        line_records.append(rec)

  raw_ways.clear()
  nodes_xy.clear()

  point_records = [
      rec for rec in point_records
      if not (rec.get("barrier") == "gate" and rec.get("_nid") not in rural_node_ids)
  ]
  rural_node_ids.clear()

  for rel_id, rel_info in rel_map.items():
    tags = rel_info["tags"]

    if tags.get("route") in ("hiking", "foot", "mtb", "bicycle", "road") or (
        tags.get("type") == "route" and "route" in tags
    ):
      way_members = _extract_relation_ways(rel_id, rel_map)
      for _, wid in way_members:
        coords = ways_coords.get(wid)
        if not coords or len(coords) < 2:
          continue
        geom_w = LineString(coords)
        if not geom_w.is_empty and geom_w.intersects(utm_bbox):
          if _is_feature_filtered(tags, filter_rules, geom=geom_w, map_scale=map_scale):
            continue
          rec = dict(tags)
          rec["clean_name"] = _filter_tag_name(
              tags.get("name", ""),
              tags,
              excl_rules,
              tag_rules,
              geom=geom_w,
              map_scale=map_scale,
          )
          rec["geometry"] = geom_w
          line_records.append(rec)
      continue

    if tags.get("type") in (
        "restriction",
        "route_master",
        "superroute",
        "connectivity",
        "associatedStreet",
        "public_transport",
        "network",
    ):
      continue

    members = _extract_relation_ways(rel_id, rel_map)
    if not members:
      continue

    geom_rel = _build_relation_polygons(members, ways_coords, utm_bbox=utm_bbox)
    if debug and geom_rel is None and tags.get("type") == "multipolygon":
      print(
          f"[DEBUG] Multipolygon fallito: id={rel_id}, name={tags.get('name', '')}, tags={tags}, membri={len(members)}",
          flush=True,
      )
    if (
        geom_rel is not None
        and not geom_rel.is_empty
        and geom_rel.intersects(utm_bbox)
    ):
      if _is_feature_filtered(tags, filter_rules, geom=geom_rel, map_scale=map_scale):
        continue
      rec = dict(tags)
      rec["clean_name"] = _filter_tag_name(
          tags.get("name", ""),
          tags,
          excl_rules,
          tag_rules,
          geom=geom_rel,
          map_scale=map_scale,
      )
      rec["geometry"] = geom_rel
      polygon_records.append(rec)

  ways_coords.clear()
  rel_map.clear()

  gdf_points = (
      gpd.GeoDataFrame(point_records, crs=utm_epsg)
      if point_records
      else gpd.GeoDataFrame(columns=["geometry"], crs=utm_epsg)
  )
  point_records.clear()

  gdf_lines = (
      gpd.GeoDataFrame(line_records, crs=utm_epsg)
      if line_records
      else gpd.GeoDataFrame(columns=["geometry"], crs=utm_epsg)
  )
  line_records.clear()

  gdf_polygons = (
      gpd.GeoDataFrame(polygon_records, crs=utm_epsg)
      if polygon_records
      else gpd.GeoDataFrame(columns=["geometry"], crs=utm_epsg)
  )
  polygon_records.clear()

  gc.collect()
  return gdf_points, gdf_lines, gdf_polygons

