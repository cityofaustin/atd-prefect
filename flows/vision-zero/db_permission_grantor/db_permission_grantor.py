#!/usr/bin/python3

import os
import json

import prefect
from prefect.backend import get_key_value
from prefect import Flow, task
from prefect.run_configs import UniversalRun
import psycopg2

from sshtunnel import SSHTunnelForwarder

kv_store = get_key_value("Vision Zero")
kv_dictionary = json.loads(kv_store)

DB_HOST = None
DB_USER = None
DB_PASS = None
DB_NAME = None
SCHEMAS_CDL = None

if False:
    DB_HOST = os.getenv("DB_HOST")
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_NAME = os.getenv("DB_NAME")
    SCHEMAS_CDL = os.getenv("DB_PERMISSION_SCHEMAS")
    DB_BASTION_HOST = os.getenv("DB_BASTION_HOST")
    DB_RDS_HOST = os.getenv("DB_RDS_HOST")
else:
    DB_HOST = kv_dictionary["DB_HOST"]
    DB_USER = kv_dictionary["DB_USER"]
    DB_PASS = kv_dictionary["DB_PASS"]
    DB_NAME = kv_dictionary["DB_NAME"]
    SCHEMAS_CDL = kv_dictionary["DB_PERMISSION_SCHEMAS"]
    DB_BASTION_HOST = kv_dictionary["DB_BASTION_HOST"]
    DB_RDS_HOST = kv_dictionary["DB_RDS_HOST"]

SCHEMAS = SCHEMAS_CDL.split(", ")

@task
def grant_permissions():
    
    ssh_tunnel = SSHTunnelForwarder(
        (DB_BASTION_HOST),
        ssh_username="vz-etl",
        ssh_private_key= '/root/.ssh/id_rsa', # will switch to ed25519 when we rebuild this for prefect 2
        remote_bind_address=(DB_RDS_HOST, 5432)
        )
    ssh_tunnel.start()   

    print("SSH Tunnel Established (local port: " + str(ssh_tunnel.local_bind_port) + ")")

    pg = psycopg2.connect(
        user=DB_USER,
        password=DB_PASS,
        host='localhost',
        port=ssh_tunnel.local_bind_port,
        sslmode="require",
        database=DB_NAME,)

    cursor = pg.cursor()

    logger = prefect.context.get("logger")

    for schema in SCHEMAS:

        sql = f'GRANT USAGE ON SCHEMA {schema} TO staff'
        logger.info(sql)
        cursor.execute(sql)

        sql = f'GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO staff'
        logger.info(sql)
        cursor.execute(sql)

        sql = f'GRANT SELECT ON ALL SEQUENCES IN SCHEMA {schema} TO staff'
        logger.info(sql)
        cursor.execute(sql)
    
    pg.commit()

with Flow(
    "Refresh DB Permissions for Read Replica",
    run_config=UniversalRun(labels=["vision-zero", "atd-data03"]),
) as flow:
    logger = prefect.context.get("logger")
    result = grant_permissions()

# flow.run()
flow.register(project_name="vision-zero")
