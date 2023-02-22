#!/usr/bin/env python

"""
Name: Knack Banner HR App integration
Description: Update knack HR app based on records in Banner and CTM
Schedule: "45 13 * * *"
"""

import prefect
import docker

# Prefect
from prefect import flow, task, get_run_logger
from prefect.blocks.notifications import SlackWebhook
from prefect.blocks.system import JSON

docker_image = f"atddocker/atd-knack-banner:production"


@task(name="get_environment_variables")
def get_env_vars():
    # Environment Variables stored in JSON block in Prefect
    return JSON.load("atd-knack-banner")


# Retrieve the provider's data
@task(
    name="update HR employees in knack",
    retries=2,
    retry_delay_seconds=300,
    task_run_name="atd-knack-banner/update-employees",
)
def knack_banner_update_employees(environment_variables):
    logger = get_run_logger()
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir="/app",
            command=f"./atd-knack-banner/update_employees.py",
            environment=environment_variables.value,
            volumes=None,
            remove=True,
            detach=False,
            stdout=True,
        )
        .decode("utf-8")
    )
    logger.info(response)
    return response


@flow(name=f"Knack HR Banner")
def knack_hr_banner_flow():
    logger = get_run_logger()
    environment_variables = get_env_vars()
    knack_banner_update_employees(environment_variables)


if __name__ == "__main__":
    knack_hr_banner_flow()
