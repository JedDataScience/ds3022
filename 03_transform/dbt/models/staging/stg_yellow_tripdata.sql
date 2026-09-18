-- Staging: light cleanup and standardization of raw parquet columns.
-- Materialized as a table — pulls all 12 remote parquet files once per
-- rebuild and caches the result locally, so downstream models and ad
-- hoc queries don't re-fetch from the network every time.

with source as (
    select * from {{ source('raw', 'yellow_tripdata') }}
),

renamed as (
    select
        cast(vendorid as integer)              as vendor_id,
        cast(tpep_pickup_datetime as timestamp) as pickup_at,
        cast(tpep_dropoff_datetime as timestamp) as dropoff_at,
        cast(passenger_count as integer)        as passenger_count,
        cast(trip_distance as double)           as trip_distance_miles,
        cast(pulocationid as integer)           as pickup_location_id,
        cast(dolocationid as integer)           as dropoff_location_id,
        cast(payment_type as integer)           as payment_type_code,
        cast(fare_amount as double)             as fare_amount,
        cast(tip_amount as double)              as tip_amount,
        cast(tolls_amount as double)            as tolls_amount,
        cast(total_amount as double)            as total_amount
    from source
)

select *
from renamed
where
    -- filter out the well-known TLC data-quality junk before it
    -- propagates downstream
    pickup_at is not null
    and dropoff_at is not null
    and dropoff_at > pickup_at
    and trip_distance_miles > 0
    and fare_amount > 0
    and passenger_count > 0
    -- drop trips whose average speed is null, non-positive, or over 60 mph:
    -- above ~60 the trip counts stop tapering and are mostly GPS/meter glitches
    and trip_distance_miles
        / nullif(date_diff('second', pickup_at, dropoff_at) / 3600.0, 0) > 0
    and trip_distance_miles
        / nullif(date_diff('second', pickup_at, dropoff_at) / 3600.0, 0) <= 60
