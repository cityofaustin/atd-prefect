#!/usr/bin/python3

import os
import json

import prefect
from prefect.backend import get_key_value
from prefect import Flow, task
from prefect.run_configs import UniversalRun
import psycopg2

kv_store = get_key_value("Vision Zero")
kv_dictionary = json.loads(kv_store)

DB_HOST = None
DB_USER = None
DB_PASS = None
DB_NAME = None
SCHEMAS_CDL = None
STAFF_CDL = None

if True:
    DB_HOST = os.getenv("DB_HOST")
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_NAME = os.getenv("DB_NAME")
    SCHEMAS_CDL = os.getenv("DB_PERMISSION_SCHEMAS")
    STAFF_CDL = os.getenv("DB_PERMISSION_STAFF")
else:
    DB_HOST = kv_dictionary["DB_HOST"]
    DB_USER = kv_dictionary["DB_USER"]
    DB_PASS = kv_dictionary["DB_PASS"]
    DB_NAME = kv_dictionary["DB_NAME"]
    SCHEMAS_CDL = kv_dictionary["DB_PERMISSION_SCHEMAS"]
    STAFF_CDL = kv_dictionary["DB_PERMISSION_STAFF"]

SCHEMAS = SCHEMAS_CDL.split(", ")
STAFF = STAFF_CDL.split(", ")

@task

def grant_permissions():
    pg = psycopg2.connect(
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port="5432",
        database=DB_NAME,)

    cursor = pg.cursor()

    logger = prefect.context.get("logger")

    for staffMember in STAFF:
        for schema in SCHEMAS:

            sql = f'GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO {staffMember}'
            logger.info(sql)
            cursor.execute(sql)
    
    pg.commit()

with Flow(
    "Refresh DB Permissions for Read Replica",
    run_config=UniversalRun(labels=["vision-zero", "atd-data03"]),
) as flow:
    logger = prefect.context.get("logger")
    result = grant_permissions()

flow.run()
# flow.register(project_name="vision-zero")
