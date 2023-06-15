#!/usr/bin/env python

"""
Name: atd-bond-reporting: Bond Dashboard Scripts
Description: Repo: https://github.com/cityofaustin/atd-bond-reporting Wrapper ETL for the atd-bond-reporting docker image 
             with commands for moving the data from S3 to Socrata.

Create Deployment:
$ prefect deployment build flows/atd-bond-reporting/atd-bond-reporting.py:main \
    --name "Bond Reporting Data Scripts" \
    --pool atd-data-03 \
    --cron "0 15 * * *" \
    -q default \
    -sb github/atd-prefect-main-branch \
    -o "deployments/atd-bond-reporting.yaml"\
    --skip-upload \
    --description "Repo: https://github.com/cityofaustin/atd-bond-reporting Wrapper ETL for the atd-bond-reporting docker image with commands for moving the data from S3 to Socrata."
 
$ prefect deployment apply deployments/atd-bond-reporting.yaml
"""

import os

import docker
import prefect
from datetime import datetime, timedelta

# Prefect
from prefect import flow, task, get_run_logger
from prefect.blocks.system import JSON


# Docker settings
docker_image = "atddocker/atd-bond-reporting"


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
    retries=3,
    retry_delay_seconds=timedelta(minutes=2).seconds,
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


@flow(name=f"Bond Reporting Data Scripts")
def main(commands, block, docker_tag):
    # Logger instance
    logger = get_run_logger()

    # Start: get env vars and pull the latest docker image
    environment_variables = get_env_vars(block)
    docker_res = pull_docker_image(docker_tag)

    # Run our commands
    for c in commands:
        commands_res = docker_commands(environment_variables, c, logger, docker_tag)
    if commands_res:
        update_exec_date(block)


if __name__ == "__main__":
    # List of commands to be sent to the docker image,
    # Note that the date filter arg is added last in determine_date_args task
    commands = [
        'atd-bond-reporting/microstrategy_to_s3.py -r "2020 Bond Expenses Obligated"',
        'atd-bond-reporting/microstrategy_to_s3.py -r "All bonds Expenses Obligated"',
        'atd-bond-reporting/microstrategy_to_s3.py -r "FDU Expenses by Quarter"',
        'atd-bond-reporting/microstrategy_to_s3.py -r "2020 Division Group and Unit"',
        "atd-bond-reporting/bond_data.py",
        "atd-bond-reporting/bond_calculations.py",
        "atd-bond-reporting/quarterly_reporting.py",
    ]

    # Environment Variable Storage Block Name
    block = "atd-bond-reporting"

    # Docker tag
    docker_tag = "production"

    main(commands, block, docker_tag)
