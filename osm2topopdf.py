"""
osm2topopdf - Topographic Georeferenced PDF Map Generator

Utility by Massimo Peverada to make a georeferenced PDF from OSM data, given one or more GPX tracks, based on a FreeBASIC utility to convert OSM to DXF, ported to
Python and integrated with the help of Gemini.

Released under GPLv3.
"""

VERSION = "1.1.8"
print(f"Starting osm2topopdf v{VERSION} cartographic engine...", flush=True)
import argparse
import configparser
from datetime import datetime
import math
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from dtm_contours import generate_contours_from_dtm
import geopandas as gpd
from i18n import load_language
from legend import compute_legend_layout, draw_legend
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from osm_loader import load_osm_data
from shapely.geometry import LineString, box
from topo_lines import draw_lines_and_contours
from topo_points_labels import draw_points_and_labels
from topo_polygons import draw_topo_polygons

INI_TEMPLATE = """# Default configuration for osm2topopdf
# Values set here are used automatically and can be overridden via command-line arguments.

[PATHS]
inosm = 
outosm = section.osm
dtm = 
contours = contour_lines.osm
exclude = names.txt
labels = labels.txt

[MAP]
scale = 25000
pad = 500
dtmmain = 100
dtmsec = 25
symscale = auto
utm = auto
lang = en
author = 

[CREDITS]
text = Generated with osm2topopdf v{VERSION}
	Map data: © OpenStreetMap contributors (ODbL License)
	Contour lines (eq. {dtmsec} m) based on Digital Terrain Model...
	Projection: WGS 84 / {UTM}
"""



def load_or_create_ini(ini_path):
  if not os.path.exists(ini_path):
    with open(ini_path, "w", encoding="utf-8") as f:
      f.write(INI_TEMPLATE)
    print(f"Created default configuration file: {ini_path}", flush=True)

  cfg = configparser.ConfigParser()
  cfg.read(ini_path, encoding="utf-8")
  return cfg


def compute_symscale(val_str, scale):
  val = str(val_str).strip().lower()
  if val in ("", "auto"):
    return round((25000.0 / float(scale)) ** 0.45, 3)
  return float(val)


def resolve_utm_zone(utm_str, lon_center, lat_center):
  val = str(utm_str).strip().upper()
  if val in ("", "AUTO"):
    zone = max(1, min(60, int((lon_center + 180.0) / 6.0) + 1))
    hemisphere = "N" if lat_center >= 0.0 else "S"
  else:
    m = re.match(r"^(\d{1,2})\s*([NS])$", val)
    if not m:
      raise ValueError(
          f"Invalid -utm value: '{utm_str}'. Use 'auto' or e.g. '32N', '33N', '19S'."
      )
    zone = int(m.group(1))
    hemisphere = m.group(2)

  base_epsg = 32600 if hemisphere == "N" else 32700
  epsg_code = f"EPSG:{base_epsg + zone}"
  label = f"UTM {zone}{hemisphere}"
  return epsg_code, label


def _wait_if_double_clicked():
  if os.name == "nt":
    try:
      import ctypes
      arr = (ctypes.c_uint * 2)()
      if ctypes.windll.kernel32.GetConsoleProcessList(arr, 2) == 1:
        input("\nPress ENTER to exit...")
    except Exception:
      pass
