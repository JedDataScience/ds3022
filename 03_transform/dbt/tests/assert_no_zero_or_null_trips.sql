-- Singular test: fails if any row returned here — i.e. any trip with
-- zero/null passengers, zero/null distance, or zero/null fare slipped
-- past staging.

select *
from {{ ref('fct_trips') }}
where
    passenger_count is null or passenger_count = 0
    or trip_distance_miles is null or trip_distance_miles = 0
    or fare_amount is null or fare_amount = 0
