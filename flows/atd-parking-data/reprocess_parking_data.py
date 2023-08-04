#!/usr/bin/env python

"""
Name: atd-parking-data: Reprocessing Parking Data
Description: Repo: https://github.com/cityofaustin/atd-parking-data Scripts that download
    and process parking data for finance reporting.

Create Deployment:
$ prefect deployment build flows/atd-parking-data/reprocess_parking_data.py:main \
    --name "atd-parking-data: Reprocessing Parking Data" \
    --pool atd-data-03 \
    -q default \
    -sb github/ch-parking-data-refresh \
    -o "deployments/reprocess_parking_data.yaml"\
    --skip-upload \
    --description "Repo: https://github.com/cityofaustin/atd-parking-data Scripts that download and process parking data for finance reporting."
 
$ prefect deployment apply deployments/reprocess_parking_data.yaml
"""

import os
import itertools

import docker
import prefect
from datetime import datetime, timedelta

# Prefect
from prefect import flow, task, get_run_logger
from prefect.blocks.system import JSON


# Docker settings
docker_image = "atddocker/atd-parking-data-meters"


@task(
    name="get_env_vars",
    retries=10,
    retry_delay_seconds=timedelta(seconds=15).seconds,
)
def get_env_vars(json_block):
    # Environment Variables stored in JSON block in Prefect
    return JSON.load(json_block).dict()["value"]


@task(
    name="pull_docker_image",
    retries=1,
    retry_delay_seconds=timedelta(minutes=5).seconds,
)
def pull_docker_image(docker_env):
    client = docker.from_env()
    client.images.pull(docker_image, tag=docker_env)
    return True


@task(
    name="docker_command",
    retries=3,
    retry_delay_seconds=timedelta(minutes=2).seconds,
    task_run_name="Docker Command: {command}",  # note this is not wrong, you don't use an f-string here.
)
def docker_command(docker_env, environment_variables, command, logger):
    response = (
        docker.from_env()
        .containers.run(
            image=f"{docker_image}:{docker_env}",
            working_dir=None,
            command=f"python {command}",
            environment=environment_variables,
            volumes=None,
            remove=True,
            detach=False,
            stdout=True,
        )
        .decode("utf-8")
    )
    logger.info(response)
    return response


@flow(name="atd-parking-data: Reprocessing Parking Data")
def main(start_date, block, s3_env, docker_env):
    # Logger instance
    logger = get_run_logger()

    # Start: get env vars and pull the latest docker image
    environment_variables = get_env_vars(block)

    command = f"txn_history.py --env {s3_env} --report payments --start {start_date}"
    command_res = docker_command(docker_env, environment_variables, command, logger)


if __name__ == "__main__":
    # Environment Variable Storage Block Name
    block = "atd-parking-data"

    # Which s3 folder to use
    s3_env = "prod"

    # Tag of docker image to use
    docker_env = "production"

    start_date = "2023-01-01"

    main(start_date, block, s3_env, docker_env)