def parse_args():
  pre = argparse.ArgumentParser(add_help=False)
  pre.add_argument("-config", default="osm2topopdf.ini")
  pre_args, _ = pre.parse_known_args()
  cfg = load_or_create_ini(pre_args.config)

  today = datetime.now().strftime("%Y-%m-%d")
  def_inosm = cfg.get("PATHS", "inosm", fallback="")
  def_outosm = cfg.get("PATHS", "outosm", fallback="section.osm")
  def_dtm = cfg.get("PATHS", "dtm", fallback="")
  def_contours = cfg.get("PATHS", "contours", fallback="contour_lines.osm")
  def_exclude = cfg.get("PATHS", "exclude", fallback="names.txt")
  def_labels = cfg.get("PATHS", "labels", fallback="labels.txt")
  def_scale = cfg.getint("MAP", "scale", fallback=25000)
  def_pad = cfg.getfloat("MAP", "pad", fallback=500.0)
  def_dtmmain = cfg.getfloat("MAP", "dtmmain", fallback=100.0)
  def_dtmsec = cfg.getfloat("MAP", "dtmsec", fallback=25.0)
  def_symscale = cfg.get("MAP", "symscale", fallback="auto")
  def_utm = cfg.get("MAP", "utm", fallback="auto")
  def_lang = cfg.get("MAP", "lang", fallback="en")
  def_author = cfg.get("MAP", "author", fallback="")
  def_credits = cfg.get("CREDITS", "text", fallback="")

  parser = argparse.ArgumentParser(
      prog="osm2topopdf",
      description=(
          f"osm2topopdf v{VERSION} - Utility by Massimo Peverada to make a "
          "georeferenced PDF from OSM data, given one or more GPX tracks, based "
          "on a FreeBASIC utility to convert OSM to DXF, ported to Python and "
          "integrated with the help of Gemini."
      ),
      epilog="Released under GPLv3.",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  )
  parser.add_argument(
      "-help",
      action="help",
      help="Show this help message and exit.",
  )
  parser.add_argument(
      "-v",
      "-version",
      action="version",
      version=f"osm2topopdf v{VERSION}",
      help="Show program version and exit.",
  )
  parser.add_argument(
      "positional_gpx",
      nargs="?",
      default="",
      help="GPX file dragged onto the executable or passed without -track.",
  )
  parser.add_argument(
      "-config",
      default=pre_args.config,
      help="Configuration INI file (created automatically if missing).",
  )
  parser.add_argument(
      "-track",
      default="track.gpx",
      help="GPX track file to map.",
  )
  parser.add_argument(
      "-trackvar",
      nargs="*",
      default=[],
      help="One or more GPX route variant files (drawn in dashed red).",
  )
  parser.add_argument(
      "-inosm",
      default=def_inosm,
      help="Full source OSM file (e.g. north-west-latest.osm.pbf). If set, clips with pyosmium.",
  )
  parser.add_argument(
      "-outosm",
      default=def_outosm,
      help="Clipped OSM file generated by pyosmium (default: section.osm) or custom name.",
  )
  parser.add_argument(
      "-force",
      action="store_true",
      help="Automatically overwrite -outosm with pyosmium without asking for confirmation.",
  )
  parser.add_argument(
      "-fast",
      action="store_true",
      help="Use native C++ pyosmium filters (FileProcessor + IdFilter) for fast clipping.",
  )
  parser.add_argument(
      "-superfast",
      action="store_true",
      help="Single-pass clipping with pyosmium C++ BackReferenceWriter.",
  )
  parser.add_argument(
      "-debug",
      action="store_true",
      help=argparse.SUPPRESS,
  )  
  parser.add_argument(
      "-pad",
      type=float,
      default=def_pad,
      help="Minimum padding in meters around the GPX track (rounded to 1000 m).",
  )
  parser.add_argument(
      "-dtm",
      default=def_dtm,
      help="ESRI ASCII Grid (.asc) DTM file or folder of .asc files to generate contour lines.",
  )
  parser.add_argument(
      "-dtmmain",
      type=float,
      default=def_dtmmain,
      help="Major contour interval in meters (e.g. 100).",
  )
  parser.add_argument(
      "-dtmsec",
      type=float,
      default=def_dtmsec,
      help="Minor contour interval in meters (e.g. 25, 10, 50).",
  )
  parser.add_argument(
      "-contours",
      default=def_contours,
      help="OSM contour lines file (used if -dtm is not specified).",
  )
  parser.add_argument(
      "-exclude",
      default=def_exclude,
      help="File with name exclusion rules (prefixes b=begins with, e=equals, i=contains).",
  )
  parser.add_argument(
      "-labels",
      default=def_labels,
      help="File with custom label offset/priority rules.",
  )
  parser.add_argument(
      "-outpdf",
      default="topo_map.pdf",
      help="Output PDF file.",
  )
  parser.add_argument(
      "-scale",
      type=int,
      default=def_scale,
      help="Map cartographic scale (e.g. 25000 or 15000).",
  )
  parser.add_argument(
      "-symscale",
      default=def_symscale,
      help="Symbol/label scale factor: 'auto' based on scale or numeric value (e.g. 0.8, 1.2).",
  )
  parser.add_argument(
      "-utm",
      default=def_utm,
      help="UTM zone: 'auto' from GPX centroid or e.g. '32N', '33N', '19S'.",
  )
  parser.add_argument(
      "-lang",
      default=def_lang,
      help="Map legend and axis language code (e.g. 'en', 'it'). Falls back to 'en' if missing.",
  )
  parser.add_argument(
      "-title",
      default="",
      help="Title printed at the top of the legend (default: GPX filename).",
  )
  parser.add_argument(
      "-author",
      default=def_author,
      help="Author printed in the legend (default: omitted if empty in INI).",
  )
  parser.add_argument(
      "-date",
      default=today,
      help="Date printed in the legend (pass \"\" to omit).",
  )

  if len(sys.argv) == 1:
    parser.print_help()
    _wait_if_double_clicked()
    sys.exit(0)

  args = parser.parse_args()
  if args.positional_gpx:
    args.track = args.positional_gpx
  args.credits_text = def_credits
  args.symscale_val = compute_symscale(args.symscale, args.scale)
  return args
def load_gpx_track(gpx_path, utm_pref="auto"):
  if not os.path.exists(gpx_path):
    raise FileNotFoundError(f"GPX file not found: {gpx_path}")
  tree = ET.parse(gpx_path)
  root = tree.getroot()

  seg_lines = []
  for seg in root.findall(".//{*}trkseg"):
    coords = [
        (float(p.attrib["lon"]), float(p.attrib["lat"]))
        for p in seg.findall("{*}trkpt")
    ]
    if len(coords) >= 2:
      seg_lines.append(LineString(coords))

  if not seg_lines:
    pts = root.findall(".//{*}trkpt") or root.findall(".//{*}rtept")
    coords = [(float(p.attrib["lon"]), float(p.attrib["lat"])) for p in pts]
    if len(coords) >= 2:
      seg_lines.append(LineString(coords))

  if not seg_lines:
    raise ValueError(f"GPX track is empty or has fewer than 2 points: {gpx_path}")

  gdf_wgs = gpd.GeoDataFrame(geometry=seg_lines, crs="EPSG:4326")
  lon_min, lat_min, lon_max, lat_max = gdf_wgs.total_bounds
  lon_c = (lon_min + lon_max) / 2.0
  lat_c = (lat_min + lat_max) / 2.0

  utm_epsg, utm_label = resolve_utm_zone(utm_pref, lon_c, lat_c)
  return gdf_wgs.to_crs(utm_epsg), utm_epsg, utm_label


