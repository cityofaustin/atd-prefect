#!/usr/bin/python3

import os
import json
from prefect.backend import set_key_value

RAW_AIRFLOW_CONFIG_JSON = os.getenv("RAW_AIRFLOW_CONFIG")

kv_store = {
    "SFTP_ENDPOINT": os.getenv("SFTP_ENDPOINT"),
    "ZIP_PASSWORD": os.getenv("ZIP_PASSWORD"),
    "VZ_ETL_LOCATION": os.getenv("VZ_ETL_LOCATION"),
    "RAW_AIRFLOW_CONFIG": RAW_AIRFLOW_CONFIG_JSON,
    "AWS_DEFAULT_REGION": os.getenv("AWS_DEFAULT_REGION"),
    "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
    "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "AWS_CSV_ARCHIVE_BUCKET_NAME": os.getenv("AWS_CSV_ARCHIVE_BUCKET_NAME"),
    "AWS_CSV_ARCHIVE_PATH_PRODUCTION": os.getenv("AWS_CSV_ARCHIVE_PATH_PRODUCTION"),
    "AWS_CSV_ARCHIVE_PATH_STAGING": os.getenv("AWS_CSV_ARCHIVE_PATH_STAGING"),
}

json = json.dumps(kv_store)

key_value_uuid = set_key_value(key="Vision Zero", value=json)
