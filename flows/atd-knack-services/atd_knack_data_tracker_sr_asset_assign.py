#!/usr/bin/env python

"""
Name: Knack Services: Data Tracker SR Assign Signals
Description: Repo: https://github.com/cityofaustin/atd-knack-services Wrapper ETL for the atd-knack-services docker image 
             with commands for a script that assigns signals to CSRs in data tracker.

Create Deployment:
$ prefect deployment build flows/atd-knack-services/atd_knack_data_tracker_sr_asset_assign.py:main \
    --name "Knack Services: Data Tracker SR Assign Signals" \
    --pool atd-data-03 \
    --cron "* * * * *" \
    -q default \
    -sb github/knack-services-wip \
    -o "deployments/atd_knack_data_tracker_sr_asset_assign.yaml"
    --description Repo: https://github.com/cityofaustin/atd-knack-services Wrapper ETL for the atd-knack-services docker image with commands for a script that assigns signals to CSRs in data tracker. \
    --skip-upload
    --tag atd-knack-services
 
$ prefect deployment apply deployments/atd_knack_data_tracker_sr_asset_assign.yaml
"""

import os

import docker
import prefect
from datetime import datetime, timedelta

# Prefect
from prefect import flow, task, get_run_logger
from prefect.blocks.system import JSON


# Docker settings
docker_env = "test"
docker_image = "atddocker/atd-knack-services"


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
def pull_docker_image():
    client = docker.from_env()
    client.images.pull(docker_image, tag=docker_env)
    return True


@task(
    name="docker_commands",
    retries=1,
    retry_delay_seconds=timedelta(minutes=5).seconds,
)
def docker_commands(environment_variables, commands, logger):
    # list ex: ["atd-knack-services/services/records_to_postgrest.py -a {app_name} -c {container} -d {date_filter}"]
    for c in commands:
        response = (
            docker.from_env()
            .containers.run(
                image=f"{docker_image}:{docker_env}",
                working_dir=None,
                command=f"python {c}",
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


@flow(name=f"Knack Services: Data Tracker SR Assign Signals")
def main(commands, block):
    # Logger instance
    logger = get_run_logger()

    # Start: get env vars and pull the latest docker image
    environment_variables = get_env_vars(block)
    docker_res = pull_docker_image()

    # Run our commands
    if docker_res:
        commands_res = docker_commands(environment_variables, commands, logger)
    if commands_res:
        update_exec_date(block)


if __name__ == "__main__":
    app_name = "data-tracker"  # Name of knack app
    container = "view_2362"  # Container
    asset = "signals"  # Name of assets to match

    # List of commands to be sent to the docker image
    commands = [
        f"atd-knack-services/services/sr_asset_assign.py -a {app_name} -c {container} -s {asset}",
    ]

    # Environment Variable Storage Block Name
    block = "atd-knack-services-data-tracker-location-updater-prod"

    main(commands, block)
