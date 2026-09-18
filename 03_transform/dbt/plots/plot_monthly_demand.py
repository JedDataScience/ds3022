"""Plot ridership by month from the mart_monthly_demand dbt model.

Run `dbt run --select +mart_monthly_demand` first so the table exists in
nyc_taxi.duckdb, then:

    python plot_monthly_demand.py
"""

from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import seaborn as sns

DB_PATH = Path(__file__).parent / "../nyc_taxi.duckdb"
OUTPUT_PATH = Path(__file__).parent / "monthly_demand.png"


def main():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    # A handful of trips carry corrupted pickup_at timestamps from other
    # years (TLC meter/GPS glitches, same class of issue as the
    # trip_distance_miles outliers) - scope to 2025 for this plot.
    df = con.execute(
        """
        select pickup_month, trip_count
        from mart_monthly_demand
        where pickup_month >= '2025-01-01' and pickup_month < '2026-01-01'
        order by pickup_month
        """
    ).df()
    con.close()

    df["month_label"] = df["pickup_month"].dt.strftime("%b")

    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(data=df, x="month_label", y="trip_count", color="steelblue", ax=ax)
    ax.plot(
        range(len(df)),
        df["trip_count"],
        color="darkorange",
        linewidth=2.5,
        marker="o",
        markersize=5,
        label="Month-over-month trend",
    )

    ax.set_title("NYC Yellow Taxi Rides by Month (2025)")
    ax.set_xlabel("Month")
    ax.set_ylabel("Trip Count")
    ax.legend()

    fig.tight_layout()
    fig.savefig(OUTPUT_PATH, dpi=150)
    print(f"Saved plot to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
