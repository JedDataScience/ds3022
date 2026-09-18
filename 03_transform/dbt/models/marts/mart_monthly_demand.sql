-- Mart: trip demand by month — answers QUESTIONS.md #3 (does ridership
-- trend up or down across 2025, and are there visible seasonal dips?).
-- One row per month, grain is plot-ready as an x=pickup_month,
-- y=trip_count line/bar chart.

select
    date_trunc('month', pickup_date)      as pickup_month,
    count(*)                              as trip_count,
    round(avg(trip_distance_miles), 2)    as avg_distance_miles,
    round(avg(trip_duration_minutes), 2)  as avg_duration_minutes,
    round(avg(avg_speed_mph), 2)          as avg_speed_mph,
    round(avg(fare_amount), 2)            as avg_fare_amount,
    round(avg(tip_pct) * 100, 2)          as avg_tip_pct
from {{ ref('fct_trips') }}
group by pickup_month
order by pickup_month
