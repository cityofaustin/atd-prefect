#!/usr/bin/env python

"""
Name: atd-trail-counter-data: Trail Counter Data Publishing
Description: Repo: https://github.com/cityofaustin/atd-trail-counter-data wrapper for ETL that
    scrapes trail counter data from the public eco-counter website and publishes it in Socrata.

Create Deployment:
$ prefect deployment build flows/atd-trail-counter-data/ped_data_pub.py:main \
    --name "atd-trail-counter-data: Trail Counter Data Publishing" \
    --pool atd-data-03 \
    --cron "00 8 * * *" \
    -q default \
    -sb github/ch-ped-counters \
    -o "deployments/ped_data_pub.yaml"\
    --skip-upload \
    --description "Repo: https://github.com/cityofaustin/atd-trail-counter-data wrapper for ETL that \
    scrapes trail counter data from the public eco-counter website and publishes it in Socrata."
 
$ prefect deployment apply deployments/ped_data_pub.yaml
"""

import os

import docker
import prefect
from datetime import datetime, timedelta

# Prefect
from prefect import flow, task, get_run_logger
from prefect.blocks.system import JSON


# Docker settings
docker_image = "atddocker/atd-trail-counters"


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


@task
def get_start_date(prev_execution_date_success):
    """Creates a start date 7 days before the date of the last successful run of the flow

    Args:
        prev_execution_date_success (string): Date of the last successful run of the flow

    Returns:
        list: The start date (string) which is 7 days before the last run.
        Defaults to 2014-01-01 if none were previously successful.
    """
    if prev_execution_date_success:
        # parse CLI arg date
        start_date = datetime.strptime(prev_execution_date_success, "%Y-%m-%d")
        start_date = start_date - timedelta(days=7)

        return start_date.strftime("%Y-%m-%d")
    else:
        return "2014-01-01"


@task(
    name="trail_counter_data_publish",
    retries=3,
    retry_delay_seconds=timedelta(minutes=2).seconds,
)
def trail_counter_data_publish(docker_env, environment_variables, start_date, logger):
    response = (
        docker.from_env()
        .containers.run(
            image=f"{docker_image}:{docker_env}",
            working_dir=None,
            command=f"python counter_data.py --start {start_date}",
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
    retry_delay_seconds=15,
)
def update_exec_date(json_block):
    # Update our JSON block with the updated date of last flow execution
    block = JSON.load(json_block)
    block.value["PREV_EXEC"] = datetime.today().strftime("%Y-%m-%d")
    block.save(name=json_block, overwrite=True)


@flow(name="atd-trail-counter-data: Trail Counter Data Publishing")
def main(block, docker_env):
    # Logger instance
    logger = get_run_logger()

    # Start: get env vars and pull the latest docker image
    environment_variables = get_env_vars(block)
    docker_res = pull_docker_image(docker_env)

    # Get previous exec date
    start_date = get_start_date(environment_variables["PREV_EXEC"])

    # Run our commands
    if docker_res:
        commands_res = trail_counter_data_publish(
            docker_env, environment_variables, start_date, logger
        )
    if commands_res:
        update_exec_date(block)


if __name__ == "__main__":
    # Environment Variable Storage Block Name
    block = "ped-data-pub"

    # Tag of docker image to use
    docker_env = "latest"

    main(block, docker_env)
