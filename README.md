<p align="center">
  <img src="assets/osm2topopdf.jpg" alt="osm2topopdf banner" width="100%">
</p>

# osm2topopdf

**Topographic Georeferenced PDF Map Generator from OpenStreetMap Data and GPX Tracks**

Utility by **Massimo Peverada** to make a georeferenced PDF from OSM data, given one or more GPX tracks, based on a FreeBASIC utility to convert OSM to DXF, ported to Python and developed with the help of Gemini.

Released under the **GNU General Public License v3.0 (GPLv3)**.

---

## Features

- **Cartographic TOPO Styling:** Renders landcover polygons, buildings, road hierarchies, rough/forest tracks with parallel edges, marked hiking and MTB/cycle trails, railways, aerialways, waterways, and custom vector symbols.
- **Georeferenced PDF Output:** Embeds ISO 32000 geospatial metadata (`EPSG` / `WKT` / `Viewport`) directly into the output PDF, ready for mobile GPS apps (e.g., Avenza Maps, Locus Map, QField) and GIS software.
- **Contour Lines from DTM or OSM:** Generates smooth index and intermediate contour lines directly from ESRI ASCII Grid (`.asc`) Digital Terrain Models (single file or multi-tile folder) or loads pre-existing OSM contour files.
- **Fast OSM Clipping:** Integrates `pyosmium` (including C++ `-fast` and single-pass `-superfast` modes) to extract the required bounding box directly from large `.osm.pbf` extracts.
- **Smart Label & Symbol Placement:** Priority-based classification engine with 400 m deduplication, border clipping, and bounding-box collision avoidance.
- **Multilingual Legend & Axes:** Defaults to English (`-lang en`), with built-in support for Italian (`-lang it`), French (`-lang fr`), German (`-lang de`), and Spanish (`-lang es`), plus easy extensibility to other languages.
- **Automatic UTM Zone Detection:** Automatically selects the appropriate WGS 84 UTM zone from the GPX track centroid (or accepts a manual zone such as `32N` or `19S`).

---

## Requirements & Installation

Requires **Python 3.10 or higher** (tested on Python 3.13).

1. Clone or download this repository:
   ```bash
   git clone https://github.com/MassimoPeverada/osm2topopdf.git
   cd osm2topopdf
   ```

2. Install the required Python libraries:
   ```bash
   pip install -r requirements.txt
   ```

---

## Quick Start

### 1. Basic map from an already clipped `.osm` file
```bash
python osm2topopdf.py -track my_hike.gpx -outosm area.osm -outpdf my_hike.pdf
```

### 2. Clip directly from a large `.osm.pbf` extract + generate DTM contours
```bash
python osm2topopdf.py -track my_hike.gpx -inosm region-latest.osm.pbf -outosm area.osm -dtm ./dtm_folder -fast -outpdf my_hike.pdf
```

### 3. Generate a map with Italian legend and axis labels (`-lang it`)
```bash
python osm2topopdf.py -track my_hike.gpx -outosm area.osm -lang it -title "MONTE ROSA TOUR" -author "Massimo Peverada" -outpdf my_hike_it.pdf
```

### 4. Include route variants and custom scale
```bash
python osm2topopdf.py -track main_route.gpx -trackvar variant1.gpx variant2.gpx -scale 15000 -outpdf detailed_map.pdf
```

---
## Command-Line Options

Running `python osm2topopdf.py` with no arguments prints the full help message and creates a default `osm2topopdf.ini` configuration file if one does not exist.

### Input & Output Files

| Option | Default | Description |
| :--- | :--- | :--- |
| `-track <file>` | `track.gpx` | Main GPX track file to display on the map (also accepted as a positional argument). |
| `-trackvar <files...>` | *(none)* | One or more optional GPX route variant files, drawn as dashed red lines. |
| `-inosm <file>` | *(from INI)* | Full source OSM file (`.osm.pbf` or `.osm`). If specified, clips the map area using `pyosmium`. |
| `-outosm <file>` | `section.osm` | Clipped OSM file written by `pyosmium` (or read directly if `-inosm` is omitted). |
| `-outpdf <file>` | `topo_map.pdf` | Output georeferenced PDF filename. |
| `-config <file>` | `osm2topopdf.ini` | Path to the INI configuration file. |

### OSM Clipping Performance (`pyosmium`)

| Option | Default | Description |
| :--- | :--- | :--- |
| `-fast` | `False` | Uses native C++ `pyosmium` filters (`FileProcessor` + `IdFilter`) for faster clipping. |
| `-superfast` | `False` | Single-pass clipping using `pyosmium` C++ `BackReferenceWriter` (fastest on large `.pbf` files). |
| `-force` | `False` | Overwrites an existing `-outosm` file without asking for confirmation. |

### Elevation & Contour Lines

