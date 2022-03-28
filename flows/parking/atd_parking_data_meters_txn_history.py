#!/usr/bin/env python

"""
Name: Fetch Flowbird meter transactions and load to S3
Description: Fetch Flowbird meter transactions and load to S3
Schedule: "35 3 * * *"
Labels: atd-data02, parking
"""

import os

import docker
import prefect
from datetime import datetime, timedelta

# Prefect
from prefect import Flow, task
from prefect.storage import GitHub
from prefect.run_configs import UniversalRun
from prefect.engine.state import Failed
from prefect.schedules import Schedule
from prefect.schedules.clocks import CronClock
from prefect.backend import set_key_value, get_key_value
from prefect.triggers import all_successful
from prefect.tasks.docker import PullImage

from prefect.utilities.notifications import slack_notifier

# First, we must always define the current environment, and default to staging:
current_environment = os.getenv("PREFECT_CURRENT_ENVIRONMENT", "staging")
current_environment = "test"
# Set up slack fail handler
# handler = slack_notifier(only_states=[Failed])

# Logger instance
logger = prefect.context.get("logger")

# Notice how test_kv is an object that contains our data as a dictionary:
env = "prod"  # if current_environment == "production" else "staging"

docker_env = "latest"
docker_image = f"atddocker/atd-parking-data-meters:{docker_env}"

image = PullImage(
    docker_server_url="unix:///var/run/docker.sock",
    repository="atddocker/atd-parking-data-meters",
    tag=docker_env,
)

# docker_image = f"atddocker/atd-parking-data-meters:{current_environment}"
environment_variables = get_key_value(key=f"atd_parking_data_meters")

# Last execution date
prev_execution_key = f"atd_parking_data_meters_prev_exec_production"
prev_execution_date_success = get_key_value(prev_execution_key)


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


start_date = get_start_date(prev_execution_date_success)
start_date = "2022-03-20"


@task(
    name="pull_docker_image",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
)
def pull_docker_image():
    client = docker.from_env()
    client.images.pull("atddocker/atd-parking-data-meters", all_tags=True)

    return


# Retrieve the provider's data
@task(
    name="parking_transaction_history_to_s3",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
)
def parking_transaction_history_to_s3():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python txn_history.py -v --report transactions --env {env} --start {start_date}",
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


# Sync the data with the database
@task(
    name="parking_payment_history_to_s3",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
    trigger=all_successful,
)
def parking_payment_history_to_s3():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python txn_history.py -v --report payments --env {env} --start {start_date}",
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


# Get pool pass data
@task(
    name="pard_payment_history_to_s3",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
    trigger=all_successful,
)
def pard_payment_history_to_s3():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python txn_history.py -v --report payments --env {env} --user pard --start {start_date}",
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


@task(trigger=all_successful)
def update_last_exec_time():
    new_date = datetime.today().strftime("%Y-%m-%d")
    set_key_value(key=prev_execution_key, value=new_date)


# Next, we define the flow (equivalent to a DAG).
# Notice we use the label "test" to match this flow to an agent.
with Flow(
    # Postfix the name of the flow with the environment it belongs to
    f"atd_parking_data_txn_history_{current_environment}",
    # Let's configure the agents to download the file from this repo
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/parking/atd_parking_data_meters_txn_history.py",
        ref="pard-data-flow",  # The branch name
        # ref=current_environment.replace("staging", "main"),  # The branch name
    ),
    # Run config will always need the current_environment
    # plus whatever labels you need to attach to this flow
    # run_config=UniversalRun(labels=[current_environment, "atd-data02"]),
    run_config=UniversalRun(labels=["test", "atd-data02"]),
    schedule=Schedule(clocks=[CronClock("35 3 * * *")]),
) as flow:
    flow.chain(
        pull_docker_image,
        parking_transaction_history_to_s3,
        parking_payment_history_to_s3,
        pard_payment_history_to_s3,
        update_last_exec_time,
    )


if __name__ == "__main__":
    flow.run()
