#!/usr/bin/env python

"""
Name: Moped Editor Test Instance Deployment
Description: Build and deploy the resources needed to test
    a feature branch of the Moped Editor application
Schedule: TBD
Labels: TBD
"""

from venv import create
import prefect
import sys, os
import subprocess

from dotenv import load_dotenv

load_dotenv()

# Prefect
from prefect import Flow, task

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Logger instance
logger = prefect.context.get("logger")

# Frontend:
# 1. When feature PR is opened, a deploy preview spins up and is linked in PR
# 2. Env vars are available to introspect PR # and context (CONTEXT = deploy-preview)
#    https://docs.netlify.com/configure-builds/environment-variables/?utm_campaign=devex-tzm&utm_source=blog&utm_medium=blog&utm_content=env-vars&_gl=1%2agvssna%2a_gcl_aw%2aR0NMLjE2NTQ1NDAxNzcuQ2p3S0NBand5X2FVQmhBQ0Vpd0EySUhIUUFud3NXc1ltbXJybGs5SnVfWTJlazlkUF9hVmM4WVZuTjR5Zk5QR0Y2U2ZOLTMycl93ekFCb0M2Y0lRQXZEX0J3RQ..&_ga=2.210432213.1131530997.1654540177-2032963523.1654540177&_gac=1.123937528.1654540177.CjwKCAjwy_aUBhACEiwA2IHHQAnwsWsYmmrrlk9Ju_Y2ek9dP_aVc8YVnN4yfNPGF6SfN-32r_wzABoC6cIQAvD_BwE#read-only-variables

# Considerations:
# 1. Auth (use staging user pool) needs a callback URL set in the user pool. How does this work
#    for the deploy previews? (I know that we can't use SSO)
#    - Just do whatever deploy previews do for auth

# Questions:
# 1. What S3 bucket does current moped-test use for file uploads?
#    - Extend directories in S3 bucket to keep files for each preview app

# Connect to database server and return psycopg2 connection and cursor
def connect_to_db_server():
    host = os.getenv("MOPED_TEST_HOSTNAME")
    user = os.getenv("MOPED_TEST_USER")
    password = os.getenv("MOPED_TEST_PASSWORD")

    pg = psycopg2.connect(host=host, user=user, password=password)
    # see https://stackoverflow.com/questions/34484066/create-a-postgres-database-using-python
    pg.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = pg.cursor()

    return (pg, cursor)


# Database and GraphQL engine tasks
@task
def create_database(database_name):
    logger.info(f"Creating database {database_name}".format(database_name))
    # Stretch goal: replicate staging data
    # Via Frank:
    # 1. Populate with seed data
    # 2. OR populate with staging data
    (pg, cursor) = connect_to_db_server()

    create_database_sql = f"CREATE DATABASE {database_name}".format(database_name)
    cursor.execute(create_database_sql)

    # Commit changes and close connections
    pg.commit()
    cursor.close()
    pg.close()

    host = os.getenv("MOPED_TEST_HOSTNAME")
    user = os.getenv("MOPED_TEST_USER")
    password = os.getenv("MOPED_TEST_PASSWORD")

    # Connect to the new DB so we can update it
    db_pg = psycopg2.connect(
        host=host, user=user, password=password, database=database_name
    )
    db_cursor = db_pg.cursor()

    # Add Postgis extension
    create_postgis_extension_sql = "CREATE EXTENSION postgis"

    # db_cursor.execute(disable_jit_sql)
    db_cursor.execute(create_postgis_extension_sql)

    # Commit changes and close connections
    db_pg.commit()
    db_cursor.close()
    db_pg.close()


# Need to set when database is removed
@task
def remove_database(database_name):
    logger.info(f"Removing database {database_name}".format(database_name))

    (pg, cursor) = connect_to_db_server()

    create_database_sql = f"DROP DATABASE IF EXISTS {database_name}".format(
        database_name
    )
    cursor.execute(create_database_sql)

    # Commit changes and close connections
    pg.commit()
    cursor.close()
    pg.close()


# pg_dump command
# pg_restore command
# Use Shell task, docker pg image and run psql
@task
def populate_database_with_production_data(database_name):
    logger.info(
        f"Populating {database_name} with production data".format(database_name)
    )


@task
def create_graphql_engine():
    # Deploy ECS cluster
    logger.info("creating ECS cluster")
    return True


@task
def remove_graphql_engine():
    # Remove ECS cluster
    logger.info("removing ECS cluster")
    return True


# Activity log (SQS & Lambda) tasks


@task
def create_activity_log_sqs():
    # Use boto3 to create SQS
    logger.info("creating activity log SQS")
    return True


@task
def create_activity_log_lambda():
    # Use boto3 to create activity log event lambda
    logger.info("creating activity log Lambda")
    return True


@task
def remove_activity_log_sqs():
    # Use boto3 to remove SQS
    logger.info("removing activity log SQS")
    return True


@task
def remove_activity_log_lambda():
    # Use boto3 to remove activity log event lambda
    logger.info("removing activity log Lambda")
    return True


# Moped API tasks


@task
def create_moped_api():
    # Deploy moped API using Zappa or the CloudFormation template that it generates
    logger.info("creating Moped API Lambda")
    return True


@task
def remove_moped_api():
    # Remove CloudFormation stack that create_moped_api deployed with boto3
    return True


# Next, we define the flow (equivalent to a DAG).
with Flow("test flow") as flow:
    # Calls tasks
    logger.info("Calling tasks")

    # Env var from GitHub action?
    database_name = os.getenv("DATABASE_NAME")
    create_database(database_name)
    # remove_database(database_name)


if __name__ == "__main__":
    flow.run()