| Option | Default | Description |
| :--- | :--- | :--- |
| `-dtm <path>` | *(from INI)* | **Recommended.** ESRI ASCII Grid (`.asc`) DTM file, folder of `.asc` tiles, or wildcard pattern to generate smooth contour lines. |
| `-dtmmain <meters>` | `100` | Elevation interval in meters for index (major) contour lines. |
| `-dtmsec <meters>` | `25` | Elevation interval in meters for intermediate (minor) contour lines. |
| `-contours <file>` | `contour_lines.osm` | *Optional / legacy.* Pre-generated OSM XML file containing contour ways tagged with `contour=elevation` and `ele=<meters>` (e.g., created with `phyghtmap`). Ignored if `-dtm` is provided, and safely skipped if the file does not exist. |

#### Supported DTM & Contour Format Specifications
- **DTM File Format (`-dtm`):** **ESRI ASCII Grid** (`.asc` / `.ASC`) with standard 6-line header (`ncols`, `nrows`, `xllcorner`/`xllcenter`, `yllcorner`/`yllcenter`, `cellsize`, `nodata_value`). Both dot (`.`) and comma (`,`) decimal separators are supported.
- **DTM Input Modes:** Accepts a single `.asc` file, a folder containing multiple `.asc` tiles (automatically mosaicked over the map bounding box), or a wildcard pattern (e.g., `./dtm/*.asc`).
- **DTM Coordinate Reference System (CRS):** DTM coordinates must match the **projected UTM coordinate system** of the map (e.g., WGS 84 / UTM Zone 32N, `EPSG:32632`).
- **Pre-generated OSM XML Contours (`-contours`):** Standard OSM XML (`.osm`) in WGS 84 (`EPSG:4326`) containing ways tagged with `contour=elevation`, `ele=<meters>`, and optional `contour_ext=elevation_major` / `elevation_minor` (e.g., generated with `phyghtmap` / `pyhgtmap`).

### Map Layout, Scale & Language

| Option | Default | Description |
| :--- | :--- | :--- |
| `-scale <int>` | `25000` | Cartographic scale denominator, between `5000` and `75000` (e.g., `25000` for 1:25,000, `50000` for 1:50,000). |
| `-pad <meters>` | `500` | Minimum buffer around the GPX track in meters (automatically rounded outward to 1,000 m grid lines). |
| `-symscale <val>` | `auto` | Scale factor for symbols, labels, and road/line widths (`auto` adjusts automatically with `-scale`, or pass a number like `0.8` or `1.2`). |
| `-utm <zone>` | `auto` | WGS 84 UTM zone (`auto` detects from GPX centroid, or specify e.g. `32N`, `33N`, `19S`). |
| `-lang <code>` | `en` | Language code for legend, axes, and PDF metadata (`en` built-in; `it`, `fr`, `de`, `es` included via `lang_<code>.json`). Falls back to `en` if the file is missing. |
| `-title <text>` | *(GPX filename)* | Title printed at the top of the legend. |
| `-author <text>` | *(from INI)* | Author name printed below the scale. |
| `-date <text>` | *(today)* | Date printed in the legend (pass `""` to omit). |

### Filtering & Custom Overrides

| Option | Default | Description |
| :--- | :--- | :--- |
| `-exclude <file>` | `names.txt` | Optional text file to hide unwanted labels via text rules (`begins: text`, `equals: text`, `contains: text`) or OSM tag/area rules (`@exclude: key=val1,val2` with optional area filter). |
| `-labels <file>` | `labels.txt` | Optional file for custom label coordinates, offsets, or priority overrides. |

---

## Configuration File (`osm2topopdf.ini`)

On first run, `osm2topopdf` generates `osm2topopdf.ini` in the working directory. You can store your recurring paths (such as your regional `.osm.pbf` extract, local DTM folder, default language, author name, and map credits) there so you don't have to type them every time. Command-line flags always override INI values.

---

## Adding a New Language

English strings are built into `i18n.py`. To add another language (for example, Portuguese `pt`):
1. Copy `lang_it.json` to `lang_pt.json` in the same directory as `osm2topopdf.py`.
2. Translate the values while keeping the JSON keys unchanged.
3. Run the tool with `-lang pt` (or set `lang = pt` in `osm2topopdf.ini`).

---

## Project Structure

- `osm2topopdf.py` – Main CLI entry point, GPX loader, `pyosmium` clipper, and georeferenced PDF builder
- `i18n.py` / `lang_*.json` – Internationalization loader and translations (`it`, `fr`, `de`, `es`)
- `osm_loader.py` – OSM XML/PBF parser, multipolygon assembler, and spatial clipper
- `dtm_contours.py` – Multi-tile ESRI `.asc` DTM reader and contour line generator
- `topo_polygons.py` – Landcover, water, protected areas, and building renderer
- `topo_lines.py` – Roads, tracks, trails, railways, aerialways, waterways, and labeled contours renderer
- `topo_points_labels.py` – Symbol placement and collision-free label engine
- `topo_classifier.py` – OSM feature classification rules
- `topo_labels_config.py` – Font styles and priority definitions
- `topo_symbols.py` – Custom vector markers
- `legend.py` – Adaptive single/two-column topographic map legend
- `names.txt` – Sample universal OSM tag/area and text label exclusion rules