def _print_progress_bar(label, fraction):
  fraction = max(0.0, min(1.0, float(fraction)))
  width = 28
  filled = int(round(width * fraction))
  bar = "#" * filled + "-" * (width - filled)
  pct = int(round(fraction * 100.0))
  print(f"\r  {label}: [{bar}] {pct:3d}%", end="", flush=True)


def clip_with_pyosmium(file_in, file_out, xmin, ymin, xmax, ymax, utm_epsg):
  try:
    import osmium
  except ImportError as exc:
    raise ImportError(
        "Library 'osmium' (pyosmium) is not installed. Install it with: pip install osmium"
    ) from exc

  safety_pad = 250.0
  box_utm = gpd.GeoDataFrame(
      geometry=[
          box(
              xmin - safety_pad,
              ymin - safety_pad,
              xmax + safety_pad,
              ymax + safety_pad,
          )
      ],
      crs=utm_epsg,
  )
  lon_min, lat_min, lon_max, lat_max = box_utm.to_crs("EPSG:4326").total_bounds

  margin_deg = 0.25
  ext_lon_min = lon_min - margin_deg
  ext_lon_max = lon_max + margin_deg
  ext_lat_min = lat_min - margin_deg
  ext_lat_max = lat_max + margin_deg

  total_size = max(1, os.path.getsize(file_in))
  bytes_per_obj = 9.0 if file_in.lower().endswith(".pbf") else 110.0
  est_objects = max(1.0, total_size / bytes_per_obj)

  print(
      f"Starting pyosmium clip on '{file_in}' -> '{file_out}' "
      f"(lat: {lat_min:.5f}..{lat_max:.5f}, lon: {lon_min:.5f}..{lon_max:.5f})...",
      flush=True,
  )

  class _SelectionPass(osmium.SimpleHandler):

    def __init__(self):
      super().__init__()
      self.nodes_in_box = set()
      self.nearby_nodes = set()
      self.way_nodes = {}
      self.rel_members = {}
      self.count = 0

    def _update(self):
      self.count += 1
      if (self.count & 131071) == 0:
        ratio = self.count / est_objects
        frac = min(0.99, ratio / (1.0 + 0.12 * ratio))
        _print_progress_bar("Pass 1/2 (scanning)", frac)

    def node(self, n):
      self._update()
      if n.location.valid():
        lon = n.location.lon
        lat = n.location.lat
        if (
            ext_lon_min <= lon <= ext_lon_max
            and ext_lat_min <= lat <= ext_lat_max
        ):
          nid = n.id
          self.nearby_nodes.add(nid)
          if lon_min <= lon <= lon_max and lat_min <= lat <= lat_max:
            self.nodes_in_box.add(nid)

    def way(self, w):
      self._update()
      nids = tuple(nd.ref for nd in w.nodes)
      if any(nid in self.nearby_nodes for nid in nids):
        self.way_nodes[w.id] = nids

    def relation(self, r):
      self._update()
      members = tuple((m.type, m.ref) for m in r.members)
      if any(
          (mtype == "w" and mref in self.way_nodes)
          or (mtype == "n" and mref in self.nearby_nodes)
          or (mtype == "r" and mref in self.rel_members)
          for mtype, mref in members
      ):
        self.rel_members[r.id] = members

  _print_progress_bar("Pass 1/2 (scanning)", 0.0)
  sel = _SelectionPass()
  sel.apply_file(file_in, locations=False)
  tot_objects = max(1, sel.count)
  sel.nearby_nodes.clear()
  _print_progress_bar("Pass 1/2 (scanning)", 1.0)
  print("", flush=True)

  final_nodes = set(sel.nodes_in_box)
  final_ways = set()
  for wid, nids in sel.way_nodes.items():
    if any(nid in final_nodes for nid in nids):
      final_ways.add(wid)

  reverse_index = {}
  for rid, members in sel.rel_members.items():
    for mtype, mref in members:
      key = (mtype, mref)
      lst = reverse_index.get(key)
      if lst is None:
        reverse_index[key] = [rid]
      else:
        lst.append(rid)

  final_rels = set()
  queue = []
  for nid in final_nodes:
    for rid in reverse_index.get(("n", nid), ()):
      if rid not in final_rels:
        final_rels.add(rid)
        queue.append(rid)
  for wid in final_ways:
    for rid in reverse_index.get(("w", wid), ()):
      if rid not in final_rels:
        final_rels.add(rid)
        queue.append(rid)

  while queue:
    curr_rid = queue.pop()
    for parent_rid in reverse_index.get(("r", curr_rid), ()):
      if parent_rid not in final_rels:
        final_rels.add(parent_rid)
        queue.append(parent_rid)

  reverse_index.clear()

  for rid in final_rels:
    for mtype, mref in sel.rel_members.get(rid, ()):
      if mtype == "w" and mref in sel.way_nodes:
        final_ways.add(mref)
      elif mtype == "n":
        final_nodes.add(mref)

  for wid in final_ways:
    final_nodes.update(sel.way_nodes.get(wid, ()))

  sel.way_nodes.clear()
  sel.rel_members.clear()
  sel.nodes_in_box.clear()

  base_out, ext_out = os.path.splitext(file_out)
  tmp_out = f"{base_out}.tmp{ext_out}"
  if os.path.exists(tmp_out):
    os.remove(tmp_out)

  writer = osmium.SimpleWriter(tmp_out)

  class _WritePass(osmium.SimpleHandler):

    def __init__(self):
      super().__init__()
      self.count = 0

    def _update(self):
      self.count += 1
      if (self.count & 131071) == 0:
        _print_progress_bar(
            "Pass 2/2 (writing)", min(0.99, self.count / tot_objects)
        )

    def node(self, n):
      self._update()
      if n.id in final_nodes:
        writer.add_node(n)

    def way(self, w):
      self._update()
      if w.id in final_ways:
        writer.add_way(w)

    def relation(self, r):
      self._update()
      if r.id in final_rels:
        writer.add_relation(r)

  _print_progress_bar("Pass 2/2 (writing)", 0.0)
  try:
    writer_handler = _WritePass()
    writer_handler.apply_file(file_in, locations=False)
    writer.close()
    os.replace(tmp_out, file_out)
  except BaseException:
    try:
      writer.close()
    except Exception:
      pass
    if os.path.exists(tmp_out):
      os.remove(tmp_out)
    raise
  _print_progress_bar("Pass 2/2 (writing)", 1.0)

  print("", flush=True)

  print(
      f"pyosmium clip completed: {len(final_nodes)} nodes, "
      f"{len(final_ways)} ways, {len(final_rels)} relations saved to '{file_out}'.",
      flush=True,
  )
