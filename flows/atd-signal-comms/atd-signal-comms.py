#!/usr/bin/env python

"""
Name: atd-signal-comms: Device Comm Status Logger
Description: Repo: https://github.com/cityofaustin/atd-signal-comms Wrapper ETL for the atd-signal-comms docker image 
    with commands that check the status of various IP devices and logs the results, then publishes to the open data portal.

Create Deployment:
$ prefect deployment build flows/atd-signal-comms/atd-signal-comms.py:main \
    --name "atd-signal-comms: Device Comm Status Logger" \
    --pool atd-data-03 \
    --cron "7 7 * * *" \
    -q default \
    -sb github/ch-signal-comms \
    -o "deployments/atd-signal-comms.yaml"\
    --skip-upload \
    --description "Repo: https://github.com/cityofaustin/atd-signal-comms Wrapper ETL for the atd-signal-comms docker image \ 
    with commands that check the status of various IP devices and logs the results, then publishes to the open data portal."
 
$ prefect deployment apply deployments/atd-signal-comms.yaml
"""

import os

import docker
import prefect
from datetime import datetime, timedelta

# Prefect
from prefect import flow, task, get_run_logger
from prefect.blocks.system import JSON


# Docker settings
docker_image = "atddocker/atd-signal-comms"


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
def pull_docker_image(docker_tag):
    client = docker.from_env()
    client.images.pull(docker_image, tag=docker_tag)
    return True


@task(
    name="run_comm_check",
    task_run_name="run_comm_check: {device}",
    retries=3,
    retry_delay_seconds=timedelta(minutes=10).seconds,
)
def run_comm_check(environment_variables, device, env, logger, docker_tag):
    command = f"python atd-signal-comms/run_comm_check.py {device} --env {env}"
    logger.info(command)

    response = (
        docker.from_env()
        .containers.run(
            image=f"{docker_image}:{docker_tag}",
            working_dir=None,
            command=command,
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
    name="socrata_pub",
    task_run_name="socrata_pub: {device}",
    retries=3,
    retry_delay_seconds=timedelta(minutes=10).seconds,
)
def socrata_pub(environment_variables, device, env, logger, docker_tag):
    start_date = environment_variables["PREV_EXEC"]
    command = f"python atd-signal-comms/socrata_pub.py {device} --start {start_date} --env {env}"
    logger.info(command)

    response = (
        docker.from_env()
        .containers.run(
            image=f"{docker_image}:{docker_tag}",
            working_dir=None,
            command=command,
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


@flow(name="atd-signal-comms: Device Comm Status Logger")
def main(devices, block, env, docker_tag):
    # Logger instance
    logger = get_run_logger()

    # Start: get env vars and pull the latest docker image
    environment_variables = get_env_vars(block)
    docker_res = pull_docker_image(docker_tag)

    # Log device comm status in S3
    for device in devices:
        res = run_comm_check(environment_variables, device, env, logger, docker_tag)
    if res:
        for device in devices:
            socrata_res = socrata_pub(
                environment_variables, device, env, logger, docker_tag
            )
    if socrata_res:
        update_exec_date(block)


if __name__ == "__main__":
    # List of devices to check IP status
    devices = ["signal_monitor", "digital_message_sign"]

    # Environment Variable Storage Block Name
    block = "atd-signal-comms"

    # Environment to run the docker container in
    env = "dev"

    # Docker image tag to use
    docker_tag = "latest"

    main(devices, block, env, docker_tag)
