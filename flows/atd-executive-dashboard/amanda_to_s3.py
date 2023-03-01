#!/usr/bin/env python

"""
Name: ATD Knack Services: Signs and Markings Contractor Work Orders
Description: Wrapper ETL for the atd-knack-services docker image 
             with defined commands for the contractor work orders flow

Create Deployment:
$ prefect deployment build flows/atd-executive-dashboard/amanda_to_s3.py:main --name "Executive Dashboard: AMANDA Queries to S3" --pool atd-data-03 --cron "5 13 * * *" -q default -sb github/ch-amanda-queries -o "deployments/amanda_to_s3.yaml"
 
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
docker_env = "latest"
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


@flow(name=f"Knack Services: Signs Markings Contractor Work Orders")
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
    # List of commands to be sent to the docker image,
    # Note that the date filter arg is added last in determine_date_args task
    commands = [
        "AMANDA/amanda_to_s3.py --query applications_received",
        "AMANDA/amanda_to_s3.py --query active_permits",
        "AMANDA/amanda_to_s3.py --query issued_permits",
    ]

    # Environment Variable Storage Block Name
    block = "amanda-to-s3"

    main(commands, block)
