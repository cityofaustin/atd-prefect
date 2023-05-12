#!/usr/bin/env python

"""
Name: ATD Performance Dashboard: ROW Data Publishing
Description: Repo: https://github.com/cityofaustin/atd-executive-dashboard Downloads ROW data from AMANDA and Smartsheet and 
    publishes the weekly summary results in a Socrata Dataset.

Create Deployment:
$ prefect deployment build flows/atd-executive-dashboard/row_data_publishing.py:main \
    --name "ATD Performance Dashboard: ROW Data Publishing" \
    --pool atd-data-03 \
    --cron "5 13 * * *" \
    -q default \
    -sb github/ch-amanda-queries \
    -o "deployments/amanda_to_s3.yaml"
    --description Repo: https://github.com/cityofaustin/atd-executive-dashboard Downloads ROW data from AMANDA and Smartsheet and publishes the weekly summary results in a Socrata Dataset.
 
$ prefect deployment apply deployments/amanda_to_s3.yaml
"""

import os

import docker
import prefect
from datetime import datetime, timedelta

# Prefect
from prefect import flow, task, get_run_logger
from prefect.blocks.system import JSON


# Docker settings
docker_image = f"atddocker/atd-executive-dashboard"


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
    name="docker_commands",
    retries=1,
    retry_delay_seconds=timedelta(minutes=5).seconds,
    task_run_name="Docker Command: {command}",
)
def docker_commands(environment_variables, command, logger, docker_env):
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


@flow(name=f"ATD Performance Dashboard: ROW Data Publishing")
def main(commands, block, docker_tag):
    # Logger instance
    logger = get_run_logger()

    # Start: get env vars and pull the latest docker image
    environment_variables = get_env_vars(block)
    docker_res = pull_docker_image(docker_tag)

    # Run our commands
    if docker_res:
        for c in commands:
            commands_res = docker_commands(environment_variables, c, logger, docker_tag)
    if commands_res:
        update_exec_date(block)


if __name__ == "__main__":
    # List of commands to be sent to the docker image,
    # Note that the date filter arg is added last in determine_date_args task
    commands = [
        "AMANDA/amanda_to_s3.py --query applications_received",
        "AMANDA/amanda_to_s3.py --query active_permits",
        "AMANDA/amanda_to_s3.py --query issued_permits",
        "smartsheet/smartsheet_to_s3.py",
        "row_data_summary.py",
    ]

    # Environment Variable Storage Block Name
    block = "amanda-to-s3"

    docker_tag = "latest"

    main(commands, block, docker_tag)
