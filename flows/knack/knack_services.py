#!/usr/bin/env python

"""
Name: Parking Data Reconciliation Flows
Description: Parse Fiserv emails then upsert the CSVs to a postgres DB.
    Grab the payment data retrived from flowbird and upsert that to a postgres DB.
    Then, compare them before uploading the data to Socrata.
Schedule: "30 5 * * *"
Labels: atd-data02, parking
"""

import os

import docker
import prefect
from datetime import datetime, timedelta

# Prefect
from prefect import Flow, task
from prefect.storage import GitHub
from prefect.run_configs import LocalRun
from prefect.engine.state import Failed
from prefect.schedules import Schedule
from prefect.schedules.clocks import CronClock
from prefect.backend import set_key_value, get_key_value
from prefect.triggers import all_successful
from prefect.tasks.docker import PullImage


from prefect.utilities.notifications import slack_notifier

# Define current environment
current_environment = "test"

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed])

# Logger instance
logger = prefect.context.get("logger")

# Select the appropriate tag for the Docker Image
docker_env = "test"
docker_image = f"atddocker/atd-knack-services:{docker_env}"

environment_variables = get_key_value(key=f"atd_parking_data_meters")

# Last execution date
# prev_execution_key = f"parking_data_reconciliation_prev_exec"
# prev_execution_date_success = get_key_value(prev_execution_key)

# Task to pull the latest Docker image
# @task(
#    name="pull_docker_image",
#    max_retries=1,
#    timeout=timedelta(minutes=60),
#    retry_delay=timedelta(minutes=5),
#    state_handlers=[handler],
#    log_stdout=True
# )
# def pull_docker_image():
#    client = docker.from_env()
#    client.images.pull("atddocker/atd-parking-data-meters", all_tags=True)
#    logger.info(docker_env)
#    return


# Records to postgrest
@task(
    name="records_to_postgrest",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
    log_stdout=True,
)
def records_to_postgrest():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command="python app/services/records_to_postgrest.py -a signs-markings -c view_3628",
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
    # Run config will always need the current_environment
    # plus whatever labels you need to attach to this flow
    run_config=LocalRun(labels=["local", "charliesmacbook"]),
    schedule=None,
) as flow:
    flow.chain(
        records_to_postgrest,
    )


if __name__ == "__main__":
    flow.run()