def clip_with_pyosmium_fast(
    file_in, file_out, xmin, ymin, xmax, ymax, utm_epsg
):
  try:
    import osmium
  except ImportError as exc:
    raise ImportError(
        "Library 'osmium' (pyosmium) is not installed. Install it with: pip install osmium"
    ) from exc

  safety_pad = 250.0
  box_utm = gpd.GeoDataFrame(
      geometry=[
          box(
              xmin - safety_pad,
              ymin - safety_pad,
              xmax + safety_pad,
              ymax + safety_pad,
          )
      ],
      crs=utm_epsg,
  )
  lon_min, lat_min, lon_max, lat_max = box_utm.to_crs("EPSG:4326").total_bounds

  margin_deg = 0.25
  ext_lon_min = float(lon_min - margin_deg)
  ext_lon_max = float(lon_max + margin_deg)
  ext_lat_min = float(lat_min - margin_deg)
  ext_lat_max = float(lat_max + margin_deg)
  lon_min = float(lon_min)
  lon_max = float(lon_max)
  lat_min = float(lat_min)
  lat_max = float(lat_max)

  print(
      f"Starting pyosmium -fast clip (FileProcessor + IdFilter) on '{file_in}' -> '{file_out}'...",
      flush=True,
  )

  _print_progress_bar("Pass 1/2 (fast scan)", 0.1)
  nodes_in_box = set()
  nearby_nodes = set()
  way_nodes = {}
  rel_members = {}

  for obj in osmium.FileProcessor(file_in):
    if obj.is_node():
      loc = obj.location
      if loc.valid():
        lon = loc.lon
        lat = loc.lat
        if (
            ext_lon_min <= lon <= ext_lon_max
            and ext_lat_min <= lat <= ext_lat_max
        ):
          nid = obj.id
          nearby_nodes.add(nid)
          if lon_min <= lon <= lon_max and lat_min <= lat <= lat_max:
            nodes_in_box.add(nid)
    elif obj.is_way():
      nids = tuple(nd.ref for nd in obj.nodes)
      if any(nid in nearby_nodes for nid in nids):
        way_nodes[obj.id] = nids
    elif obj.is_relation():
      members = tuple((m.type, m.ref) for m in obj.members)
      if any(
          (mtype == "w" and mref in way_nodes)
          or (mtype == "n" and mref in nearby_nodes)
          or (mtype == "r" and mref in rel_members)
          for mtype, mref in members
      ):
        rel_members[obj.id] = members

  nearby_nodes.clear()
  _print_progress_bar("Pass 1/2 (fast scan)", 1.0)
  print("", flush=True)

  final_nodes = set(nodes_in_box)
  final_ways = set()
  for wid, nids in way_nodes.items():
    if any(nid in final_nodes for nid in nids):
      final_ways.add(wid)

  reverse_index = {}
  for rid, members in rel_members.items():
    for mtype, mref in members:
      key = (mtype, mref)
      lst = reverse_index.get(key)
      if lst is None:
        reverse_index[key] = [rid]
      else:
        lst.append(rid)

  final_rels = set()
  queue = []
  for nid in final_nodes:
    for rid in reverse_index.get(("n", nid), ()):
      if rid not in final_rels:
        final_rels.add(rid)
        queue.append(rid)
  for wid in final_ways:
    for rid in reverse_index.get(("w", wid), ()):
      if rid not in final_rels:
        final_rels.add(rid)
        queue.append(rid)

  while queue:
    curr_rid = queue.pop()
    for parent_rid in reverse_index.get(("r", curr_rid), ()):
      if parent_rid not in final_rels:
        final_rels.add(parent_rid)
        queue.append(parent_rid)

  reverse_index.clear()

  for rid in final_rels:
    for mtype, mref in rel_members.get(rid, ()):
      if mtype == "w" and mref in way_nodes:
        final_ways.add(mref)
      elif mtype == "n":
        final_nodes.add(mref)

  for wid in final_ways:
    final_nodes.update(way_nodes.get(wid, ()))

  way_nodes.clear()
  rel_members.clear()
  nodes_in_box.clear()

  base_out, ext_out = os.path.splitext(file_out)
  tmp_out = f"{base_out}.tmp{ext_out}"
  if os.path.exists(tmp_out):
    os.remove(tmp_out)

  _print_progress_bar("Pass 2/2 (C++ write)", 0.2)
  writer = osmium.SimpleWriter(tmp_out)
  all_ids = final_nodes | final_ways | final_rels

  try:
    for obj in osmium.FileProcessor(file_in).with_filter(
        osmium.filter.IdFilter(all_ids)
    ):
      if obj.is_node() and obj.id in final_nodes:
        writer.add_node(obj)
      elif obj.is_way() and obj.id in final_ways:
        writer.add_way(obj)
      elif obj.is_relation() and obj.id in final_rels:
        writer.add_relation(obj)
    writer.close()
    os.replace(tmp_out, file_out)
  except BaseException:
    try:
      writer.close()
    except Exception:
      pass
    if os.path.exists(tmp_out):
      os.remove(tmp_out)
    raise
  _print_progress_bar("Pass 2/2 (C++ write)", 1.0)

  print("", flush=True)

  print(
      f"pyosmium -fast clip completed: {len(final_nodes)} nodes, "
      f"{len(final_ways)} ways, {len(final_rels)} relations saved to '{file_out}'.",
      flush=True,
  )
