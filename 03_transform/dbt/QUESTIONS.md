# NYC Taxi Data — Exploration Questions

Ten dimensions/questions worth digging into with this dataset (2025
yellow taxi trips), using columns available in `stg_yellow_tripdata`
and `fct_trips`.

1. **Time-of-day demand curve.** How does trip volume rise and fall across
   the 24 hours of a typical day? Does it look like a single commute-driven
   peak, a bimodal AM/PM pattern, or something flatter and more
   leisure-driven?

2. **Day-of-week and weekday vs. weekend behavior.** Do trip counts, average
   distance, and average fare shift meaningfully between weekdays and
   weekends? Weekend trips might skew longer/later even if there are fewer
   of them.

3. **Seasonality across the year.** With all 12 months of 2025 available,
   does ridership trend up or down month over month? Are there visible dips
   around holidays or weather-driven slow months?

4. **Trip distance distribution and outliers.** What does the full
   distribution of `trip_distance_miles` look like, and where's a sensible
   cutoff before a trip stops looking like a real in-city ride? (There's
   already a `trip_distance_cutoffs.png` in `03_transform/` suggesting this
   was being explored manually.)

5. **Speed as a congestion proxy.** Does `avg_speed_mph` (from `fct_trips`)
   vary by hour of day or day of week in a way that tracks known NYC traffic
   patterns — slower during rush hours, faster overnight?

6. **Tipping behavior by payment type.** How does `tip_pct` differ between
   credit-card and cash trips (`payment_type_code`)? Cash tips are typically
   under-recorded in TLC data — does that show up clearly here?

7. **Fare efficiency — $/mile and $/minute.** How does `fare_amount` scale
   with `trip_distance_miles` and `trip_duration_minutes`? Are short trips
   proportionally more expensive per mile than long ones (reflecting the
   flag-drop/minimum-fare structure)?

8. **Popular pickup/dropoff corridors.** Which `pickup_location_id` /
   `dropoff_location_id` pairs see the most trips? Are there a handful of
   dominant routes (e.g., airport-to-Manhattan) that stand out from the
   long tail?

9. **Passenger count patterns.** Are the overwhelming majority of trips
   solo riders? Does `passenger_count` correlate with anything else — trip
   distance, time of day, or tipping behavior?

10. **Vendor comparison.** Do the two vendors (`vendor_id`) differ
    systematically in trip characteristics — average fare, distance,
    tip percentage, or reporting patterns (e.g., one vendor showing more
    null/zero values than the other)?
