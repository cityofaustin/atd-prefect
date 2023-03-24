#!/usr/bin/env python

"""
Name: atd-parking-data: Parking Data Processsing
Description: Repo: https://github.com/cityofaustin/atd-parking-data Scripts that download
    and process parking data for finance reporting.

Create Deployment:
$ prefect deployment build flows/atd-parking-data/parking_data_processing.py:main \
    --name "atd-parking-data: Parking Data Processsing" \
    --pool atd-data-03 \
    --cron "35 8 * * *" \
    -q default \
    -sb github/ch-parking-data-prefect2 \
    -o "deployments/parking_data_processing.yaml"\
    --skip-upload \
    --description "Repo: https://github.com/cityofaustin/atd-parking-data Scripts that download and process parking data for finance reporting."
 
$ prefect deployment apply deployments/parking_data_processing.yaml
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
def pull_docker_image():
    client = docker.from_env()
    client.images.pull(docker_image, tag=docker_env)
    return True


@task
def get_start_date(prev_execution_date_success):
    """Creates a start date 7 days before the date of the last successful run of the flow

    Args:
        prev_execution_date_success (string): Date of the last successful run of the flow

    Returns:
        list: The start date (string) which is 7 days before the last run.
        Defaults to 2021-12-25 if none were previously successful.
    """
    if prev_execution_date_success:
        # parse CLI arg date
        start_date = datetime.strptime(prev_execution_date_success, "%Y-%m-%d")
        start_date = start_date - timedelta(days=7)

        return start_date.strftime("%Y-%m-%d")
    else:
        return "2021-12-25"


@task
def decide_prev_month(prev_execution_date_success):
    """
    Determines if the current month or the current plus previous month S3
        folders are needed. If it is within a week of the previous month,
        also upsert that months data.
    Parameters
    ----------
    prev_execution_date_success : String
        Last date the flow was successful.

    Returns
    -------
    Prev_month : Bool
        Argument if the previous month should be run.

    """
    if prev_execution_date_success:
        last_date = datetime.strptime(prev_execution_date_success, "%Y-%m-%d")
        # If in the first 8 days of the month of last few days of the month re-run
        # the previous month's data to make sure it is complete.
        if last_date.day < 8 or last_date.day > 26:
            return True
        else:
            return False
    return True


@task
def add_command_arguments(commands, s3_env, start_date):
    # Adds additonal command arguments based on provided arguments
    # and the previous exec date.
    output_commands = []
    for c in commands:
        if "txn_history.py" in c:
            c = f"{c} --env {s3_env}"
            c = f"{c} --start {start_date}"

        if "passport_txns.py" in c:
            c = f"{c} --env {s3_env}"
            c = f"{c} --start {start_date}"

        if "fiserv_DB.py" in c:
            c = f"{c} --lastmonth {prev_month}"

        if "payments_s3.py" in c:
            c = f"{c} --lastmonth {prev_month}"

        if "passport_DB.py" in c:
            c = f"{c} --lastmonth {prev_month}"

        if "smartfolio_s3.py" in c:
            c = f"{c} --lastmonth {prev_month}"

        output_commands.append(c)

    return output_commands


@task(
    name="docker_commands",
    retries=3,
    retry_delay_seconds=timedelta(minutes=2).seconds,
)
def docker_commands(environment_variables, commands, logger):
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


@flow(name="atd-parking-data: Parking Data Processsing")
def main(commands, block, s3_env):
    # Logger instance
    logger = get_run_logger()

    # Start: get env vars and pull the latest docker image
    environment_variables = get_env_vars(block)
    docker_res = pull_docker_image()

    start_date = get_start_date(environment_variables["PREV_EXEC"])
    prev_month = decide_prev_month(environment_variables["PREV_EXEC"])
    commands = add_command_arguments(commands, s3_env, start_date, prev_month)

    # Run our commands
    if docker_res:
        commands_res = docker_commands(environment_variables, commands, logger)
    if commands_res:
        update_exec_date(block)


if __name__ == "__main__":
    # List of commands to be sent to the docker image,
    # Note that the date filter arg is added last in determine_date_args task
    commands = [
        "txn_history.py -v --report transactions",
        "txn_history.py -v --report payments",
        "txn_history.py -v --report payments --user pard",
        "passport_txns.py -v",
        "fiserv_email_pub.py",
        "fiserv_DB.py",
        "payments_s3.py",
        "payments_s3.py --user pard",
        "passport_DB.py",
        "smartfolio_s3.py",
        "match_field_processing.py",
        "parking_socrata.py --dataset payments",
        "parking_socrata.py --dataset fiserv",
        "parking_socrata.py --dataset transactions",
    ]

    # Environment Variable Storage Block Name
    block = "atd-parking-data"

    # Which s3 folder to use
    s3_env = "prod"

    main(commands, block)
