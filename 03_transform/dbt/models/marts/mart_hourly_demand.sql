-- Mart: trip demand by hour of day — answers QUESTIONS.md #1
-- (does the day have a single commute peak, a bimodal AM/PM pattern,
-- or something flatter?). One row per hour (0-23), grain is plot-ready
-- as an x=pickup_hour, y=trip_count line/bar chart.

select
    hour(pickup_at)                       as pickup_hour,
    count(*)                              as trip_count,
    round(avg(trip_distance_miles), 2)    as avg_distance_miles,
    round(avg(trip_duration_minutes), 2)  as avg_duration_minutes,
    round(avg(avg_speed_mph), 2)          as avg_speed_mph,
    round(avg(fare_amount), 2)            as avg_fare_amount,
    round(avg(tip_pct) * 100, 2)          as avg_tip_pct
from {{ ref('fct_trips') }}
group by pickup_hour
order by pickup_hour
