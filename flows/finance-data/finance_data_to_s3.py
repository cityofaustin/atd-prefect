#!/usr/bin/env python

"""
Name: ATD Finance Data Flow
Description: Gets Finance data from a database, places it in an S3 bucket, 
             then moves it along to Knack and socrata.

Build Deployment yaml file:
$ prefect deployment build flows/finance-data/finance_data_to_s3.py:finance_data --name "Finance Data Publishing" --pool atd-data-03 -q default -sb github/github-atd-prefect
Then, apply this deployment
$ prefect deployment apply main-deployment.yaml
"""

import os

import docker
import prefect
from datetime import datetime, timedelta

# Prefect
from prefect import flow, task, get_run_logger
from prefect.blocks.system import JSON


# Docker settings
docker_env = "production"
docker_image = f"atddocker/atd-finance-data:{docker_env}"


@task(
    name="get_env_vars",
    retries=10,
    retry_delay_seconds=timedelta(seconds=15).seconds,
)
def get_env_vars():
    # Environment Variables stored in JSON block in Prefect
    return JSON.load("atd-finance-data")


@task(
    name="pull_docker_image",
    retries=1,
    retry_delay_seconds=timedelta(minutes=5).seconds,
)
def pull_docker_image():
    client = docker.from_env()
    client.images.pull("atddocker/atd-finance-data", tag=docker_env)
    return True


@task(
    name="upload_to_s3",
    retries=1,
    retry_delay_seconds=timedelta(minutes=5).seconds,
)
def upload_to_s3(environment_variables, name):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python upload_to_s3.py {name}",
            environment=environment_variables,
            volumes=None,
            remove=True,
            detach=False,
            stdout=True,
        )
        .decode("utf-8")
    )
    return response


@task(
    name="upload_to_knack",
    retries=1,
    retry_delay_seconds=timedelta(minutes=5).seconds,
)
def upload_to_knack(environment_variables, name, app, task_orders_res):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python s3_to_knack.py {name} {app}",
            environment=environment_variables,
            volumes=None,
            remove=True,
            detach=False,
            stdout=True,
        )
        .decode("utf-8")
    )
    return response


@task(
    name="upload_to_socrata",
    retries=1,
    retry_delay_seconds=timedelta(minutes=5).seconds,
)
def upload_to_socrata(environment_variables):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command="python s3_to_socrata.py",
            environment=environment_variables,
            volumes=None,
            remove=True,
            detach=False,
            stdout=True,
        )
        .decode("utf-8")
    )

    return response


@flow(name=f"Finance Data Publishing")
def finance_data():
    # Logger instance
    logger = get_run_logger()

    # Start: get env vars and pull the latest docker image
    environment_variables = get_env_vars()
    docker_res = pull_docker_image()

    if docker_res:
        task_orders_res = upload_to_s3(
            environment_variables.value["data-tracker"], "task_orders"
        )
        logger.info(task_orders_res)

        finance_purchasing_res = upload_to_knack(
            environment_variables.value["finance-purchasing"],
            "task_orders",
            "finance-purchasing",
            task_orders_res,
        )
        logger.info(finance_purchasing_res)

        data_tracker_res = upload_to_knack(
            environment_variables.value["data-tracker"],
            "task_orders",
            "data-tracker",
            task_orders_res,
        )
        logger.info(data_tracker_res)

        units_res = upload_to_s3(environment_variables.value["data-tracker"], "units")
        logger.info(units_res)

        data_tracker_res = upload_to_knack(
            environment_variables.value["data-tracker"],
            "units",
            "data-tracker",
            units_res,
        )
        logger.info(data_tracker_res)

        objects_res = upload_to_s3(
            environment_variables.value["data-tracker"], "objects"
        )
        logger.info(objects_res)

        master_agreements_res = upload_to_s3(
            environment_variables.value["data-tracker"], "master_agreements"
        )
        logger.info(master_agreements_res)

        fdus_res = upload_to_s3(environment_variables.value["data-tracker"], "fdus")
        logger.info(fdus_res)

        if all([task_orders_res, units_res, fdus_res]):
            upload_to_socrata(environment_variables.value["data-tracker"])


if __name__ == "__main__":
    finance_data()
