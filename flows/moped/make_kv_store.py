#!/usr/bin/python3

import os
import json
from prefect.backend import set_key_value

kv_store = {
    "AWS_DEFAULT_REGION": os.getenv("AWS_DEFAULT_REGION"),
    "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
    "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
}

json = json.dumps(kv_store)

key_value_uuid = set_key_value(key="Moped", value=json)
