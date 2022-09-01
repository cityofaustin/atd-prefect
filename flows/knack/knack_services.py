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
from prefect import Flow, task, Parameter, unmapped, case
from prefect.storage import GitHub
from prefect.run_configs import LocalRun
from prefect.engine.state import Failed
from prefect.schedules import Schedule
from prefect.schedules.clocks import CronClock
from prefect.backend import set_key_value, get_key_value
from prefect.triggers import all_successful
from prefect.tasks.docker import PullImage


from prefect.utilities.notifications import slack_notifier


# Default parameters is for Signs/Markings Contractor Work Orders
FLOW_NAME_UNIQUE = "Markings Contractor Work Orders"
APP_NAME = "signs-markings"
CONTAINER = "view_3628"
LAYER_NAME = "markings_contractor_work_orders"
# Parameter that will overwrite all data (ignores date)
REPLACE_DATA = False
APP_NAME_DEST = ""
SOCRATA_FLAG = True
AGOL_FLAG = True

# Define current environment
current_environment = "prod"

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed])

# Logger instance
logger = prefect.context.get("logger")

# Select the appropriate tag for the Docker Image
docker_env = "production"
docker_image = f"atddocker/atd-knack-services:{docker_env}"

# Set flow runtime name from:
# https://github.com/PrefectHQ/prefect/discussions/3881
def set_run_name(flow, old_state, new_state):
    if new_state.is_running():
        client = prefect.Client()
        name = f"{prefect.context.parameters['App Name']}:{prefect.context.parameters['Knack Container']}-{prefect.context.date}"  # use flow-name-day-of-week as the flow run name, for example
        client.set_flow_run_name(prefect.context.flow_run_id, name)


# Based on inputs, determine if some conditional tasks should run
@task(name="determine_task_runs", nout=2)
def determine_task_runs(layer, app_name_dest):
    return bool(layer), bool(app_name_dest)


# Task to pull the latest Docker image
@task(
    name="pull_docker_image",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
    log_stdout=True,
)
def pull_docker_image():
    client = docker.from_env()
    response = client.images.pull("atddocker/atd-knack-services", all_tags=True)
    logger.info(docker_env)
    return response


# Get the envrioment variables for the given app
@task(
    name="get_env_vars",
    task_run_name="get_env_vars:{app}",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
    log_stdout=True,
)
def get_env_vars(app):
    environment_variables = get_key_value(key=f"{app}-atd_knack_services")
    return environment_variables


# Get the last date (string) the flow was succesful
@task(
    name="get_last_exec_time",
    task_run_name="get_last_exec_time (app: {app}, container: {container})",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
    log_stdout=True,
)
def get_last_exec_time(app, container, replace_data):
    # Completely replace data on 15th day of every month,
    # to catch records potentially missed by incremental refreshes
    if datetime.today().day == 15:
        return "1970-01-01"

    # parameter option to replace all data
    if replace_data:
        return "1970-01-01"

    # Get dict of previous executions
    prev_execs = get_key_value("atd_knack_services_prev_exec")

    # Key is unique based on the container and app
    key = f"{app}:{container}-prev-exec"

    # Return the date for this container/app if it exists
    if key in prev_execs:
        return prev_execs[key]
    else:
        # Return this if it doesn't exist yet
        return "1970-01-01"


# Records to postgrest
@task(
    name="records_to_postgrest",
    task_run_name="records_to_postgrest (app: {app_name}, contianer: {container}, date_filter:{date_filter})",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
    log_stdout=True,
)
def records_to_postgrest(app_name, container, date_filter, environment_variables):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python atd-knack-services/services/records_to_postgrest.py -a {app_name} -c {container} -d {date_filter}",
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
    task_run_name="records_to_agol (app: {app_name}, container: {container}, date_filter: {date_filter})",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
    log_stdout=True,
)
def records_to_agol(app_name, container, date_filter, environment_variables):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python atd-knack-services/services/records_to_agol.py -a {app_name} -c {container} -d {date_filter}",
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


# Records to Socrata
@task(
    name="records_to_socrata",
    task_run_name="records_to_socrata (app: {app_name}, container: {container}, date_filter: {date_filter})",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
    log_stdout=True,
)
def records_to_socrata(app_name, container, date_filter, environment_variables):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python atd-knack-services/services/records_to_socrata.py -a {app_name} -c {container} -d {date_filter}",
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
    task_run_name="agol_build_markings_segment_geometries (layer: {layer}, date_filter: {date_filter})",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
    log_stdout=True,
)
def agol_build_markings_segment_geometries(layer, date_filter, environment_variables):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python atd-knack-services/services/agol_build_markings_segment_geometries.py -l {layer} -d {date_filter}",
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


