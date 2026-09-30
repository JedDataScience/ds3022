import random 
import time
from prefect import flow, task, get_run_logger

## get_run_logger() is used to get the logger for the current flow run and can determine if the a log is dangerous or not. It is used to log messages in the flow and tasks.

@task(log_prints=True)
def print_and_sleep(value: int):
    delay = random.randint(5, 15)
    time.sleep(delay)
    print(f"Value: {value}, Delay: {delay}")
    time.sleep(5)
    return value

@task(log_prints=True)
def range_task(start: int = 1, end: int = 20):
    futures = print_and_sleep.map(range(start, end))
    results = futures.result()
    print(f"Completed {len(results)} subtasks")
    return results


@flow 
def fan_out_flow():
    range_task()



if __name__ == "__main__":
    fan_out_flow()