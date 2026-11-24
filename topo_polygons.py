import geopandas as gpd
import pandas as pd


def _col(df, name):
  return df[name] if name in df.columns else pd.Series(None, index=df.index)


LANDCOVER_STYLES = [
    (
        "meadows",
        lambda df: _col(df, "landuse").isin(["meadow", "grass", "pasture"])
        | _col(df, "natural").isin(["grassland", "fell"]),
        "#dff0cf",
        "none",
        0,
    ),
    (
        "farmland",
        lambda df: _col(df, "landuse").isin(
            ["farmland", "orchard", "vineyard", "allotments"]
        ),
        "#f2fae3",
        "#d8e2c8",
        0.15,
    ),
    (
        "parks_green",
        lambda df: _col(df, "leisure").isin(["park", "garden", "golf_course"]),
        "#cdebc5",
        "#95d5b2",
        0.25,
    ),
    (
        "scrub",
        lambda df: _col(df, "natural").isin(["scrub", "heath"]),
        "#d8e8c8",
        "none",
        0,
    ),
    (
        "sand",
        lambda df: _col(df, "natural").isin(["sand", "beach"]),
        "#f7e7b4",
        "#e0c989",
        0.2,
    ),
    (
        "glaciers",
        lambda df: _col(df, "natural") == "glacier",
        "#e0fbfc",
        "#90e0ef",
        0.4,
    ),
    (
        "wetlands",
        lambda df: _col(df, "natural") == "wetland",
        "#cdeef7",
        "#7cc6de",
        0.3,
    ),
    (
        "rocks_quarries",
        lambda df: _col(df, "natural").isin(
            ["bare_rock", "scree", "shingle", "rock"]
        )
        | _col(df, "landuse").isin(["quarry", "landfill"]),
        "#e6dedb",
        "#b5aca9",
        0.25,
    ),
    (
        "sports",
        lambda df: _col(df, "leisure").isin(
            ["pitch", "sports_centre", "stadium"]
        ),
        "#d9f2d9",
        "#52b788",
        0.35,
    ),
    (
        "cemeteries",
        lambda df: (_col(df, "landuse") == "cemetery")
        | (_col(df, "amenity") == "grave_yard"),
        "#c9d6c8",
        "#6c757d",
        0.35,
    ),
    (
        "military",
        lambda df: _col(df, "landuse") == "military",
        "#f5d0d0",
        "#c9184a",
        0.5,
    ),
    (
        "urban",
        lambda df: _col(df, "landuse").isin(
            ["residential", "industrial", "commercial", "retail", "farmyard"]
        )
        | _col(df, "amenity").isin(["prison"])
        | _col(df, "aeroway").isin(["aerodrome"])
        | _col(df, "power").isin(["substation", "generator"])
        | (_col(df, "man_made") == "wastewater_plant"),
        "#d1d1d1",
        "#999999",
        0.2,
    ),
    (
        "forests",
        lambda df: (_col(df, "landuse") == "forest")
        | (_col(df, "natural") == "wood"),
        "#ace5b6",
        "none",
        0,
    ),
]

OVERLAY_STYLES = [
    (
        "water",
        lambda df: (_col(df, "natural") == "water")
        | (_col(df, "waterway") == "riverbank")
        | _col(df, "landuse").isin(["basin"])
        | _col(df, "leisure").isin(["swimming_pool", "water_park"]),
        "#bae8ff",
        "#5cc2d1",
        0.5,
        20,
    ),
    (
        "buildings",
        lambda df: _col(df, "building").notna() & (_col(df, "building") != "no"),
        "#c2995d",
        "#2b2d42",
        0.25,
        30,
    ),
]


def draw_topo_polygons(ax, polygons, xmin, ymin, xmax, ymax, scale):
  if polygons.empty:
    return

  polygons = polygons.copy()
  polygons["_area"] = polygons.geometry.area
  polygons["_ground_layer"] = None

  for name, filter_fn, fcol, ecol, lw in LANDCOVER_STYLES:
    mask = filter_fn(polygons)
    polygons.loc[mask, "_ground_layer"] = name

  style_map = {
      name: (fcol, ecol, lw) for name, _, fcol, ecol, lw in LANDCOVER_STYLES
  }

  ground = polygons[polygons["_ground_layer"].notna()].sort_values(
      by="_area", ascending=False
  )
  if not ground.empty:
    ground["_group"] = (
        ground["_ground_layer"] != ground["_ground_layer"].shift()
    ).cumsum()
    for _, grp in ground.groupby("_group", sort=False):
      layer_type = next(iter(grp["_ground_layer"]))
      fcol, ecol, lw = style_map[layer_type]
      ls_ground = (0, (4, 2)) if layer_type == "military" else "-"
      grp.plot(
          ax=ax,
          facecolor=fcol,
          edgecolor=ecol,
          linewidth=lw,
          linestyle=ls_ground,
          zorder=10,
      )

  for name, filter_fn, fcol, ecol, lw, zord in OVERLAY_STYLES:
    subset = polygons[filter_fn(polygons)].sort_values(
        by="_area", ascending=False
    )
    if not subset.empty:
      if name == "water":
        subset.plot(
            ax=ax,
            facecolor="none",
            edgecolor=ecol,
            linewidth=lw * 1.6,
            zorder=zord,
        )
        subset.plot(
            ax=ax,
            facecolor=fcol,
            edgecolor="none",
            zorder=zord + 0.01,
        )
      else:
        subset.plot(
            ax=ax, facecolor=fcol, edgecolor=ecol, linewidth=lw, zorder=zord
        )


  if "boundary" in polygons.columns:
    parks = polygons[polygons["boundary"] == "protected_area"]
    if not parks.empty:
      parks.plot(
          ax=ax,
          facecolor="#80ed99",
          edgecolor="none",
          alpha=0.16,
          zorder=12,
      )
      parks.plot(
          ax=ax,
          facecolor="none",
          edgecolor="#007f5f",
          linewidth=1.5,
          linestyle=(0, (6, 2, 1.5, 2)),
          zorder=56,
      )