# Send Records to a destination knack app
@task(
    name="records_to_knack",
    task_run_name="records_to_knack (app_name_src: {app_name_src}, container_src: {container_src}, app_name_dest: {app_name_dest})",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
    log_stdout=True,
)
def records_to_knack(
    app_name_src, container_src, date_filter, app_name_dest, environment_variables
):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python atd-knack-services/services/records_to_knack.py -a {app_name_src} -c {container_src} -d {date_filter} -dest {app_name_dest}",
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


# Update the date stored in the key value in Prefect
# if the upstream tasks were successful
@task(trigger=all_successful)
def update_last_exec_time(app, container):
    # Get today's date as a string
    new_date = datetime.today().strftime("%Y-%m-%d")

    # Get dict of previous executions
    prev_execs = get_key_value("atd_knack_services_prev_exec")

    # Key is unique based on the container and app
    key = f"{app}:{container}-prev-exec"

    # Set that key to the new date
    prev_execs[key] = new_date
    set_key_value(key="atd_knack_services_prev_exec", value=prev_execs)


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
    run_config=LocalRun(labels=["atd-data02", "production"]),
    schedule=None,
    state_handlers=[set_run_name],
) as flow:
    # Parameter tasks
    app_name = Parameter("App Name", default=APP_NAME, required=True)
    container = Parameter("Knack Container", default=CONTAINER, required=True)
    layer = Parameter(
        "AGOL Build Segment Geometry Layer", default=LAYER_NAME, required=False
    )
    replace_data = Parameter("Replace all Data", default=REPLACE_DATA, required=True)
    app_name_dest = Parameter(
        "Records to Knack: App Name Destination", default=APP_NAME_DEST, required=False
    )
    soda_flag = Parameter("Send data to Socrata", default=True, required=True)
    agol_flag = Parameter("Send data to AGOL", default=True, required=True)

    # Based on provided parameters, skip or run some conditional tasks
    build_geom, to_knack = determine_task_runs(layer, app_name_dest)

    # Get the last time the flow ran for this app/container combo
    date_filter = get_last_exec_time(app_name, container, replace_data)

    environment_variables = get_env_vars(app_name)

    # 1. Pull latest docker image
    docker_pull = pull_docker_image()
    # 2. Download Knack records and send them to Postgres(t)
    postgrest_res = records_to_postgrest(
        app_name,
        container,
        date_filter,
        environment_variables,
        upstream_tasks=[docker_pull],
    )
    # 3. Send data from Postgrest to AGOL (optional)
    with case(agol_flag, True):
        agol_res = records_to_agol(
            app_name,
            container,
            date_filter,
            environment_variables,
            upstream_tasks=[docker_pull, postgrest_res],
        )

    # 4. Send data from Postgrest to Socrata (optional)
    with case(soda_flag, True):
        socrata_res = records_to_socrata(
            app_name,
            container,
            date_filter,
            environment_variables,
            upstream_tasks=[docker_pull, postgrest_res],
        )
    # 5. Build line geometries in AGOL (optional)
    with case(build_geom, True):
        agol_build_res = agol_build_markings_segment_geometries(
            layer,
            date_filter,
            environment_variables,
            upstream_tasks=[docker_pull, agol_res, build_geom],
        )
    # 6. Send data to another knack app (optional)
    with case(to_knack, True):
        knack_res = records_to_knack(
            app_name,
            container,
            date_filter,
            app_name_dest,
            environment_variables,
            upstream_tasks=[docker_pull, postgrest_res, to_knack],
        )

    # 6. (if successful) update exec date
    update_last_exec_time(app_name, container)

if __name__ == "__main__":
    flow.run(
        parameters={
            "App Name": APP_NAME,
            "Knack Container": CONTAINER,
            "AGOL Build Segment Geometry Layer": LAYER_NAME,
            "Replace all Data": REPLACE_DATA,
            "Records to Knack: App Name Destination": APP_NAME_DEST,
            "Send data to Socrata": SOCRATA_FLAG,
            "Send data to AGOL": AGOL_FLAG,
        }
    )