def georeference_pdf(
    pdf_path,
    xmin,
    ymin,
    xmax,
    ymax,
    utm_epsg,
    margin_mm,
    map_w_mm,
    map_h_mm,
    body_h_mm,
    tot_w_mm,
    tot_h_mm,
):
  try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (
        ArrayObject,
        DictionaryObject,
        FloatObject,
        NameObject,
        NumberObject,
        TextStringObject,
    )
  except ImportError:
    print(
        "[WARNING] Library 'pypdf' is not installed: PDF saved without georeferencing (pip install pypdf).",
        flush=True,
    )
    return

  from pyproj import Transformer

  # Convert the 4 corners of the map frame to WGS84 (lat, lon) as required by ISO 32000 for georeferenced PDFs
  tr = Transformer.from_crs(utm_epsg, "EPSG:4326", always_xy=True)
  lon_bl, lat_bl = tr.transform(xmin, ymin)  # Bottom-Left (South-West)
  lon_tl, lat_tl = tr.transform(xmin, ymax)  # Top-Left (North-West)
  lon_tr, lat_tr = tr.transform(xmax, ymax)  # Top-Right (North-East)
  lon_br, lat_br = tr.transform(xmax, ymin)  # Bottom-Right (South-Est)

  _, epsg_str = utm_epsg.split(":")
  epsg_num = int(epsg_str)
  zone = epsg_num % 100
  hemisphere = "North" if epsg_num < 32700 else "South"
  wkt_utm = (
      f'PROJCS["WGS 84 / UTM zone {zone}{"N" if hemisphere == "North" else "S"}",'
      'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
      'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],'
      'PROJECTION["Transverse_Mercator"],'
      'PARAMETER["latitude_of_origin",0],'
      f'PARAMETER["central_meridian",{-183 + zone * 6}],'
      'PARAMETER["scale_factor",0.9996],'
      'PARAMETER["false_easting",500000],'
      f'PARAMETER["false_northing",{0 if hemisphere == "North" else 10000000}],'
      'UNIT["metre",1]]'
  )

  reader = PdfReader(pdf_path)
  writer = PdfWriter()
  page = next(iter(reader.pages))

  mm_to_pt = 72.0 / 25.4
  x0_pt = margin_mm * mm_to_pt
  y0_pt = (margin_mm + body_h_mm - map_h_mm) * mm_to_pt
  x1_pt = (margin_mm + map_w_mm) * mm_to_pt
  y1_pt = (margin_mm + body_h_mm) * mm_to_pt

  gcs = DictionaryObject({
      NameObject("/Type"): NameObject("/PROJCS"),
      NameObject("/EPSG"): NumberObject(epsg_num),
      NameObject("/WKT"): TextStringObject(wkt_utm),
  })

  measure = DictionaryObject({
      NameObject("/Type"): NameObject("/Measure"),
      NameObject("/Subtype"): NameObject("/GEO"),
      NameObject("/GCS"): gcs,
      NameObject("/Bounds"): ArrayObject([
          FloatObject(0.0), FloatObject(0.0),
          FloatObject(0.0), FloatObject(1.0),
          FloatObject(1.0), FloatObject(1.0),
          FloatObject(1.0), FloatObject(0.0),
      ]),
      NameObject("/GPTS"): ArrayObject([
          FloatObject(lat_bl), FloatObject(lon_bl),
          FloatObject(lat_tl), FloatObject(lon_tl),
          FloatObject(lat_tr), FloatObject(lon_tr),
          FloatObject(lat_br), FloatObject(lon_br),
      ]),
      NameObject("/LPTS"): ArrayObject([
          FloatObject(0.0), FloatObject(0.0),
          FloatObject(0.0), FloatObject(1.0),
          FloatObject(1.0), FloatObject(1.0),
          FloatObject(1.0), FloatObject(0.0),
      ]),
  })

  vp = DictionaryObject({
      NameObject("/Type"): NameObject("/Viewport"),
      NameObject("/Name"): TextStringObject("Map"),
      NameObject("/BBox"): ArrayObject([
          FloatObject(x0_pt),
          FloatObject(y0_pt),
          FloatObject(x1_pt),
          FloatObject(y1_pt),
      ]),
      NameObject("/Measure"): measure,
  })

  page[NameObject("/VP")] = ArrayObject([vp])
  writer.add_page(page)
  if reader.metadata:
    writer.add_metadata(reader.metadata)

  tmp_pdf = pdf_path + ".tmp"
  with open(tmp_pdf, "wb") as f_out:
    writer.write(f_out)
  os.replace(tmp_pdf, pdf_path)
