# 01 - The happy path. No error handling at all.
# Break it: misspell USER, or turn off Wi-Fi, and read the traceback.

import httpx
import json
import logging

logging.basicConfig(
    filename="04_apis/01_plain.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

USER = "schaconxyz"
URL = "https://api.github.com/users/{user}/events/public"

try:
    response = httpx.get(URL.format(user=USER))
    response.raise_for_status()  # Raises an error for bad responses (4xx or 5xx)   
    data = response.json()

    for item in data: 
        print(item["repo"]["name"], " - ", item["type"])

    logging.info(f"Retrieved {len(data)} events for user {USER}")

except httpx.HTTPError as e:
    #print(e)
    logging.error(f"Error fetching events for user {USER}: {e}")