---
## License & Data Attribution

- **Software:** Licensed under the GNU General Public License v3.0 (GPLv3).
- **OpenStreetMap Data:** Map features rendered by this tool come from OpenStreetMap (`© OpenStreetMap contributors`, licensed under the ODbL). Proper attribution to OpenStreetMap is mandatory when publishing or distributing generated maps.
- **Elevation Data (DTM):** Digital Terrain Models are not included in this repository. If you use external DTM files (`-dtm`) to generate contour lines, **you are responsible for complying with the provider's license terms and adding the required copyright notice** in the credits section of `osm2topopdf.ini` before distributing the resulting PDF maps.

---

## Disclaimer

**Use this utility at your own risk.**  
This software is provided "as is", without warranty of any kind, express or implied, in accordance with the GNU General Public License v3.0 (GPLv3).

The maps generated by `osm2topopdf` rely on crowd-sourced OpenStreetMap data and third-party elevation models, which may contain inaccuracies, omissions, or outdated information. **Do not rely solely on these maps for navigation, mountaineering, or outdoor safety.** Always verify routes on the ground, carry official cartography and proper navigation equipment, and check local trail and weather conditions before heading outdoors. The author assumes no responsibility or liability for any accidents, injuries, damages, or losses resulting from the use of this software or the maps it produces.

**No Affiliation:** `osm2topopdf` is an independent open-source project and is not affiliated with, endorsed by, or sponsored by the OpenStreetMap Foundation (OSMF), the Free Software Foundation (FSF), or any other third-party organization or data provider mentioned in this documentation. All trademarks and data copyrights belong to their respective owners.

## Getting OpenStreetMap Data (`.osm.pbf`)

To generate maps for your area, download a regional OpenStreetMap extract in `.osm.pbf` format from one of the free public mirrors:

- **Geofabrik Download Server:** `download.geofabrik.de` (organized by continent, country, and region — e.g., `italy-nord-ovest-latest.osm.pbf`)

Save the downloaded `.osm.pbf` file locally and pass it via `-inosm <file.osm.pbf>` (or set `inosm = ...` once in `osm2topopdf.ini`).

## Roadmap

Planned features and improvements for upcoming releases (v1.2.0+):

- **Layer & Feature Filtering (`layers` in `osm2topopdf.ini`):** Toggle individual map layers (`buildings`, `landcover`, `contours`, `roads`, `trails`, `railways`, `waterways`, `poi_shops`, `labels`) on or off without editing code.
- **GeoTIFF DEM Support:** Add native support for `.tif` / `.tiff` Digital Elevation Models alongside ESRI ASCII Grid (`.asc`).
- **Additional Language Packs:** Community translations (e.g., Portuguese, Dutch, Polish) via `lang_<code>.json` files.

## Changelog

### v1.1.9 (2026-11-25)
- Added universal OSM tag and polygon area label filtering (`@exclude: key=val1,val2` with optional area filter) in `names.txt` (`-exclude`), hiding unwanted shop, restaurant, and small company labels while preserving building footprints and map symbols, plus an updated `names.txt` sample file in the repository root.
- Added line-numbered syntax validation warnings when loading `names.txt`.
- Added automatic case-insensitive file matching for CLI path arguments (`-track`, `-trackvar`, `-inosm`, `-dtm`, `-contours`, `-exclude`, `-labels`, `-config`) across both Windows and Linux.
- Enforced `-scale` range between `5000` and `75000` and extended `-symscale` proportional scaling to road, track, railway, and waterway widths (with slimmer `highway=service` styling to prevent parking-aisle clutter at 1:50,000).
- Increased label deduplication radius to `400 m` for cleaner maps at overview scales and added an early file-lock check when the output PDF is already open.

### v1.1.8 (2026-11-24)
- Added automatic topological closing of clipped multipolygons along the map bounding box (enabling full rendering of large rivers, forests, and parks even with `-fast` and `-superfast`).
- Updated hydrographic layer `zorder` so riverbank polygons cleanly cover river centerlines (`waterway=river`).
- Eliminated visible seam lines at joints between adjacent riverbank/water polygons while keeping crisp shoreline outlines.
- Filtered out urban `barrier=gate` nodes to reduce map clutter, keeping gates only along rural tracks, paths, and cycleways while preserving `lift_gate` and `swing_gate` barriers everywhere.
- Smoothed hiking and cycling route highlights using `linemerge` and butt capstyles to prevent opacity overlaps at segment joints.
- Added hidden `-debug` diagnostic flag for multipolygon inspection.

### v1.1.7 (2026-11-24)
- Initial public release.