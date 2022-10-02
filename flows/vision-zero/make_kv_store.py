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
    "PRODUCTION_GRAPHQL_ENDPOINT": os.getenv("PRODUCTION_GRAPHQL_ENDPOINT"),
    "PRODUCTION_GRAPHQL_ENDPOINT_ACCESS_KEY": os.getenv("PRODUCTION_GRAPHQL_ENDPOINT_ACCESS_KEY"),
    "OCR_CR3_SOURCE_BUCKET": os.getenv("OCR_CR3_SOURCE_BUCKET"),
    "OCR_CR3_SOURCE_PATH": os.getenv("OCR_CR3_SOURCE_PATH"),
    "OCR_DIAGRAM_TARGET_BUCKET": os.getenv("OCR_DIAGRAM_TARGET_BUCKET"),
    "OCR_DIAGRAM_TARGET_PATH": os.getenv("OCR_DIAGRAM_TARGET_PATH"),
    "OCR_BATCH_SIZE": os.getenv("OCR_BATCH_SIZE"),
    "OCR_SINGLE_CRASH": os.getenv("OCR_SINGLE_CRASH"),

    "AFD_DB_USERNAME": os.getenv("AFD_DB_USERNAME"),
    "AFD_DB_PASSWORD": os.getenv("AFD_DB_PASSWORD"),
    "AFD_DB_HOSTNAME": os.getenv("AFD_DB_HOSTNAME"),
    "AFD_DB_PORT": os.getenv("AFD_DB_PORT"),
    "AFD_DB_DATABASE": os.getenv("AFD_DB_DATABASE"),
    "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
    "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "AFD_S3_SOURCE_BUCKET": os.getenv("AFD_S3_SOURCE_BUCKET"),
    "AFD_S3_ARCHIVE_BUCKET": os.getenv("AFD_S3_ARCHIVE_BUCKET"),
    "AFD_S3_SOURCE_PREFIX": os.getenv("AFD_S3_SOURCE_PREFIX"),
    "AFD_S3_ARCHIVE_PREFIX": os.getenv("AFD_S3_ARCHIVE_PREFIX"),
    "EMS_S3_SOURCE_BUCKET": os.getenv("EMS_S3_SOURCE_BUCKET"),
    "EMS_S3_ARCHIVE_BUCKET": os.getenv("EMS_S3_ARCHIVE_BUCKET"),
    "EMS_S3_SOURCE_PREFIX": os.getenv("EMS_S3_SOURCE_PREFIX"),
    "EMS_S3_ARCHIVE_PREFIX": os.getenv("EMS_S3_ARCHIVE_PREFIX"),

    "DB_HOST": os.getenv("DB_HOST"),
    "DB_USER": os.getenv("DB_USER"),
    "DB_PASS": os.getenv("DB_PASS"),
    "DB_NAME": os.getenv("DB_NAME"),
    "DB_IMPORT_SCHEMA": os.getenv("DB_IMPORT_SCHEMA"),
    "GRAPHQL_ENDPOINT": os.getenv("GRAPHQL_ENDPOINT"),
    "GRAPHQL_ENDPOINT_KEY": os.getenv("GRAPHQL_ENDPOINT_KEY"),
}

json = json.dumps(kv_store)

key_value_uuid = set_key_value(key="Vision Zero Development", value=json)
