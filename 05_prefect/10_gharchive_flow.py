import gzip
import json
from collections import Counter
import requests
from prefect import flow, task


URL = "https://data.gharchive.org/2025-01-01-{hour}.json.gz"


@task(retries=3, retry_delay_seconds=10)
def count_events_for_hour(hour: int) -> dict[str, int]:
    """Stream one hourly GH Archive file and return {event_type: count}."""
    counts = Counter()
    bad_lines = 0

    # stream=True downloads in chunks; timeout stops a dead connection from hanging forever
    with requests.get(URL.format(hour=hour), stream=True, timeout=60) as r:
        r.raise_for_status()  # 404/500 raises an error, which triggers Prefect's retries

        # r.raw is the raw byte stream; gzip.open decompresses it as it's read ("rt" = text mode)
        with gzip.open(r.raw, "rt", encoding="utf-8") as f:
            for line in f:
                try:
                    counts[json.loads(line)["type"]] += 1
                except (json.JSONDecodeError, KeyError):
                    bad_lines += 1  # skip a malformed line rather than failing the whole hour

    if bad_lines:
        print(f"hour {hour}: skipped {bad_lines} bad lines")
    print(f"hour {hour}: {counts.total():,} events")
    return dict(counts)


@task
def combine_counts(hourly_counts: list[dict[str, int]]) -> dict[str, int]:
    """Merge per-hour {event_type: count} dicts into one total, sorted descending."""
    totals = Counter()
    for i, hour_counts in enumerate(hourly_counts):
        try:
            if not isinstance(hour_counts, dict):
                raise TypeError(f"expected dict, got {type(hour_counts).__name__}")
            totals.update(hour_counts)  # adds counts rather than overwriting
        except (TypeError, ValueError) as e:
            # Skip the bad hour but keep the rest of the results
            print(f"skipping hour index {i}: {e}")

    # Fail loudly if no hour produced usable data
    if not totals:
        raise ValueError("no valid hourly counts to combine")

    # most_common() sorts by count, highest first; dict() keeps that order
    ordered = dict(totals.most_common())

    for event_type, count in ordered.items():
        print(f"{event_type:<30} {count:>10,}")
    print(f"{'TOTAL':<30} {totals.total():>10,}")

    return ordered


@flow(log_prints=True)
def gharchive_flow(hours: list[int] | None = None) -> dict[str, int]:
    """Count GH Archive event types across the given hours of 2025-01-01."""
    hours = hours if hours is not None else list(range(1, 4))  # avoid a mutable default argument

    # Fail fast on bad input instead of burning 3 retries on guaranteed 404s
    invalid = [h for h in hours if not 0 <= h <= 23]
    if invalid:
        raise ValueError(f"hours must be 0-23, got {invalid}")

    # .map() submits one task run per hour; they run concurrently
    futures = count_events_for_hour.map(hours)

    # Collect results one at a time so one failed hour doesn't sink the whole flow
    hourly = []
    for hour, future in zip(hours, futures):
        try:
            hourly.append(future.result())
        except Exception as e:
            print(f"hour {hour} failed after retries: {e}")

    return combine_counts(hourly)  # prints the totals and raises if every hour failed


if __name__ == "__main__":
    gharchive_flow()
