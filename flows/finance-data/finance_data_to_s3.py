#!/usr/bin/env python

"""
Name: ATD Finance Data Flow
Description: Gets Finance data from a database, places it in an S3 bucket, 
             then moves it along to Knack and socrata.
Schedule: "30 12 * * *"
Labels: atd-data02, moped
"""

import os

import docker
import prefect
from datetime import datetime, timedelta

# Prefect
from prefect import Flow, task, case
from prefect.storage import GitHub
from prefect.run_configs import UniversalRun
from prefect.engine.state import Failed
from prefect.schedules import Schedule
from prefect.schedules.clocks import CronClock
from prefect.backend import set_key_value, get_key_value
from prefect.triggers import all_successful
from prefect.tasks.control_flow import merge

from prefect.utilities.notifications import slack_notifier

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed])

# Logger instance
logger = prefect.context.get("logger")

# Docker settings
docker_env = "production"
docker_image = f"atddocker/atd-finance-data:{docker_env}"


@task(
    name="get_env_vars",
    max_retries=10,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(seconds=15),
    state_handlers=[handler],
)
def get_env_vars():
    # Environment Variables from KV Store in Prefect
    return get_key_value(key=f"atd_finance_data")


@task(
    name="pull_docker_image",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
)
def pull_docker_image():
    client = docker.from_env()
    client.images.pull("atddocker/atd-finance-data", all_tags=True)
    logger.info(docker_image)
    return True


@task(
    name="upload_to_s3",
    task_run_name="upload_to_s3: {name}",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
)
def upload_to_s3(environment_variables, name):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python upload_to_s3.py {name}",
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
    name="upload_to_knack",
    task_run_name="upload_to_knack: {name}, {app}",
    max_retries=1,
    timeout=timedelta(minutes=180),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
)
def upload_to_knack(environment_variables, name, app, task_orders_res):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python s3_to_knack.py {name} {app}",
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
    name="upload_to_socrata",
    task_run_name="upload_to_socrata",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
)
def upload_to_socrata(environment_variables, socrata_fl):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command="python s3_to_socrata.py",
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


with Flow(
    # Postfix the name of the flow with the environment it belongs to
    f"Finance Data Publishing",
    # Let's configure the agents to download the file from this repo
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/finance-data/finance_data_to_s3.py",
        ref="main",  # The branch name
        access_token_secret="GITHUB_ACCESS_TOKEN",
    ),
    # Run config will always need the current_environment
    # plus whatever labels you need to attach to this flow
    run_config=UniversalRun(labels=["test", "atd-data02"]),
    schedule=Schedule(clocks=[CronClock("13 7 * * *")]),
) as flow:
    # Start: get env vars and pull the latest docker image
    environment_variables = get_env_vars()
    docker_res = pull_docker_image()

    with case(docker_res, True):
        task_orders_res = upload_to_s3(
            environment_variables["data-tracker"], "task_orders"
        )
        upload_to_knack(
            environment_variables["finance-purchasing"],
            "task_orders",
            "finance-purchasing",
            task_orders_res,
        )
        upload_to_knack(
            environment_variables["data-tracker"],
            "task_orders",
            "data-tracker",
            task_orders_res,
        )
        units_res = upload_to_s3(environment_variables["data-tracker"], "units")
        upload_to_knack(
            environment_variables["data-tracker"], "units", "data-tracker", units_res
        )
        objects_res = upload_to_s3(environment_variables["data-tracker"], "objects")
        master_agreements_res = upload_to_s3(
            environment_variables["data-tracker"], "master_agreements"
        )
        fdus_res = upload_to_s3(environment_variables["data-tracker"], "fdus")

        socrata_start = merge(task_orders_res, units_res, fdus_res)
        upload_to_socrata(environment_variables["data-tracker"], socrata_start)


if __name__ == "__main__":
    flow.run()
