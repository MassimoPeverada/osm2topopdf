import os
import xml.etree.ElementTree as ET
import geopandas as gpd
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
    "contour_ext"
}


def load_exclusion_rules(names_path="names.txt"):
  rules = []
  if not names_path or not os.path.exists(names_path):
    return rules

  with open(names_path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
      s = line.strip()
      if not s or s.startswith("'") or s.startswith("#"):
        continue
      if len(s) < 2:
        continue
      rule_type = s[:1].lower()
      text = s[1:].lower()
      if rule_type in ("b", "e", "i") and text:
        rules.append((rule_type, text))
  return rules


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
  for m in rel.findall("member"):
    mtype = m.attrib.get("type")
    mref = m.attrib.get("ref")
    if mtype == "way":
      result.append((m.attrib.get("role", ""), mref))
    elif mtype == "relation":
      result.extend(_extract_relation_ways(mref, rel_map, visited))
  return result


def _build_relation_polygons(members, ways_coords):
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

  if inner_segments:
    merged_in = linemerge(inner_segments)
    for p in polygonize(merged_in):
      if p.is_valid and not p.is_empty:
        inner_rings.append(p)

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
    osm_file, utm_bbox, names_path="names.txt", utm_epsg="EPSG:32632"
):
  excl_rules = load_exclusion_rules(names_path)
  transformer = Transformer.from_crs("EPSG:4326", utm_epsg, always_xy=True)

  tree = ET.parse(osm_file)
  root = tree.getroot()

  nodes_xy = {}
  point_records = []

  for node in root.findall("node"):
    nid = node.attrib.get("id")
    lon = float(node.attrib["lon"])
    lat = float(node.attrib["lat"])
    x, y = transformer.transform(lon, lat)
    nodes_xy[nid] = (x, y)

    tags = _extract_tags(node)
    if tags:
      pt = Point(x, y)
      if utm_bbox.contains(pt):
        rec = dict(tags)
        rec["clean_name"] = clean_name(tags.get("name", ""), excl_rules)
        rec["geometry"] = pt
        point_records.append(rec)

  ways_coords = {}
  line_records = []
  polygon_records = []

  for way in root.findall("way"):
    wid = way.attrib.get("id")
    coords = []
    for nd in way.findall("nd"):
      ref = nd.attrib.get("ref")
      xy = nodes_xy.get(ref)
      if xy is not None:
        coords.append(xy)

    if len(coords) < 2:
      continue
    ways_coords[wid] = coords

    tags = _extract_tags(way)
    if not tags:
      continue

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
        rec = dict(tags)
        rec["clean_name"] = clean_name(tags.get("name", ""), excl_rules)
        rec["geometry"] = geom
        polygon_records.append(rec)
    else:
      geom = LineString(coords)
      if not geom.is_empty and geom.intersects(utm_bbox):
        rec = dict(tags)
        rec["clean_name"] = clean_name(tags.get("name", ""), excl_rules)
        rec["geometry"] = geom
        line_records.append(rec)

  rel_map = {r.attrib.get("id"): r for r in root.findall("relation")}

  for rel in root.findall("relation"):
    tags = _extract_tags(rel)
    if not tags:
      continue

    # Linear relations (hiking trails, MTB routes, cycleways, roads)
    if tags.get("route") in ("hiking", "foot", "mtb", "bicycle", "road") or (
        tags.get("type") == "route" and "route" in tags
    ):
      rel_id = rel.attrib.get("id")
      way_members = _extract_relation_ways(rel_id, rel_map)
      for _, wid in way_members:
        coords = ways_coords.get(wid)
        if not coords or len(coords) < 2:
          continue
        geom_w = LineString(coords)
        if not geom_w.is_empty and geom_w.intersects(utm_bbox):
          rec = dict(tags)
          rec["clean_name"] = clean_name(tags.get("name", ""), excl_rules)
          rec["geometry"] = geom_w
          line_records.append(rec)
      continue

    members = []
    for m in rel.findall("member"):
      if m.attrib.get("type") == "way":
        members.append((m.attrib.get("role", "outer"), m.attrib.get("ref")))
    if not members:
      continue

    # Area relations (multipolygons: forests, lakes, parks, riverbanks, etc.)
    geom_rel = _build_relation_polygons(members, ways_coords)
    if (
        geom_rel is not None
        and not geom_rel.is_empty
        and geom_rel.intersects(utm_bbox)
    ):
      rec = dict(tags)
      rec["clean_name"] = clean_name(tags.get("name", ""), excl_rules)
      rec["geometry"] = geom_rel
      polygon_records.append(rec)

  gdf_points = (
      gpd.GeoDataFrame(point_records, crs=utm_epsg)
      if point_records
      else gpd.GeoDataFrame(columns=["geometry"], crs=utm_epsg)
  )
  gdf_lines = (
      gpd.GeoDataFrame(line_records, crs=utm_epsg)
      if line_records
      else gpd.GeoDataFrame(columns=["geometry"], crs=utm_epsg)
  )
  gdf_polygons = (
      gpd.GeoDataFrame(polygon_records, crs=utm_epsg)
      if polygon_records
      else gpd.GeoDataFrame(columns=["geometry"], crs=utm_epsg)
  )

  return gdf_points, gdf_lines, gdf_polygons
