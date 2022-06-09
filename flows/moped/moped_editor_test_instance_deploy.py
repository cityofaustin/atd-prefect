#!/usr/bin/env python

"""
Name: Moped Editor Test Instance Deployment
Description: Build and deploy the resources needed to test
    a feature branch of the Moped Editor application
Schedule: TBD
Labels: TBD
"""

import prefect

# Prefect
from prefect import Flow, task

# Logger instance
logger = prefect.context.get("logger")

# Questions
# 1. What S3 bucket does current moped-test use for file uploads?
# 2.

# Database tasks
@task
def create_database():
    # Use psycopg2 to connect to RDS
    # Need to think about how to prevent staging or prod DBs from being touched
    # Create ephemeral DB with name tied to PR # so it is easy to identify later
    # Run migrations
    # Stretch goal: replicate prod data
    logger.info("creating database")
    return True


@task
def remove_database():
    # Use psycopg2 to connect to RDS
    # Remove ephemeral DB
    # When PR is closed? When inactive for certain amount of time?
    logger.info("removing database")
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
    logger.info("creating Moped API Lam")
    return True


@task
def remove_moped_api():
    # Remove CloudFormation stack that create_moped_api deployed
    return True


# Next, we define the flow (equivalent to a DAG).
with Flow as flow:
    # Calls tasks
    logger.info("Calling tasks")


if __name__ == "__main__":
    flow.run()
