# nyc_taxi_dbt

A minimal dbt project transforming NYC yellow taxi trip data, using
DuckDB as the adapter so it reads parquet directly over HTTPS — no
warehouse, download, or load step needed.

This project is being built up gradually across three classes. Right
now it contains staging (Class 1) plus tests and the `fct_trips` fact
model (Class 2 scope); the rest lives in `future/` and gets folded in
as we go.

## Layout

```
nyc_taxi_dbt/
├── dbt_project.yml
├── profiles.yml.example        # copy to ~/.dbt/profiles.yml
├── models/
│   ├── staging/
│   │   ├── sources.yml               # points at the raw parquet (local or remote)
│   │   ├── stg_yellow_tripdata.sql   # cast/clean raw columns
│   │   └── schema.yml                # column tests on the staging model
│   └── marts/
│       ├── fct_trips.sql             # derived duration/speed/tip metrics per trip
│       └── schema.yml
├── tests/
│   ├── assert_no_zero_or_null_trips.sql       # business-rule test on staging
│   └── assert_no_unrealistic_trip_speeds.sql  # business-rule test on fct_trips
└── future/                     # not yet wired into models/ — added in later classes
    └── marts/
        ├── mart_daily_summary.sql
        └── schema.yml
```

## Setup

1. Install: `pip install dbt-duckdb`
2. Copy `profiles.yml.example` to `~/.dbt/profiles.yml`.
3. From the `nyc_taxi_dbt/` directory:

```bash
dbt debug        # confirm the connection
dbt run          # build stg_yellow_tripdata and fct_trips
dbt test         # run column tests + the singular tests in tests/
```

4. Query the result:

```bash
duckdb nyc_taxi.duckdb -c "select * from fct_trips limit 10;"
```

No local data file to download — `sources.yml` points `external_location`
at TLC's public HTTPS parquet host, and DuckDB's `httpfs`/`parquet`
extensions stream it on demand. That same `external_location` key can
just as easily point at a local file path or an `s3://` URL — see the
comments in `sources.yml`.

## Why `{{ }}`? (Jinja + `ref()`)

The `.sql` files in `models/` aren't plain SQL — they're SQL *templates*
written in [Jinja](https://jinja.palletsprojects.com/), the same
templating language Flask/Django use for HTML. dbt compiles each
template into real SQL before running it.

The construct you'll see everywhere is `{{ ref('model_name') }}`, e.g.
in `fct_trips.sql`:

```sql
with trips as (
    select * from {{ ref('stg_yellow_tripdata') }}
)
```

`ref()` is a function call, not a table name — dbt resolves it at
compile time to the actual table/view in whatever database and schema
the current target points at. Two things fall out of that:

- **No hardcoded table names.** The same model compiles correctly
  whether it's running against your local `dev` target or a
  teammate's, without editing SQL.
- **Automatic lineage.** Because every `ref()` is a real, parseable
  function call, dbt can statically scan the whole `models/` directory
  and build the dependency graph from it — that's how it knows
  `fct_trips` must run after `stg_yellow_tripdata`. `sources.yml`'s
  `{{ source('raw', 'yellow_tripdata') }}` does the same thing for raw
  tables (see `stg_yellow_tripdata.sql`).

Want to see what a model actually compiles to? Run `dbt compile` and
open the matching file under `target/compiled/nyc_taxi_dbt/models/` —
`{{ ref(...) }}` will have become a literal table reference. That
side-by-side (template vs. compiled SQL) is the fastest way to get an
intuition for what Jinja is doing.

This project only uses `ref()`/`source()` — the two constructs that
cover most day-to-day dbt work. Jinja's other features (`{% if %}`,
`{% for %}`, custom macros, `{{ var(...) }}`) are worth learning once a
model actually needs them — e.g. looping over columns, or an
incremental model's `{% if is_incremental() %}` block — rather than as
syntax to memorize up front.

## View vs. table (and why `dbt run` re-reads everything)

- **`view`**: dbt stores your `SELECT` as a database view. Nothing is
  copied locally — every query against it re-runs the SQL and, for
  `stg_yellow_tripdata`, re-fetches the remote parquet over HTTPS each
  time.
- **`table`**: dbt materializes the result into DuckDB on disk
  (`CREATE OR REPLACE TABLE ... AS SELECT`). The remote parquet is read
  once at build time; everything downstream reads the local table.

**`dbt run` does not diff or check for existing data — it always
rebuilds.** Every run re-executes each model's `SELECT` from scratch,
so a `table` model still re-fetches all remote parquet files on every
`dbt run`, same as a `view` would. Materializing as `table` only saves
the network round-trip *between* runs (downstream models read local
disk instead of the network); it doesn't make a single `dbt run` any
smarter.

If re-reading the full remote source on every run is too slow/costly:

- **Scope your runs** once staging is built, e.g.
  `dbt run --select fct_trips+` or `dbt run --exclude stg_yellow_tripdata`,
  so you only rebuild the models that actually changed.
- **Use `incremental` materialization** for models where you can
  express "only the new rows" in SQL (via `{% if is_incremental() %}`,
  filtering on a date or ID column) — the first run does a full load,
  later runs only add rows matching that filter. This doesn't avoid
  reading the remote file if the filter can't be pushed down to
  CloudFront/S3, but it avoids re-writing rows that are already local.

For this project's static TLC parquet source, the simplest habit is:
build `stg_yellow_tripdata` once, then scope subsequent runs to
`marts` so the remote fetch isn't repeated unnecessarily.

## Class-by-class build-up

- **Class 1:** `stg_yellow_tripdata` only — a `source()` reading raw
  parquet, cast/renamed columns, a `where` filter dropping bad rows.
  Materialized as a `view`.
- **Class 2 (current):** column tests on staging (`not_null` on
  `pickup_at`, `trip_distance_miles`) plus a singular test,
  `assert_no_zero_or_null_trips.sql`. Adds `fct_trips`
  (`models/marts/fct_trips.sql`), wired via `{{ ref() }}` to the
  staging model — introduces model lineage, derived columns
  (duration/speed/tip%), and `table` materialization. A second
  singular test, `assert_no_unrealistic_trip_speeds.sql`, checks a
  *derived* column against a business rule (no NYC taxi can plausibly
  average >100mph) — something a generic `not_null`/`unique` test
  can't express.
- **Class 3:** add `mart_daily_summary` (`future/marts/mart_daily_summary.sql`)
  for the daily-rollup aggregation layer, and its `schema.yml` tests
  (`unique` + `not_null` on the `pickup_date` grain).

## Model chain (end state, after Class 3)

`stg_yellow_tripdata` (view, cleans/casts raw parquet) →
`fct_trips` (table, adds duration/speed/tip_pct, drops bad durations) →
`mart_daily_summary` (table, daily aggregates for reporting)