def main():
  t_start = time.perf_counter()
  args = parse_args()
  strings, active_lang = load_language(args.lang)

  if not args.outpdf.lower().endswith(".pdf"):
    args.outpdf += ".pdf"

  if os.path.exists(args.outpdf):
    try:
      with open(args.outpdf, "a+b"):
        pass
    except PermissionError:
      print(
          f"[ERROR] Output PDF file '{args.outpdf}' is currently locked or open in another program. "
          "Close it and try again.",
          file=sys.stderr,
          flush=True,
      )
      sys.exit(1)

  if not args.outosm.lower().endswith((".osm", ".pbf")):
    print(
        f"[WARNING] Invalid -outosm extension ('{args.outosm}'): appending '.osm' -> '{args.outosm}.osm'",
        flush=True,
    )
    args.outosm += ".osm"

  if not os.path.isfile(args.track):
    print(
        f"[ERROR] GPX track file not found: '{os.path.abspath(args.track)}'",
        file=sys.stderr,
        flush=True,
    )
    sys.exit(1)

  if args.inosm:
    if not os.path.isfile(args.inosm):
      print(
          f"[ERROR] Source OSM file (-inosm) not found: '{os.path.abspath(args.inosm)}'",
          file=sys.stderr,
          flush=True,
      )
      sys.exit(1)
  elif not os.path.isfile(args.outosm):
    print(
        f"[ERROR] Clipped OSM file (-outosm) not found: '{os.path.abspath(args.outosm)}'. "
        "Specify -inosm to generate it.",
        file=sys.stderr,
        flush=True,
    )
    sys.exit(1)

  print(
      f"Scale 1:{args.scale} | Symbol/label scale factor (-symscale): {args.symscale_val} | Language: {active_lang}",
      flush=True,
  )
  print(f"Loading GPX track: {args.track}", flush=True)
  gdf_gpx, utm_epsg, utm_label = load_gpx_track(args.track, args.utm)
  gxmin, gymin, gxmax, gymax = gdf_gpx.total_bounds

  gdfs_var = []
  for path_var in args.trackvar:
    if not os.path.isfile(path_var):
      print(
          f"[ERROR] GPX variant file not found: '{os.path.abspath(path_var)}'",
          file=sys.stderr,
          flush=True,
      )
      sys.exit(1)
    print(f"Loading GPX variant: {path_var}", flush=True)
    gdf_v, _, _ = load_gpx_track(path_var, args.utm)
    gdfs_var.append(gdf_v)
    vxmin, vymin, vxmax, vymax = gdf_v.total_bounds
    gxmin = min(gxmin, vxmin)
    gymin = min(gymin, vymin)
    gxmax = max(gxmax, vxmax)
    gymax = max(gymax, vymax)

  xmin = math.floor((gxmin - args.pad) / 1000.0) * 1000.0
  ymin = math.floor((gymin - args.pad) / 1000.0) * 1000.0
  xmax = math.ceil((gxmax + args.pad) / 1000.0) * 1000.0
  ymax = math.ceil((gymax + args.pad) / 1000.0) * 1000.0

  print(
      f"Bounding box {utm_label} ({utm_epsg}): X={int(xmin)} .. {int(xmax)}, Y={int(ymin)} .. {int(ymax)}",
      flush=True,
  )

  if args.inosm:
    do_clip = True
    if os.path.exists(args.outosm) and not args.force:
      ans = (
          input(
              f"File '{args.outosm}' already exists. Overwrite it with pyosmium? [y/N]: "
          )
          .strip()
          .lower()
      )
      if ans not in ("y", "yes", "s", "si", "sì"):
        do_clip = False
        print(f"Using existing file: {args.outosm}", flush=True)

    if do_clip:
      if args.superfast:
        clip_fn = clip_with_pyosmium_superfast
      elif args.fast:
        clip_fn = clip_with_pyosmium_fast
      else:
        clip_fn = clip_with_pyosmium
      clip_fn(
          args.inosm,
          args.outosm,
          xmin,
          ymin,
          xmax,
          ymax,
          utm_epsg,
      )

  if not os.path.exists(args.outosm):
    raise FileNotFoundError(
        f"Clipped OSM file not found: {args.outosm}. Specify -inosm to generate it."
    )
  map_w_mm = ((xmax - xmin) * 1000.0) / args.scale
  map_h_mm = ((ymax - ymin) * 1000.0) / args.scale

  layout = compute_legend_layout(map_h_mm)
  margin_mm = 12.0
  gap_mm = 5.0
  legend_w_mm = layout["w_mm"]
  legend_h_mm = layout["h_mm"]

  body_h_mm = max(map_h_mm, legend_h_mm)
  tot_w_mm = margin_mm + map_w_mm + gap_mm + legend_w_mm + margin_mm
  tot_h_mm = margin_mm + body_h_mm + margin_mm

  fig = plt.figure(figsize=(tot_w_mm / 25.4, tot_h_mm / 25.4), dpi=300)
  ax_m = fig.add_axes((
      margin_mm / tot_w_mm,
      (margin_mm + body_h_mm - map_h_mm) / tot_h_mm,
      map_w_mm / tot_w_mm,
      map_h_mm / tot_h_mm,
  ))
  ax_l = fig.add_axes((
      (margin_mm + map_w_mm + gap_mm) / tot_w_mm,
      (margin_mm + body_h_mm - legend_h_mm) / tot_h_mm,
      legend_w_mm / tot_w_mm,
      legend_h_mm / tot_h_mm,
  ))
  ax_l.set_axis_off()

  ax_m.set_xlim(xmin, xmax)
  ax_m.set_ylim(ymin, ymax)
  ax_m.set_aspect("equal")

  fmt_int = FuncFormatter(lambda val, pos: f"{int(round(val))}")
  ax_m.xaxis.set_major_formatter(fmt_int)
  ax_m.yaxis.set_major_formatter(fmt_int)
  ax_m.tick_params(axis="x", labelsize=6.0, pad=2)
  ax_m.tick_params(axis="y", labelsize=6.0, pad=2)
  ax_m.set_xlabel(strings["east_label"], fontsize=6.5, labelpad=3)
  ax_m.set_ylabel(strings["north_label"], fontsize=6.5, labelpad=3)
  yticks_lbl = ax_m.get_yticklabels()
  for idx, lbl in enumerate(yticks_lbl):
    lbl.set_rotation(90)
    if idx == 0:
      lbl.set_verticalalignment("bottom")
    elif idx == len(yticks_lbl) - 1:
      lbl.set_verticalalignment("top")
    else:
      lbl.set_verticalalignment("center")

  ax_m.text(
      0.0,
      1.008,
      utm_label,
      transform=ax_m.transAxes,
      fontsize=6.2,
      fontweight="bold",
      color="#222222",
      ha="left",
      va="bottom",
  )

  xticks = list(range(int(xmin), int(xmax) + 1000, 1000))
  yticks = list(range(int(ymin), int(ymax) + 1000, 1000))
  ax_m.set_xticks(xticks)
  ax_m.set_yticks(yticks)
  ax_m.grid(
      True, color="#4a90e2", linestyle="-", linewidth=0.35, alpha=0.55, zorder=90
  )

  bbox_poly = box(xmin, ymin, xmax, ymax)

  print(f"Loading OSM data: {args.outosm}", flush=True)
  points, lines, polygons = load_osm_data(
      args.outosm, bbox_poly, names_path=args.exclude, utm_epsg=utm_epsg, debug=args.debug
  )


  print(
      f"  OSM features in bounding box: {len(points)} points, {len(lines)} lines, {len(polygons)} polygons",
      flush=True,
  )

  gdf_contours = None
  if args.dtm and (
      os.path.exists(args.dtm) or any(ch in args.dtm for ch in ("*", "?"))
  ):
    print(
        f"Generating contour lines from DTM ({int(args.dtmsec)} m / {int(args.dtmmain)} m): {args.dtm}",
        flush=True,
    )
    gdf_contours = generate_contours_from_dtm(
        args.dtm,
        bbox_poly,
        step_m=args.dtmsec,
        major_step_m=args.dtmmain,
        utm_epsg=utm_epsg,
    )
  elif args.contours and os.path.exists(args.contours):
    print(f"Loading contour lines: {args.contours}", flush=True)
    _, gdf_contours, _ = load_osm_data(
        args.contours, bbox_poly, utm_epsg=utm_epsg
    )


  print("Rendering TOPO cartographic layers...", flush=True)
  draw_topo_polygons(ax_m, polygons, xmin, ymin, xmax, ymax, args.scale)
  draw_lines_and_contours(ax_m, lines, gdf_contours, bbox_poly, scale=args.scale, major_step_m=args.dtmmain)


  gdf_gpx.plot(
      ax=ax_m,
      color="#d90429",
      linewidth=2.2,
      alpha=0.90,
      zorder=100,
      capstyle="round",
      joinstyle="round",
  )

  for gdf_v in gdfs_var:
    gdf_v.plot(
        ax=ax_m,
        color="#d90429",
        linewidth=2.2,
        linestyle=(0, (4.5, 3.5)),
        alpha=0.92,
        zorder=99.2,
        capstyle="butt",
        joinstyle="round",
    )

  start_pt = None
  geom0 = next(iter(gdf_gpx.geometry))
  track_coords = list(geom0.coords)
  if track_coords:
    sx, sy = next(iter(track_coords))
    start_pt = (sx, sy)
    u = (1.1 * args.symscale_val * args.scale) / 1000.0
    ax_m.plot(
        (sx, sx),
        (sy, sy + 4.2 * u),
        color="#000000",
        linewidth=1.1 * args.symscale_val,
        zorder=106,
    )
    for col_i in range(3):
      for row_i in range(2):
        sq_col = "#000000" if (col_i + row_i) % 2 == 1 else "#ffffff"
        rect = Rectangle(
            (sx + col_i * u, sy + (2.2 + row_i) * u),
            u,
            u,
            facecolor=sq_col,
            edgecolor="#000000",
            linewidth=0.35 * args.symscale_val,
            zorder=107,
        )
        ax_m.add_patch(rect)

  draw_points_and_labels(
      ax_m,
      points,
      lines,
      polygons,
      args.scale,
      map_bbox=bbox_poly,
      overrides_path=args.labels,
      symscale=args.symscale_val,
      start_pt=start_pt,
  )

  base_name = next(iter(os.path.splitext(os.path.basename(args.track))))
  title = args.title or base_name.replace("_", " ").upper()

  if active_lang == "it" and (
      not args.credits_text.strip()
      or "Generated with osm2topopdf" in args.credits_text
  ):
    final_credits = strings["default_credits"].format(
        version=VERSION,
        dtmsec=int(round(args.dtmsec)),
        utm=utm_label,
    )
  else:
    final_credits = (
        args.credits_text.replace("{VERSION}", VERSION)
        .replace("{UTM}", utm_label)
        .replace("UTM Zone 32N", utm_label)
        .replace("UTM 32N", utm_label)
        .replace("{dtmsec}", str(int(round(args.dtmsec))))
        .replace("eq. 25 m", f"eq. {int(round(args.dtmsec))} m")
    )

  draw_legend(
      ax_l,
      title,
      args.scale,
      layout,
      strings=strings,
      author=args.author,
      date_str=args.date,
      credits_text=final_credits,
      utm_label=utm_label,
      version=VERSION,
      dtmmain=int(round(args.dtmmain)),
      dtmsec=int(round(args.dtmsec)),
  )


  pdf_metadata = {
      "Title": title,
      "Author": args.author,
      "Creator": f"osm2topopdf v{VERSION}",
      "Subject": strings["pdf_subject"].format(
          scale=args.scale, utm=utm_label
      ),
  }

  print(f"Saving PDF: {args.outpdf}", flush=True)
  fig.savefig(args.outpdf, format="pdf", metadata=pdf_metadata)
  plt.close(fig)
  georeference_pdf(
      args.outpdf,
      xmin,
      ymin,
      xmax,
      ymax,
      utm_epsg,
      margin_mm,
      map_w_mm,
      map_h_mm,
      body_h_mm,
      tot_w_mm,
      tot_h_mm,
  )

  dt_tot = time.perf_counter() - t_start
  minutes, seconds = divmod(dt_tot, 60.0)
  print(
      f"Map osm2topopdf v{VERSION} generated successfully in "
      f"{int(minutes)}m {seconds:05.2f}s ({dt_tot:.2f}s)!",
      flush=True,
  )


