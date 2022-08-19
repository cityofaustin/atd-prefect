#!/usr/bin/env python

"""
Name: ATD Knack Services
Description: This set of tasks publishes data from ATD's various Knack 
 applications to other platforms including a Postgres database, Socrata, 
 and ArcGIS Online (AGOL). 
Schedule: "30 14,18 * * *"
Labels: atd-data02, knack
"""

import os

import docker
import prefect
from datetime import datetime, timedelta

# Prefect
from prefect import Flow, task, Parameter
from prefect.storage import GitHub
from prefect.run_configs import LocalRun
from prefect.engine.state import Failed
from prefect.schedules import Schedule
from prefect.schedules.clocks import CronClock
from prefect.backend import set_key_value, get_key_value
from prefect.triggers import all_successful
from prefect.tasks.docker import PullImage


from prefect.utilities.notifications import slack_notifier

CONFIG = [
    {
        "apps": "signs-markings",
        "containers": "view_3628",
        "layer": "markings_contractor_work_orders",
    },
]

# Report names and ids separated from dicts
app_names = [i["apps"] for i in CONFIG]
containers = [i["containers"] for i in CONFIG]
layer_names = [i["layer"] for i in CONFIG]


# Define current environment
current_environment = "test"

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed])

# Logger instance
logger = prefect.context.get("logger")

# Select the appropriate tag for the Docker Image
docker_env = "test"
docker_image = f"atddocker/atd-knack-services:{docker_env}"

environment_variables = get_key_value(key=f"atd_knack_services")

# Last execution date
# prev_execution_key = f"parking_data_reconciliation_prev_exec"
# prev_execution_date_success = get_key_value(prev_execution_key)

# Task to pull the latest Docker image
@task(
    name="pull_docker_image",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
    log_stdout=True,
)
def pull_docker_image():
    client = docker.from_env()
    client.images.pull("atddocker/atd-knack-services", all_tags=True)
    logger.info(docker_env)
    return


# Records to postgrest
@task(
    name="records_to_postgrest",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
    log_stdout=True,
)
def records_to_postgrest(app_name, container):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python atd-knack-services/services/records_to_postgrest.py -a {app_name} -c {container}",
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


# Records to AGOL
@task(
    name="records_to_agol",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
    log_stdout=True,
)
def records_to_agol(app_name, container):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python atd-knack-services/services/records_to_agol.py -a {app_name} -c {container}",
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


# Building AGOL segment geometries
@task(
    name="agol_build_markings_segment_geometries",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
    log_stdout=True,
)
def agol_build_markings_segment_geometries(layer):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python atd-knack-services/services/agol_build_markings_segment_geometries.py -l {layer}",
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


# @task(trigger=all_successful)
# def update_last_exec_time():
#    new_date = datetime.today().strftime("%Y-%m-%d")
#    set_key_value(key=prev_execution_key, value=new_date)


# Next, we define the flow (equivalent to a DAG).
# Notice we use the label "test" to match this flow to an agent.
with Flow(
    # Postfix the name of the flow with the environment it belongs to
    f"knack_services_{current_environment}",
    # Let's configure the agents to download the file from this repo
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/knack/knack_services.py",
        ref="atd-knack-services",  # The branch name
    ),
    run_config=LocalRun(labels=["atd-data02", "test"]),
    schedule=None,
) as flow:
    app_name = Parameter("apps", default=app_names, required=True)
    container = Parameter("containers", default=containers, required=True)
    layer = Parameter("layers", default=layer_names, required=True)

    # 1. Pull latest docker image
    pull_docker_image()

    # 2. Download Knack records and send them to Postgres(t)
    records_to_postgrest.map(app_name, container)

    # 3. Send data from Postgrest to AGOL
    records_to_agol.map(app_name, container)

    # 4. Build line geometries in AGOL
    agol_build_markings_segment_geometries.map(layer)


if __name__ == "__main__":
    flow.run(
        parameters={"apps": app_names, "containers": containers, "layers": layer_names}
    )
