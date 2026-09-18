"""Plot average rides per hour from the mart_hourly_demand dbt model.

Run `dbt run --select +mart_hourly_demand` first so the table exists in
nyc_taxi.duckdb, then:

    python plot_hourly_demand.py
"""

from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

DB_PATH = Path(__file__).parent / "../nyc_taxi.duckdb"
OUTPUT_PATH = Path(__file__).parent / "hourly_demand.png"


def kalman_smooth(observations, process_var=5000.0, measurement_var=50000.0):
    """Rauch-Tung-Striebel smoother over a local-level (random-walk) model.

    A forward Kalman filter pass followed by a backward smoothing pass —
    the standard way to get a smooth trend line through noisy sequential
    counts without a curve-fitting library.
    """
    n = len(observations)
    filtered_means = np.zeros(n)
    filtered_vars = np.zeros(n)
    predicted_vars = np.zeros(n)

    mean, var = observations[0], measurement_var
    for t in range(n):
        if t > 0:
            var += process_var  # predict step: random-walk state
        predicted_vars[t] = var

        # update step: blend prediction with the observation
        kalman_gain = var / (var + measurement_var)
        mean = mean + kalman_gain * (observations[t] - mean)
        var = (1 - kalman_gain) * var

        filtered_means[t] = mean
        filtered_vars[t] = var

    smoothed_means = filtered_means.copy()
    for t in range(n - 2, -1, -1):
        gain = filtered_vars[t] / predicted_vars[t + 1]
        smoothed_means[t] = filtered_means[t] + gain * (
            smoothed_means[t + 1] - filtered_means[t]
        )

    return smoothed_means


def main():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute(
        "select pickup_hour, trip_count from mart_hourly_demand order by pickup_hour"
    ).df()
    con.close()

    smoothed = kalman_smooth(df["trip_count"].to_numpy(dtype=float))

    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(data=df, x="pickup_hour", y="trip_count", color="steelblue", ax=ax)
    ax.plot(
        range(len(df)),
        smoothed,
        color="darkorange",
        linewidth=2.5,
        marker="o",
        markersize=4,
        label="Kalman-smoothed trend",
    )

    ax.set_title("NYC Yellow Taxi Rides by Hour of Day (2025)")
    ax.set_xlabel("Pickup Hour (0-23)")
    ax.set_ylabel("Trip Count")
    ax.legend()

    fig.tight_layout()
    fig.savefig(OUTPUT_PATH, dpi=150)
    print(f"Saved plot to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
