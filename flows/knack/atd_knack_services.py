#!/usr/bin/env python

"""
Name: ATD Knack Services: Signs and Markings Contractor Work Orders
Description: Wrapper ETL for the atd-knack-services docker image 
             with defined commands for the contractor work orders flow

Create Deployment:
$ prefect deployment build flows/knack/atd_knack_services.py:main --name "Knack Services: SM Contractor Work Orders" -q ch-test-queue -sb github/knack-services-wip

Apply Deployment:
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
docker_image = f"atddocker/atd-knack-services:{docker_tag}"

# Environment Variable Storage Block Name
json_block = "atd-knack-services-sm-contractor-work-orders"


@task(
    name="get_env_vars",
    retries=10,
    retry_delay_seconds=timedelta(seconds=15).seconds,
)
def get_env_vars():
    # Environment Variables stored in JSON block in Prefect
    return JSON.load(json_block)


@task(
    name="pull_docker_image",
    retries=1,
    retry_delay_seconds=timedelta(minutes=5).seconds,
)
def pull_docker_image():
    client = docker.from_env()
    client.images.pull("atddocker/atd-finance-data", tag=docker_env)
    return True


# Determine what date to run the knack scripts
@task(
    name="determine_date_args",
    retries=1,
    retry_delay_seconds=timedelta(minutes=5).seconds,
)
def determine_date_args(environment_variables, commands):
    # Completely replace data on 15th day of every month,
    # to catch records potentially missed by incremental refreshes
    output = []
    if datetime.today().day == 15: 
        for c in commands:
            output.append(f"{c} -d 1970-01-01")
        return output

    prev_exec = environment_variables.value("PREV_EXEC")
    for c in commands:
        output.append(f"{c} -d {prev_exec}")
    return output

@task(
    name="docker_commands",
    retries=1,
    retry_delay_seconds=timedelta(minutes=5).seconds,
)
def docker_commands(environment_variables, commands):
    # list ex: ["atd-knack-services/services/records_to_postgrest.py -a {app_name} -c {container} -d {date_filter}"]
    output = []
    for c in commands:
        response = (
            docker.from_env()
            .containers.run(
                image=docker_image,
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
        output.append(response)
    return output

@flow(name=f"Knack Services: Signs Markings Contractor Work Orders")
def main(commands):
    # Logger instance
    logger = get_run_logger()

    # Start: get env vars and pull the latest docker image
    environment_variables = get_env_vars()
    docker_res = pull_docker_image()

    # Append date argument to our commands list 
    commands = determine_date_args(environment_variables, commands)

    # Run our commands
    if docker_res:
        commands_res = docker_commands(
            environment_variables, commands
        )
        logger.info(commands_res)


if __name__ == "__main__":
    app_name = "signs-markings" # Name of knack app
    container = "view_3628" # Container of contractor work orders
    layer_name = "markings_contractor_work_orders" # AGOL layer name for building segment geometries

    # List of commands to be sent to the docker image, 
    # Note that the date filter arg is added last in determine_date_args task 
    cmds = [
        f"atd-knack-services/services/records_to_postgrest.py -a {app_name} -c {container}",
        f"atd-knack-services/services/records_to_agol.py -a {app_name} -c {container}",
        f"atd-knack-services/services/records_to_socrata.py -a {app_name} -c {container}",
        f"atd-knack-services/services/agol_build_markings_segment_geometries.py -l {layer_name}",
        ]
    
    main(cmds)