def clip_with_pyosmium_superfast(
    file_in, file_out, xmin, ymin, xmax, ymax, utm_epsg
):
  try:
    import osmium
  except ImportError as exc:
    raise ImportError(
        "Library 'osmium' (pyosmium) is not installed. Install it with: pip install osmium"
    ) from exc

  safety_pad = 250.0
  box_utm = gpd.GeoDataFrame(
      geometry=[
          box(
              xmin - safety_pad,
              ymin - safety_pad,
              xmax + safety_pad,
              ymax + safety_pad,
          )
      ],
      crs=utm_epsg,
  )
  lon_min, lat_min, lon_max, lat_max = box_utm.to_crs("EPSG:4326").total_bounds
  lon_min = float(lon_min)
  lon_max = float(lon_max)
  lat_min = float(lat_min)
  lat_max = float(lat_max)

  total_size = max(1, os.path.getsize(file_in))
  bytes_per_obj = 9.0 if file_in.lower().endswith(".pbf") else 110.0
  est_objects = max(1.0, total_size / bytes_per_obj)

  base_out, ext_out = os.path.splitext(file_out)
  tmp_out = f"{base_out}.tmp{ext_out}"
  if os.path.exists(tmp_out):
    os.remove(tmp_out)

  print(
      f"Starting pyosmium -superfast clip (BackReferenceWriter C++) on '{file_in}' -> '{file_out}'...",
      flush=True,
  )

  _print_progress_bar("Single pass (BackReferenceWriter)", 0.0)
  nodes_in_box = set()
  ways_in_box = set()
  count = 0

  try:
    with osmium.BackReferenceWriter(
        tmp_out, ref_src=file_in, overwrite=True
    ) as writer:
      for obj in osmium.FileProcessor(file_in):
        count += 1
        if (count & 131071) == 0:
          ratio = count / est_objects
          frac = min(0.99, ratio / (1.0 + 0.12 * ratio))
          _print_progress_bar("Single pass (BackReferenceWriter)", frac)

        if obj.is_node():
          loc = obj.location
          if loc.valid():
            if lon_min <= loc.lon <= lon_max and lat_min <= loc.lat <= lat_max:
              nodes_in_box.add(obj.id)
              writer.add(obj)
        elif obj.is_way():
          if any(nd.ref in nodes_in_box for nd in obj.nodes):
            ways_in_box.add(obj.id)
            writer.add(obj)
        elif obj.is_relation():
          if any(
              (m.type == "w" and m.ref in ways_in_box)
              or (m.type == "n" and m.ref in nodes_in_box)
              for m in obj.members
          ):
            writer.add(obj)
    os.replace(tmp_out, file_out)
  except BaseException:
    if os.path.exists(tmp_out):
      os.remove(tmp_out)
    raise

  _print_progress_bar("Single pass (BackReferenceWriter)", 1.0)
  print("", flush=True)
  print(
      f"pyosmium -superfast clip completed in '{file_out}'.",
      flush=True,
  )



if __name__ == "__main__":
  try:
    main()
  except SystemExit:
    raise
  except Exception:
    import traceback
    traceback.print_exc()
  finally:
    _wait_if_double_clicked()
