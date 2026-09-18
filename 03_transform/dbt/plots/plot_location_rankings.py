"""Map the top 10 and bottom 10 taxi zones from mart_location_rankings.

Run `dbt build --select +mart_location_rankings` first so the view exists
in nyc_taxi.duckdb, then:

    python plot_location_rankings.py

The zone boundaries come from TLC's taxi_zones shapefile, downloaded once
into plots/taxi_zones/ and read with DuckDB's spatial extension - no
geopandas needed. Coordinates are NY State Plane (feet), which draws
correctly as-is with an equal aspect ratio.
"""

import io
import json
import urllib.request
import zipfile
from pathlib import Path

import duckdb
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Polygon

HERE = Path(__file__).parent
DB_PATH = HERE / "../nyc_taxi.duckdb"
OUTPUT_PATH = HERE / "location_rankings.png"
ZONES_DIR = HERE / "taxi_zones"
ZONES_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"

TOP_COLOR = "#2a78d6"
BOTTOM_COLOR = "#eb6834"
OTHER_COLOR = "#e4e3de"
INK = "#2b2b29"
MUTED = "#6b6a64"


def ensure_shapefile():
    shp = next(ZONES_DIR.rglob("taxi_zones.shp"), None)
    if shp is None:
        print(f"Downloading taxi zone shapefile to {ZONES_DIR}")
        with urllib.request.urlopen(ZONES_URL) as resp:
            zipfile.ZipFile(io.BytesIO(resp.read())).extractall(ZONES_DIR)
        shp = next(ZONES_DIR.rglob("taxi_zones.shp"))
    return shp


def load_data(shp):
    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.install_extension("spatial")
    con.load_extension("spatial")
    ranks = con.execute("select * from mart_location_rankings").df()
    zones = con.execute(
        f"""
        select
            LocationID                          as location_id,
            ST_AsGeoJSON(geom)                  as geojson,
            ST_X(ST_PointOnSurface(geom))       as label_x,
            ST_Y(ST_PointOnSurface(geom))       as label_y
        from ST_Read('{shp}')
        """
    ).df()
    con.close()
    return ranks, zones


def polygons(geojson):
    """Yield each outer ring of a Polygon/MultiPolygon as a list of (x, y)."""
    geom = json.loads(geojson)
    parts = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    for part in parts:
        yield part[0]


def draw_zones(ax, zones, groups, label_ids):
    for zone in zones.itertuples():
        group = groups.get(zone.location_id, (None, None))[0]
        color = {"top": TOP_COLOR, "bottom": BOTTOM_COLOR}.get(group, OTHER_COLOR)
        for ring in polygons(zone.geojson):
            ax.add_patch(Polygon(ring, facecolor=color, edgecolor="white", linewidth=0.4))
        if zone.location_id in label_ids:
            ax.text(
                zone.label_x, zone.label_y, str(groups[zone.location_id][1]),
                fontsize=8, fontweight="bold", color=INK, ha="center", va="center",
                path_effects=[pe.withStroke(linewidth=2.5, foreground="white")],
            )


def draw_panel(ax, zones, ranks, location_type):
    subset = ranks[ranks["location_type"] == location_type]
    groups = {
        row.location_id: (row.rank_group, row.location_rank)
        for row in subset.itertuples()
    }

    # The busiest Manhattan zones are too small and packed to label on the
    # full map, so they get their own zoomed inset in the empty top-left.
    crowded = set(
        subset[(subset["rank_group"] == "top") & (subset["borough"] == "Manhattan")]["location_id"]
    )
    draw_zones(ax, zones, groups, label_ids=set(groups) - crowded)
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(f"{location_type.title()}s", fontsize=14, color=INK, loc="left")

    if crowded:
        coords = [
            xy
            for zone in zones[zones["location_id"].isin(crowded)].itertuples()
            for ring in polygons(zone.geojson)
            for xy in ring
        ]
        xs, ys = zip(*coords)
        pad = 3000  # feet
        inset = ax.inset_axes([0.0, 0.52, 0.36, 0.46])
        draw_zones(inset, zones, groups, label_ids=crowded)
        inset.set_xlim(min(xs) - pad, max(xs) + pad)
        inset.set_ylim(min(ys) - pad, max(ys) + pad)
        inset.set_aspect("equal")
        inset.set_xticks([])
        inset.set_yticks([])
        inset.set_title("Manhattan detail", fontsize=9, color=MUTED, loc="left")
        ax.indicate_inset_zoom(inset, edgecolor=MUTED, linewidth=0.8)

    for i, (group, label) in enumerate([("top", "Busiest 10"), ("bottom", "Quietest 10")]):
        rows = subset[subset["rank_group"] == group].sort_values("location_rank")
        lines = [label] + [
            f"{r.location_rank:>2}. {r.zone[:30].rstrip()} ({r.trip_count:,})" for r in rows.itertuples()
        ]
        ax.text(
            0.5 * i, -0.02, "\n".join(lines), transform=ax.transAxes,
            fontsize=8.5, color=INK, va="top", ha="left", family="monospace",
        )


def main():
    shp = ensure_shapefile()
    ranks, zones = load_data(shp)

    fig, axes = plt.subplots(1, 2, figsize=(16, 10))
    for ax, location_type in zip(axes, ["pickup", "dropoff"]):
        draw_panel(ax, zones, ranks, location_type)

    fig.legend(
        handles=[
            Patch(facecolor=TOP_COLOR, label="Top 10 (most trips)"),
            Patch(facecolor=BOTTOM_COLOR, label="Bottom 10 (fewest trips)"),
            Patch(facecolor=OTHER_COLOR, label="Other zones"),
        ],
        loc="upper right", frameon=False, fontsize=10, labelcolor=INK,
    )
    fig.suptitle("NYC Yellow Taxi: Busiest and Quietest Zones (2025)", fontsize=16, color=INK, x=0.02, ha="left")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.24, wspace=0.05)
    fig.savefig(OUTPUT_PATH, dpi=150, facecolor="white")
    print(f"Saved map to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
