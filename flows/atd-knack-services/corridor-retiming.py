#!/usr/bin/env python

"""
Name: ATD Knack Services: Corridor Retiming
Description: Wrapper ETL for the atd-knack-services docker image 
             with defined commands for the corridor retiming view in Data Tracker app
Create Deployment:
$ prefect deployment build flows/atd-knack-services/corridor-retiming.py:main \
--name "Knack Services: SM Contractor Work Orders" --pool atd-data-03 \
--cron "45 11 * * *" -q default -sb github/atd-prefect-main-branch \
-o "deployments/knack-services-corridor-retiming.yaml"
 
$ prefect deployment apply deployments/atd_knack_services_sm_contractors.yaml
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
docker_image = f"atddocker/atd-knack-services:{docker_env}"

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
    client.images.pull(docker_image)
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

    prev_exec = environment_variables["PREV_EXEC"]
    for c in commands:
        output.append(f"{c} -d {prev_exec}")
    return output


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
        logger.info(response)
    return response


@task(
    name="update_exec_date",
    retries=10,
    retry_delay_seconds=timedelta(seconds=15).seconds,
)
def update_exec_date(json_block):
    # Update our JSON block with the updated date of last flow execution
    block = JSON.load(json_block)
    block.value["PREV_EXEC"] = datetime.today().strftime("%Y-%m-%d")
    block.save(name=json_block, overwrite=True)


@flow(name=f"Knack Services: Data Tracker Corridor Retiming")
def main(commands, env_block_name):
    # Logger instance
    logger = get_run_logger()

    # Start: get env vars and pull the latest docker image
    environment_variables = get_env_vars(env_block_name)
    docker_res = pull_docker_image()

    # Append date argument to our commands list
    commands = determine_date_args(environment_variables, commands)

    # Run our commands
    if docker_res:
        commands_res = docker_commands(environment_variables, commands, logger)
    if commands_res:
        update_exec_date(env_block_name)


if __name__ == "__main__":
    app_name = "data_tracker"  # Name of knack app
    container = "view_3814"  # Container of contractor work orders

    # List of commands to be sent to the docker image,
    # Note that the date filter arg is added last in determine_date_args task
    commands = [
        f"atd-knack-services/services/records_to_postgrest.py -a {app_name} -c {container}",
        f"atd-knack-services/services/records_to_socrata.py -a {app_name} -c {container}",
    ]

    # Environment Variable Storage Block Name
    # todo: add this block and var name
    env_block_name = ""

    main(commands, env_block_name)
