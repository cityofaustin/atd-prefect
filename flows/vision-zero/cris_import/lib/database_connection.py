import os

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import psycopg2.extras

if False:
    kv_store = get_key_value("Vision Zero Development")
    kv_dictionary = json.loads(kv_store)

    DB_HOST = kv_dictionary["DB_HOST"]
    DB_USER = kv_dictionary["DB_USER"]
    DB_PASS = kv_dictionary["DB_PASS"]
    DB_NAME = kv_dictionary["DB_NAME"]
    DB_IMPORT_SCHEMA = kv_dictionary["DB_IMPORT_SCHEMA"]
    DB_SSL_REQUIREMENT = kv_dictionary["DB_SSL_REQUIREMENT"]
else:
    DB_HOST = os.getenv("DB_HOST")
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_NAME = os.getenv("DB_NAME")
    DB_IMPORT_SCHEMA = os.getenv("DB_IMPORT_SCHEMA")
    DB_SSL_REQUIREMENT = os.getenv("DB_SSL_REQUIREMENT")


def get_pg_connection():
    """
    Returns a connection to the Postgres database
    """
    return psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME,
        sslmode=DB_SSL_REQUIREMENT,
        sslrootcert="/root/rds-combined-ca-bundle.pem",
    )